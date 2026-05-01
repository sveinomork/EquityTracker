import uuid

from app.domain.exceptions import NotFoundError
from app.models.daily_fund_price import DailyFundPrice
from app.models.loan_rate_history import LoanRateHistory
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.rate_repository import RateRepository
from app.schemas.price import DailyFundPriceBatchCreate
from app.schemas.rate import LoanRateBatchCreate


class MarketDataService:
    def __init__(
        self,
        fund_repository: FundRepository,
        price_repository: PriceRepository,
        rate_repository: RateRepository,
    ) -> None:
        self.fund_repository = fund_repository
        self.price_repository = price_repository
        self.rate_repository = rate_repository

    def add_prices(
        self, fund_id: uuid.UUID, payload: DailyFundPriceBatchCreate
    ) -> list[DailyFundPrice]:
        if self.fund_repository.get(fund_id) is None:
            raise NotFoundError("Fund not found")

        prices = [
            DailyFundPrice(fund_id=fund_id, date=item.date, price=item.price)
            for item in payload.items
        ]
        stored = self.price_repository.upsert_many(fund_id, prices)
        self.price_repository.session.commit()
        return stored

    def add_rates(self, fund_id: uuid.UUID, payload: LoanRateBatchCreate) -> list[LoanRateHistory]:
        if self.fund_repository.get(fund_id) is None:
            raise NotFoundError("Fund not found")

        rates = [
            LoanRateHistory(
                fund_id=fund_id,
                effective_date=item.effective_date,
                nominal_rate=item.nominal_rate,
            )
            for item in payload.items
        ]
        stored = self.rate_repository.upsert_many(fund_id, rates)
        self.rate_repository.session.commit()
        return stored
