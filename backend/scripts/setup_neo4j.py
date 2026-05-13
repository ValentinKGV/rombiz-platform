"""
Neo4j schema setup script for RomBiz Fraud Graph.
Creates constraints, indexes, and initial schema structure.

Usage:
    python -m scripts.setup_neo4j
    # or
    python scripts/setup_neo4j.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Constraints ──────────────────────────────────────────────────────
CONSTRAINTS = [
    "CREATE CONSTRAINT company_cui IF NOT EXISTS FOR (c:Company) REQUIRE c.cui IS UNIQUE",
    "CREATE CONSTRAINT person_cnp IF NOT EXISTS FOR (p:Person) REQUIRE p.cnp_hash IS UNIQUE",
    "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE (p.first_name, p.last_name) IS NOT NULL",
]

# ── Indexes ──────────────────────────────────────────────────────────
INDEXES = [
    "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.denumire)",
    "CREATE INDEX company_judet_idx IF NOT EXISTS FOR (c:Company) ON (c.judet)",
    "CREATE INDEX company_caen_idx IF NOT EXISTS FOR (c:Company) ON (c.caen_principal)",
    "CREATE INDEX company_risk_idx IF NOT EXISTS FOR (c:Company) ON (c.risk_rating)",
    "CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.last_name, p.first_name)",
    "CREATE INDEX address_judet_idx IF NOT EXISTS FOR (a:Address) ON (a.judet)",
]

# ── Node labels and their properties (documentation) ─────────────────
NODE_TYPES = """
// Node Types:
//
// (:Company {
//     cui: STRING,           -- CUI (unique)
//     denumire: STRING,      -- Company name
//     judet: STRING,
//     localitate: STRING,
//     caen_principal: STRING,
//     stare: STRING,         -- ACTIV, INACTIV, RADIAT
//     risk_score: FLOAT,
//     risk_rating: STRING,   -- A, B, C, D, E
//     capital_social: FLOAT,
//     data_infiintare: DATE,
//     has_debts: BOOLEAN,
//     has_insolvency: BOOLEAN
// })
//
// (:Person {
//     cnp_hash: STRING,       -- GDPR-compliant hashed CNP
//     first_name: STRING,
//     last_name: STRING,
//     function: STRING,       -- Administrator, Asociat, Director
//     nationality: STRING
// })
//
// (:Address {
//     judet: STRING,
//     localitate: STRING,
//     strada: STRING,
//     numar: STRING,
//     full_address: STRING
// })
//
// (:BankAccount {
//     bank_name: STRING,
//     iban_hash: STRING
// })
"""

# ── Relationship types ───────────────────────────────────────────────
RELATIONSHIP_TYPES = """
// Relationship Types:
//
// (:Person)-[:ADMINISTRATOR_OF {from_date, to_date}]->(:Company)
// (:Person)-[:ASSOCIATE_OF {share_pct: FLOAT, from_date}]->(:Company)
// (:Person)-[:DIRECTOR_OF {from_date, to_date}]->(:Company)
// (:Person)-[:CENSOR_OF]->(:Company)
//
// (:Company)-[:SHAREHOLDER_OF {share_pct: FLOAT}]->(:Company)
// (:Company)-[:SUBSIDIARY_OF]->(:Company)
// (:Company)-[:SUPPLIER_OF]->(:Company)
// (:Company)-[:CLIENT_OF]->(:Company)
//
// (:Company)-[:REGISTERED_AT]->(:Address)
// (:Person)-[:LIVES_AT]->(:Address)
//
// (:Company)-[:HAS_CONTRACT_WITH {value, currency, year}]->(:Company)
// (:Company)-[:LITIGANT_WITH {case_number, year}]->(:Company)
//
// (:Company)-[:FLAGGED {type: STRING, score: FLOAT, date}]->(:FraudAlert)
"""

# ── Sample Cypher queries for fraud detection ────────────────────────
FRAUD_QUERIES = {
    "circular_ownership": """
        // Detect circular ownership (A owns B owns C owns A)
        MATCH path = (c1:Company)-[:SHAREHOLDER_OF*2..5]->(c1)
        RETURN c1.cui, c1.denumire, length(path) as cycle_length, 
               [n IN nodes(path) | n.denumire] AS companies
        LIMIT 100
    """,
    "shared_administrator": """
        // Companies sharing administrators (potential related-party)
        MATCH (p:Person)-[:ADMINISTRATOR_OF]->(c1:Company),
              (p)-[:ADMINISTRATOR_OF]->(c2:Company)
        WHERE c1 <> c2
        RETURN p.first_name + ' ' + p.last_name AS person,
               collect(DISTINCT c1.denumire) AS companies,
               count(DISTINCT c1) AS company_count
        ORDER BY company_count DESC
        LIMIT 50
    """,
    "same_address_cluster": """
        // Companies at the same address (potential shell companies)
        MATCH (c1:Company)-[:REGISTERED_AT]->(a:Address)<-[:REGISTERED_AT]-(c2:Company)
        WHERE c1 <> c2
        WITH a, collect(DISTINCT c1.denumire) AS companies, count(DISTINCT c1) AS cnt
        WHERE cnt >= 5
        RETURN a.full_address, companies, cnt
        ORDER BY cnt DESC
        LIMIT 20
    """,
    "high_risk_network": """
        // Network of high-risk companies connected through people
        MATCH (c:Company {risk_rating: 'E'})<-[:ADMINISTRATOR_OF|ASSOCIATE_OF]-(p:Person)
              -[:ADMINISTRATOR_OF|ASSOCIATE_OF]->(c2:Company)
        WHERE c <> c2
        RETURN c.denumire AS risky_company, c.risk_score,
               p.first_name + ' ' + p.last_name AS connector,
               c2.denumire AS connected_company, c2.risk_rating
        ORDER BY c.risk_score DESC
        LIMIT 100
    """,
    "revenue_anomaly_connected": """
        // Connected companies where one has revenue anomaly
        MATCH (c1:Company)-[:SHAREHOLDER_OF|HAS_CONTRACT_WITH]-(c2:Company)
        WHERE c1.risk_score > 80 AND c2.risk_score < 30
        RETURN c1.denumire, c1.risk_score, c2.denumire, c2.risk_score,
               type(relationships(path)[0]) AS connection_type
        LIMIT 50
    """,
}


async def setup_neo4j():
    """Create Neo4j schema: constraints, indexes."""
    try:
        from neo4j import AsyncGraphDatabase
    except ImportError:
        print("ERROR: neo4j package not installed. Run: pip install neo4j")
        return

    from app.core.config import settings

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        print(f"Connecting to Neo4j at {settings.NEO4J_URI}...")
        async with driver.session() as session:
            # Verify connectivity
            result = await session.run("RETURN 1 AS test")
            await result.single()
            print("Connected to Neo4j!")

            # Create constraints
            print("\nCreating constraints...")
            for cypher in CONSTRAINTS:
                try:
                    await session.run(cypher)
                    print(f"  [OK]   {cypher[:60]}...")
                except Exception as e:
                    print(f"  [SKIP] {str(e)[:80]}")

            # Create indexes
            print("\nCreating indexes...")
            for cypher in INDEXES:
                try:
                    await session.run(cypher)
                    print(f"  [OK]   {cypher[:60]}...")
                except Exception as e:
                    print(f"  [SKIP] {str(e)[:80]}")

            print("\nNeo4j schema setup complete!")
            print(f"\nAvailable fraud detection queries: {list(FRAUD_QUERIES.keys())}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(setup_neo4j())
