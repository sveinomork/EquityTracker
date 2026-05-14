import uuid

from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import NotFoundError, ValidationError
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundCreate, FundTaxConfigUpdate


class FundService:
    """Business operations for creating and maintaining funds."""
    def __init__(self, fund_repository: FundRepository) -> None:
        """Initialize the service with fund repository access."""
        self.fund_repository = fund_repository

    def create_fund(self, payload: FundCreate) -> Fund:
        """Create and persist a new fund from request payload data."""
        fund = Fund(
            name=payload.name.strip(),
            ticker=payload.ticker.strip().upper(),
            is_distributing=payload.is_distributing,
            manual_taxable_gain_override=payload.manual_taxable_gain_override,
        )
        try:
            created = self.fund_repository.add(fund)
            self.fund_repository.session.commit()
            return created
        except IntegrityError as exc:
            self.fund_repository.session.rollback()
            raise ValidationError("Fund ticker already exists") from exc

    def list_funds(self) -> list[Fund]:
        """Return all funds available in the system."""
        return self.fund_repository.list_all()

    def get_fund(self, fund_id: uuid.UUID) -> Fund:
        """Return one fund by id or raise when it does not exist."""
        fund = self.fund_repository.get(fund_id)
        if fund is None:
            raise NotFoundError("Fund not found")
        return fund

    def update_tax_config(self, fund_id: uuid.UUID, payload: FundTaxConfigUpdate) -> Fund:
        """Update tax-related fund configuration values."""
        fund = self.get_fund(fund_id)
        if "is_distributing" in payload.model_fields_set and payload.is_distributing is not None:
            fund.is_distributing = payload.is_distributing
        if "manual_taxable_gain_override" in payload.model_fields_set:
            fund.manual_taxable_gain_override = payload.manual_taxable_gain_override
        self.fund_repository.session.flush()
        self.fund_repository.session.commit()
        self.fund_repository.session.refresh(fund)
        return fund
