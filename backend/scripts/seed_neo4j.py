"""Seed Neo4j graph database from PostgreSQL data."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def seed_neo4j():
    from neo4j import AsyncGraphDatabase
    from app.core.config import settings
    from app.core.database import get_db_context
    from sqlalchemy import text

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    # Get companies from PG
    async with get_db_context() as db:
        result = await db.execute(text(
            "SELECT c.cui, c.denumire, c.judet, c.localitate, c.caen_principal, c.stare,"
            " c.capital_social, c.adresa_completa,"
            " rs.score as risk_score, rs.rating as risk_rating"
            " FROM companies c"
            " LEFT JOIN risk_scores rs ON rs.company_id = c.id"
        ))
        companies = result.fetchall()

        result2 = await db.execute(text(
            "SELECT p.nume_complet, p.tip, "
            " c.cui as company_cui"
            " FROM company_persons p"
            " JOIN companies c ON c.id = p.company_id"
        ))
        persons = result2.fetchall()

    async with driver.session() as session:
        # Create Company nodes
        count = 0
        for c in companies:
            await session.run(
                "MERGE (comp:Company {cui: $cui}) "
                "SET comp.denumire = $denumire, "
                "comp.judet = $judet, "
                "comp.localitate = $localitate, "
                "comp.caen_principal = $caen, "
                "comp.stare = $stare, "
                "comp.capital_social = $capital, "
                "comp.risk_score = $risk_score, "
                "comp.risk_rating = $risk_rating",
                {
                    "cui": str(c.cui),
                    "denumire": c.denumire,
                    "judet": c.judet,
                    "localitate": c.localitate,
                    "caen": c.caen_principal,
                    "stare": c.stare,
                    "capital": float(c.capital_social) if c.capital_social else 0,
                    "risk_score": float(c.risk_score) if c.risk_score else None,
                    "risk_rating": c.risk_rating,
                },
            )
            count += 1
        print(f"Created {count} Company nodes.")

        # Create Address nodes + relationships
        for c in companies:
            if c.adresa_completa:
                await session.run(
                    "MERGE (a:Address {full_address: $addr}) "
                    "SET a.judet = $judet, a.localitate = $localitate "
                    "WITH a "
                    "MATCH (comp:Company {cui: $cui}) "
                    "MERGE (comp)-[:REGISTERED_AT]->(a)",
                    {
                        "addr": c.adresa_completa,
                        "judet": c.judet,
                        "localitate": c.localitate,
                        "cui": str(c.cui),
                    },
                )
        print("Created Address nodes and relationships.")

        # Create Person nodes + relationships
        pcount = 0
        for p in persons:
            func = (p.tip or "").lower()
            if "admin" in func:
                rel = "ADMINISTRATOR_OF"
            elif "asociat" in func or "shareholder" in func:
                rel = "ASSOCIATE_OF"
            elif "director" in func:
                rel = "DIRECTOR_OF"
            else:
                rel = "ASSOCIATE_OF"

            # Split nume_complet into first/last
            parts = (p.nume_complet or "").strip().split(" ", 1)
            fn = parts[0] if parts else ""
            ln = parts[1] if len(parts) > 1 else ""

            await session.run(
                f"MERGE (p:Person {{first_name: $fn, last_name: $ln}}) "
                f"SET p.function = $func "
                f"WITH p "
                f"MATCH (c:Company {{cui: $cui}}) "
                f"MERGE (p)-[:{rel}]->(c)",
                {
                    "fn": fn,
                    "ln": ln,
                    "func": p.tip,
                    "cui": str(p.company_cui),
                },
            )
            pcount += 1
        print(f"Created {pcount} Person nodes with relationships.")

        # Summary
        result = await session.run(
            "MATCH (n) RETURN labels(n)[0] as label, count(n) as cnt"
        )
        records = [r async for r in result]
        for r in records:
            print(f"  {r['label']}: {r['cnt']} nodes")

    await driver.close()
    print("\nNeo4j seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_neo4j())
