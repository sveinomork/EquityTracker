import uuid

from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import NotFoundError, ValidationError
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundCreate


class FundService:
    def __init__(self, fund_repository: FundRepository) -> None:
        self.fund_repository = fund_repository

    def create_fund(self, payload: FundCreate) -> Fund:
        fund = Fund(name=payload.name.strip(), ticker=payload.ticker.strip().upper())
        try:
            created = self.fund_repository.add(fund)
            self.fund_repository.session.commit()
            return created
        except IntegrityError as exc:
            self.fund_repository.session.rollback()
            raise ValidationError("Fund ticker already exists") from exc

    def list_funds(self) -> list[Fund]:
        return self.fund_repository.list_all()

    def get_fund(self, fund_id: uuid.UUID) -> Fund:
        fund = self.fund_repository.get(fund_id)
        if fund is None:
            raise NotFoundError("Fund not found")
        return fund
