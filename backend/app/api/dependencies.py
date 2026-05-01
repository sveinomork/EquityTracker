from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.rate_repository import RateRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.fund_service import FundService
from app.services.interest_service import InterestService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.services.transaction_service import TransactionService

SessionDependency = Annotated[Session, Depends(get_db_session)]


def get_fund_service(session: SessionDependency) -> FundService:
    return FundService(FundRepository(session))


def get_transaction_service(session: SessionDependency) -> TransactionService:
    return TransactionService(FundRepository(session), TransactionRepository(session))


def get_market_data_service(session: SessionDependency) -> MarketDataService:
    return MarketDataService(
        FundRepository(session), PriceRepository(session), RateRepository(session)
    )


def get_portfolio_analytics_service(session: SessionDependency) -> PortfolioAnalyticsService:
    return PortfolioAnalyticsService(
        FundRepository(session),
        TransactionRepository(session),
        PriceRepository(session),
        RateRepository(session),
        InterestService(),
    )


FundServiceDependency = Annotated[FundService, Depends(get_fund_service)]
TransactionServiceDependency = Annotated[TransactionService, Depends(get_transaction_service)]
MarketDataServiceDependency = Annotated[MarketDataService, Depends(get_market_data_service)]
PortfolioAnalyticsServiceDependency = Annotated[
    PortfolioAnalyticsService,
    Depends(get_portfolio_analytics_service),
]
