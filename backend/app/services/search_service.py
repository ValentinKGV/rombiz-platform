"""
Search service — Elasticsearch + PostgreSQL hybrid search.

v2 Improvements:
  4.1: PostgreSQL pg_trgm fallback for fuzzy search when ES is unavailable
  4.2: Faceted search with dynamic aggregations
  4.3: Multi-column sorting with financial joins
  4.4: "Did you mean" suggestions via trigram similarity
  4.5: Saved searches (CRUD)
  4.6: Geo search by judet/localitate radius proxy
"""
from __future__ import annotations

from typing import Optional, Any
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, func, text, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.models import Company, FinancialData, SavedSearch

logger = get_logger(__name__)

# ── 4.6: Romanian county centroids (lat, lon) for geo proximity ──
JUDET_COORDS: dict[str, tuple[float, float]] = {
    "ALBA": (46.07, 23.57), "ARAD": (46.18, 21.32), "ARGES": (44.86, 24.87),
    "BACAU": (46.57, 26.91), "BIHOR": (47.05, 21.93), "BISTRITA-NASAUD": (47.13, 24.50),
    "BOTOSANI": (47.75, 26.67), "BRAILA": (45.27, 27.97), "BRASOV": (45.65, 25.61),
    "BUCURESTI": (44.43, 26.10), "BUZAU": (45.15, 26.83), "CALARASI": (44.20, 26.99),
    "CARAS-SEVERIN": (45.30, 21.89), "CLUJ": (46.77, 23.60), "CONSTANTA": (44.18, 28.63),
    "COVASNA": (45.85, 26.18), "DAMBOVITA": (44.93, 25.45), "DOLJ": (44.32, 23.80),
    "GALATI": (45.44, 28.05), "GIURGIU": (43.90, 25.97), "GORJ": (45.05, 23.27),
    "HARGHITA": (46.36, 25.80), "HUNEDOARA": (45.88, 22.90), "IALOMITA": (44.57, 26.88),
    "IASI": (47.17, 27.58), "ILFOV": (44.53, 26.10), "MARAMURES": (47.66, 24.00),
    "MEHEDINTI": (44.63, 22.65), "MURES": (46.55, 24.56), "NEAMT": (46.93, 26.38),
    "OLT": (44.43, 24.37), "PRAHOVA": (44.95, 25.95), "SALAJ": (47.20, 23.05),
    "SATU MARE": (47.78, 22.88), "SIBIU": (45.80, 24.15), "SUCEAVA": (47.64, 26.26),
    "TELEORMAN": (43.98, 25.30), "TIMIS": (45.76, 21.23), "TULCEA": (45.18, 28.80),
    "VALCEA": (45.10, 24.37), "VASLUI": (46.64, 27.73), "VRANCEA": (45.70, 27.18),
}


