import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import TransactionServiceDependency
from app.schemas.transaction import TransactionCreate, TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])
FundIdQuery = Annotated[uuid.UUID | None, Query()]


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    service: TransactionServiceDependency,
) -> TransactionRead:
    return TransactionRead.model_validate(service.create_transaction(payload))


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    service: TransactionServiceDependency,
    fund_id: FundIdQuery = None,
) -> list[TransactionRead]:
    return [
        TransactionRead.model_validate(item)
        for item in service.list_transactions(fund_id=fund_id)
    ]
