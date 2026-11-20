from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.budgets import router as budgets_router
from app.api.v1.endpoints.categorization import router as categorization_router
from app.api.v1.endpoints.transactions import router as transactions_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(budgets_router, prefix="/budgets", tags=["budgets"])
api_router.include_router(categorization_router, prefix="/categorization", tags=["categorization"])
