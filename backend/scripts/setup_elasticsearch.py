"""
Elasticsearch index setup script for RomBiz platform.
Creates indices with proper mappings, analyzers, and aliases.

Usage:
    python -m scripts.setup_elasticsearch
    # or
    python scripts/setup_elasticsearch.py
"""
import asyncio
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
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
                },
                "company_name_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "asciifolding",
                        "edge_ngram_filter",
                    ],
                },
                "cui_analyzer": {
                    "type": "custom",
                    "tokenizer": "keyword",
                    "filter": ["trim"],
                },
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
                "edge_ngram_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 15,
                },
            },
        },
    },
}

INDICES = {
    "rombiz_companies": {
        **INDEX_SETTINGS,
        "mappings": {
            "properties": {
                "id": {"type": "long"},
                "cui": {"type": "keyword", "copy_to": "cui_searchable"},
                "cui_searchable": {"type": "text", "analyzer": "cui_analyzer"},
                "denumire": {
                    "type": "text",
                    "analyzer": "romanian_custom",
                    "fields": {
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "company_name_analyzer",
                            "search_analyzer": "standard",
                        },
                        "keyword": {"type": "keyword"},
                    },
                },
                "judet": {"type": "keyword"},
                "localitate": {"type": "keyword"},
                "caen_principal": {"type": "keyword"},
                "descriere_caen": {"type": "text", "analyzer": "romanian_custom"},
                "stare": {"type": "keyword"},
                "forma_juridica": {"type": "keyword"},
                "data_infiintare": {"type": "date"},
                "capital_social": {"type": "scaled_float", "scaling_factor": 100},
                "has_debts": {"type": "boolean"},
                "has_insolvency": {"type": "boolean"},
                "platitor_tva": {"type": "boolean"},
                "risk_score": {"type": "scaled_float", "scaling_factor": 100},
                "risk_rating": {"type": "keyword"},
                "nr_angajati": {"type": "integer"},
                "cifra_afaceri": {"type": "scaled_float", "scaling_factor": 100},
                "profit_net": {"type": "scaled_float", "scaling_factor": 100},
                "location": {"type": "geo_point"},
                "updated_at": {"type": "date"},
                "suggest": {
                    "type": "completion",
                    "analyzer": "simple",
                    "preserve_separators": True,
                    "preserve_position_increments": True,
                    "max_input_length": 50,
                },
            }
        },
    },
    "rombiz_tenders": {
        **INDEX_SETTINGS,
        "mappings": {
            "properties": {
                "id": {"type": "long"},
                "tender_number": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "romanian_custom"},
                "authority_name": {"type": "text", "analyzer": "romanian_custom", "fields": {"keyword": {"type": "keyword"}}},
                "cpv_code": {"type": "keyword"},
                "estimated_value": {"type": "scaled_float", "scaling_factor": 100},
                "currency": {"type": "keyword"},
                "procedure_type": {"type": "keyword"},
                "submission_deadline": {"type": "date"},
                "status": {"type": "keyword"},
                "created_at": {"type": "date"},
            }
        },
    },
    "rombiz_court_cases": {
        **INDEX_SETTINGS,
        "mappings": {
            "properties": {
                "id": {"type": "long"},
                "company_id": {"type": "long"},
                "numar_dosar": {"type": "keyword"},
                "instanta": {"type": "keyword"},
                "materie": {"type": "keyword"},
                "stadiu": {"type": "keyword"},
                "data_ultimei_modificari": {"type": "date"},
                "parti": {"type": "text", "analyzer": "romanian_custom"},
                "obiect": {"type": "text", "analyzer": "romanian_custom"},
            }
        },
    },
    "rombiz_audit_log": {
        **INDEX_SETTINGS,
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "org_id": {"type": "keyword"},
                "action": {"type": "keyword"},
                "entity_type": {"type": "keyword"},
                "entity_id": {"type": "keyword"},
                "ip_address": {"type": "ip"},
                "user_agent": {"type": "text"},
                "created_at": {"type": "date"},
            }
        },
    },
}

ALIASES = {
    "companies": "rombiz_companies",
    "tenders": "rombiz_tenders",
    "court_cases": "rombiz_court_cases",
    "audit": "rombiz_audit_log",
}


async def setup_indices():
    """Create all Elasticsearch indices."""
    try:
        from elasticsearch import AsyncElasticsearch
    except ImportError:
        print("ERROR: elasticsearch package not installed. Run: pip install elasticsearch[async]")
        return

    from app.core.config import settings

    es = AsyncElasticsearch(settings.ELASTICSEARCH_URL)

    try:
        print(f"Connecting to Elasticsearch at {settings.ELASTICSEARCH_URL}...")
        info = await es.info()
        print(f"Connected: {info['version']['number']}")

        for index_name, config in INDICES.items():
            if await es.indices.exists(index=index_name):
                print(f"  [SKIP] Index '{index_name}' already exists")
            else:
                await es.indices.create(index=index_name, body=config)
                print(f"  [OK]   Created index '{index_name}'")

        # Create aliases
        for alias, target in ALIASES.items():
            try:
                await es.indices.put_alias(index=target, name=alias)
                print(f"  [OK]   Alias '{alias}' -> '{target}'")
            except Exception:
                print(f"  [SKIP] Alias '{alias}' already exists")

        print("\nElasticsearch setup complete!")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(setup_indices())
