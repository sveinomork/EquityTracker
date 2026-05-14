import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import TransactionServiceDependency
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])
FundIdQuery = Annotated[uuid.UUID | None, Query()]


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    service: TransactionServiceDependency,
) -> TransactionRead:
    """Create a new transaction in the portfolio."""
    return TransactionRead.model_validate(service.create_transaction(payload))


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    service: TransactionServiceDependency,
) -> TransactionRead:
    """Update an existing transaction by its identifier."""
    return TransactionRead.model_validate(service.update_transaction(transaction_id, payload))


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    service: TransactionServiceDependency,
    fund_id: FundIdQuery = None,
) -> list[TransactionRead]:
    """List transactions, optionally filtered by fund id."""
    return [
        TransactionRead.model_validate(item)
        for item in service.list_transactions(fund_id=fund_id)
    ]
