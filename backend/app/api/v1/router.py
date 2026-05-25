"""
API v1 Router — aggregates all endpoint modules.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    bvb,
    companies,
    search,
    watch,
    risk,
    esg,
    alerts,
    portfolios,
    seap,
    reports,
    admin,
    ai_agent,
    new_companies,
    dashboard,
    predictive,
    relationships,
    due_diligence,
    market_intelligence,
    supply_chain,
    document_intelligence,
    regulatory_compliance,
    geospatial,
    api_marketplace,
    portfolio_optimization,
    international_expansion,
    blockchain_audit,
    crm,
    co2,
    dosare,
    balance_sheets,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(companies.router, prefix="/companies", tags=["Companies"])
api_v1_router.include_router(search.router, prefix="/search", tags=["Search & Discovery"])
api_v1_router.include_router(risk.router, prefix="/risk", tags=["Risk & Credit"])
api_v1_router.include_router(esg.router, prefix="/esg", tags=["ESG Scoring"])
api_v1_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts & Monitoring"])
api_v1_router.include_router(portfolios.router, prefix="/portfolios", tags=["Portfolios"])
api_v1_router.include_router(seap.router, prefix="/seap", tags=["SEAP Tenders"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["Reports & Export"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["Admin Dashboard"])
api_v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_v1_router.include_router(ai_agent.router, prefix="/ai", tags=["AI Agent"])
api_v1_router.include_router(new_companies.router, prefix="/new-companies", tags=["New Companies Feed"])
api_v1_router.include_router(predictive.router, prefix="/predictive", tags=["Predictive Analytics"])
api_v1_router.include_router(relationships.router, prefix="/relationships", tags=["Relationship Intelligence"])
api_v1_router.include_router(due_diligence.router, prefix="/due-diligence", tags=["Due Diligence"])
api_v1_router.include_router(market_intelligence.router, prefix="/market", tags=["Market Intelligence"])
api_v1_router.include_router(supply_chain.router, prefix="/supply-chain", tags=["Supply Chain Risk"])
api_v1_router.include_router(document_intelligence.router, prefix="/documents", tags=["Document Intelligence"])
api_v1_router.include_router(regulatory_compliance.router, prefix="/compliance", tags=["Regulatory Compliance"])
api_v1_router.include_router(geospatial.router, prefix="/geo", tags=["Geospatial BI"])
api_v1_router.include_router(api_marketplace.router, prefix="/marketplace", tags=["API Marketplace"])
api_v1_router.include_router(portfolio_optimization.router, prefix="/portfolio-opt", tags=["Portfolio Optimization"])
api_v1_router.include_router(international_expansion.router, prefix="/international", tags=["International Expansion"])
api_v1_router.include_router(blockchain_audit.router, prefix="/blockchain", tags=["Blockchain Audit"])
api_v1_router.include_router(crm.router, prefix="/crm", tags=["CRM Bridge"])
api_v1_router.include_router(co2.router, prefix="/co2", tags=["CO2 Emissions"])
api_v1_router.include_router(dosare.router, prefix="/dosare", tags=["Dosare Judecătorești"])
api_v1_router.include_router(balance_sheets.router, prefix="/companies", tags=["Balance Sheets"])
api_v1_router.include_router(bvb.router, prefix="/bvb", tags=["BVB"])
api_v1_router.include_router(watch.router, prefix="/watch", tags=["Watch"])
