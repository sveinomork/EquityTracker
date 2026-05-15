from fastapi import APIRouter

from app.api.v1 import funds, portfolio, prices, rates, reports, sync, transactions

api_router = APIRouter()
api_router.include_router(funds.router)
api_router.include_router(transactions.router)
api_router.include_router(prices.router)
api_router.include_router(rates.router)
api_router.include_router(portfolio.router)
api_router.include_router(reports.router)
api_router.include_router(sync.router)