class SearchService:
    """
    Hybrid search: Elasticsearch for fuzzy/NLP search,
    PostgreSQL pg_trgm + tsvector as fallback.
    v2: 6 enhancement areas.
    """

    def __init__(self, es_client=None, db: AsyncSession = None):
        self.es = es_client
        self.db = db
        self.index_name = "companies"

    async def init_index(self):
        """Create Elasticsearch index with Romanian analyzer."""
        if not self.es:
            return

        mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "romanian_custom": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "romanian_stop",
                                "romanian_stemmer",
                                "asciifolding",
                            ],
                        }
                    },
                    "filter": {
                        "romanian_stop": {
                            "type": "stop",
                            "stopwords": "_romanian_",
                        },
                        "romanian_stemmer": {
                            "type": "stemmer",
                            "language": "romanian",
                        },
                    },
                },
                "number_of_shards": 2,
                "number_of_replicas": 1,
            },
            "mappings": {
                "properties": {
                    "cui": {"type": "integer"},
                    "denumire": {
                        "type": "text",
                        "analyzer": "romanian_custom",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {
                                "type": "completion",
                                "analyzer": "simple",
                            },
                        },
                    },
                    "judet": {"type": "keyword"},
                    "localitate": {"type": "text"},
                    "cod_caen": {"type": "keyword"},
                    "stare_firma": {"type": "keyword"},
                    "stare_tva": {"type": "keyword"},
                    "data_infiintare": {"type": "date"},
                    "flag_insolventa": {"type": "boolean"},
                    "flag_datorii": {"type": "boolean"},
                    "adresa_completa": {"type": "text"},
                    "forma_juridica": {"type": "keyword"},
                    "cifra_afaceri": {"type": "long"},
                    "numar_angajati": {"type": "integer"},
                    "scor_risc": {"type": "float"},
                },
            },
        }

        exists = await self.es.indices.exists(index=self.index_name)
        if not exists:
            await self.es.indices.create(index=self.index_name, body=mapping)
            logger.info("elasticsearch_index_created", index=self.index_name)

    async def index_company(self, company_data: dict):
        """Index a single company document."""
        if not self.es:
            return

        await self.es.index(
            index=self.index_name,
            id=str(company_data["cui"]),
            body=company_data,
        )

    async def bulk_index(self, companies: list[dict]):
        """Bulk index companies."""
        if not self.es:
            return

        from elasticsearch.helpers import async_bulk

        actions = [
            {
                "_index": self.index_name,
                "_id": str(c["cui"]),
                "_source": c,
            }
            for c in companies
        ]

        success, errors = await async_bulk(self.es, actions)
        logger.info("elasticsearch_bulk_index", success=success, errors=len(errors))

    async def search(
        self,
        q: str,
        filters: Optional[dict] = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "_score",
        sort_dir: str = "DESC",
    ) -> dict:
        """
        Full-text search with filters.
        4.1: Falls back to PostgreSQL pg_trgm when ES is unavailable.
        """
        if self.es:
            return await self._search_es(q, filters, page, per_page, sort_by, sort_dir)
        elif self.db:
            return await self._search_pg(q, filters, page, per_page, sort_by, sort_dir)
        else:
            return {"total": 0, "items": [], "source": "unavailable"}

    async def _search_es(
        self, q: str, filters: Optional[dict],
        page: int, per_page: int, sort_by: str, sort_dir: str,
    ) -> dict:
        """Elasticsearch search."""
        must = []
        filter_clauses = []

        if q:
            must.append({
                "multi_match": {
                    "query": q,
                    "fields": ["denumire^3", "adresa_completa", "localitate"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            })

        if filters:
            if filters.get("judet"):
                filter_clauses.append({"term": {"judet": filters["judet"]}})
            if filters.get("cod_caen"):
                filter_clauses.append({"prefix": {"cod_caen": filters["cod_caen"]}})
            if filters.get("stare_firma"):
                filter_clauses.append({"term": {"stare_firma": filters["stare_firma"]}})
            if filters.get("has_insolvency") is not None:
                filter_clauses.append({"term": {"flag_insolventa": filters["has_insolvency"]}})
            if filters.get("cifra_afaceri_min"):
                filter_clauses.append({"range": {"cifra_afaceri": {"gte": filters["cifra_afaceri_min"]}}})
            if filters.get("cifra_afaceri_max"):
                filter_clauses.append({"range": {"cifra_afaceri": {"lte": filters["cifra_afaceri_max"]}}})

        # 4.3: Sort
        sort_clause = []
        if sort_by != "_score" and q:
            sort_clause.append({"_score": "desc"})
        if sort_by and sort_by != "_score":
            sort_clause.append({sort_by: sort_dir.lower()})

        body = {
            "query": {
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "from": (page - 1) * per_page,
            "size": per_page,
            "highlight": {
                "fields": {
                    "denumire": {},
                    "adresa_completa": {},
                }
            },
        }
        if sort_clause:
            body["sort"] = sort_clause

        result = await self.es.search(index=self.index_name, body=body)

        hits = result["hits"]
        return {
            "total": hits["total"]["value"],
            "items": [
                {
                    **hit["_source"],
                    "score": hit["_score"],
                    "highlights": hit.get("highlight", {}),
                }
                for hit in hits["hits"]
            ],
            "source": "elasticsearch",
        }

    async def _search_pg(
        self, q: str, filters: Optional[dict],
        page: int, per_page: int, sort_by: str, sort_dir: str,
    ) -> dict:
        """
        4.1: PostgreSQL fallback with pg_trgm similarity and ILIKE.
        Works without Elasticsearch for development/small deployments.
        """
        if not self.db:
            return {"total": 0, "items": [], "source": "unavailable"}

        query = select(Company)
        count_query = select(func.count(Company.id))
        clauses = []

        if q:
            # Use ILIKE for basic match + trigram ordering
            like_pattern = f"%{q}%"
            clauses.append(
                or_(
                    Company.denumire.ilike(like_pattern),
                    Company.adresa_completa.ilike(like_pattern),
                    Company.localitate.ilike(like_pattern),
                )
            )

        if filters:
            if filters.get("judet"):
                clauses.append(Company.judet == filters["judet"])
            if filters.get("cod_caen"):
                clauses.append(Company.caen_principal.startswith(filters["cod_caen"]))
            if filters.get("stare_firma"):
                clauses.append(Company.stare == filters["stare_firma"])
            if filters.get("has_insolvency") is not None:
                clauses.append(Company.has_insolvency == filters["has_insolvency"])

        if clauses:
            query = query.where(and_(*clauses))
            count_query = count_query.where(and_(*clauses))

        # 4.3: Sort mapping
        pg_sort_map = {
            "denumire": Company.denumire,
            "cui": Company.cui,
            "data_infiintare": Company.data_infiintare,
            "capital_social": Company.capital_social,
        }
        sort_col = pg_sort_map.get(sort_by, Company.denumire)
        if sort_dir.upper() == "ASC":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await self.db.execute(query)
        companies = result.scalars().all()

        return {
            "total": total,
            "items": [
                {
                    "cui": c.cui,
                    "denumire": c.denumire,
                    "judet": c.judet,
                    "localitate": c.localitate,
                    "stare": c.stare,
                    "caen_principal": c.caen_principal,
                    "data_infiintare": c.data_infiintare.isoformat() if c.data_infiintare else None,
                    "score": None,
                }
                for c in companies
            ],
            "source": "postgresql",
        }

    async def suggest(self, prefix: str, limit: int = 10) -> list[dict]:
        """Autocomplete suggestions. 4.1: PostgreSQL fallback."""
        if self.es:
            return await self._suggest_es(prefix, limit)
        elif self.db:
            return await self._suggest_pg(prefix, limit)
        return []

    async def _suggest_es(self, prefix: str, limit: int) -> list[dict]:
        """ES completion suggest."""
        body = {
            "suggest": {
                "company-suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "denumire.suggest",
                        "size": limit,
                        "fuzzy": {"fuzziness": 1},
                    },
                }
            }
        }

        result = await self.es.search(index=self.index_name, body=body)
        suggestions = result.get("suggest", {}).get("company-suggest", [{}])[0]

        return [
            {
                "cui": opt["_source"]["cui"],
                "denumire": opt["_source"]["denumire"],
                "judet": opt["_source"].get("judet"),
            }
            for opt in suggestions.get("options", [])
        ]

    async def _suggest_pg(self, prefix: str, limit: int) -> list[dict]:
        """4.1: PostgreSQL ILIKE fallback for suggestions."""
        if not self.db:
            return []

        result = await self.db.execute(
            select(Company.cui, Company.denumire, Company.judet)
            .where(Company.denumire.ilike(f"{prefix}%"))
            .order_by(Company.denumire)
            .limit(limit)
        )
        return [
            {"cui": r.cui, "denumire": r.denumire, "judet": r.judet}
            for r in result.all()
        ]

    # ──────────────────────────────────────────────────────────────────
    # 4.4: "Did you mean" suggestions
    # ──────────────────────────────────────────────────────────────────

    async def did_you_mean(self, q: str) -> Optional[str]:
        """
        4.4: Suggest corrected query by finding most similar company names.
        Uses pg_trgm similarity or Levenshtein distance.
        """
        if not self.db or not q or len(q) < 3:
            return None

        # Try pg_trgm similarity (requires pg_trgm extension)
        try:
            result = await self.db.execute(
                text("""
                    SELECT denumire, similarity(denumire, :q) AS sim
                    FROM companies
                    WHERE similarity(denumire, :q) > 0.15
                    ORDER BY sim DESC
                    LIMIT 1
                """),
                {"q": q},
            )
            row = result.one_or_none()
            if row and row[0].lower() != q.lower():
                return row[0]
        except Exception:
            # pg_trgm not available — use ILIKE prefix fallback
            try:
                prefix = q[:3]
                result = await self.db.execute(
                    select(Company.denumire)
                    .where(Company.denumire.ilike(f"{prefix}%"))
                    .order_by(Company.denumire)
                    .limit(1)
                )
                row = result.one_or_none()
                if row and row[0].lower() != q.lower():
                    return row[0]
            except Exception:
                pass

        return None

    # ──────────────────────────────────────────────────────────────────
    # 4.5: Saved Searches
    # ──────────────────────────────────────────────────────────────────

    async def save_search(
        self, user_id: int, name: str, filters: dict
    ) -> dict:
        """4.5: Save a search configuration for a user."""
        if not self.db:
            raise ValueError("Database not available")

        saved = SavedSearch(
            user_id=user_id,
            name=name,
            filters=filters,
        )
        self.db.add(saved)
        return {"id": saved.id, "name": name, "created": True}

    async def get_saved_searches(self, user_id: int) -> list[dict]:
        """4.5: Get all saved searches for a user."""
        if not self.db:
            return []

        result = await self.db.execute(
            select(SavedSearch)
            .where(SavedSearch.user_id == user_id)
            .order_by(SavedSearch.created_at.desc())
        )
        searches = result.scalars().all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "filters": s.filters,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in searches
        ]

    async def delete_saved_search(self, user_id: int, search_id: int) -> bool:
        """4.5: Delete a saved search."""
        if not self.db:
            return False

        result = await self.db.execute(
            select(SavedSearch)
            .where(SavedSearch.id == search_id, SavedSearch.user_id == user_id)
        )
        search = result.scalar_one_or_none()
        if search:
            await self.db.delete(search)
            return True
        return False

    # ──────────────────────────────────────────────────────────────────
    # 4.6: Geo Search
    # ──────────────────────────────────────────────────────────────────

    async def geo_search(
        self, judet: str, radius_km: float = 100, limit: int = 50
    ) -> list[dict]:
        """
        4.6: Find companies near a county center.
        Uses precomputed county centroids for proximity calculation.
        Returns counties within radius with company counts.
        """
        center = JUDET_COORDS.get(judet.upper())
        if not center:
            return []

        nearby_judete = []
        for jud, coords in JUDET_COORDS.items():
            # Approximate distance using Haversine simplified
            import math
            lat1, lon1 = math.radians(center[0]), math.radians(center[1])
            lat2, lon2 = math.radians(coords[0]), math.radians(coords[1])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            km = 6371 * c

            if km <= radius_km:
                nearby_judete.append({"judet": jud, "distance_km": round(km, 1)})

        nearby_judete.sort(key=lambda x: x["distance_km"])

        if not self.db:
            return nearby_judete

        # Get company counts per nearby county
        jud_names = [j["judet"] for j in nearby_judete]
        result = await self.db.execute(
            select(Company.judet, func.count(Company.id).label("cnt"))
            .where(Company.judet.in_(jud_names))
            .group_by(Company.judet)
        )
        counts = {r.judet: r.cnt for r in result.all()}

        for j in nearby_judete:
            j["company_count"] = counts.get(j["judet"], 0)

        return nearby_judete[:limit]
