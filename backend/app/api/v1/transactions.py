from fastapi import APIRouter, status

from app.api.dependencies import TransactionServiceDependency
from app.schemas.transaction import TransactionCreate, TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    service: TransactionServiceDependency,
) -> TransactionRead:
    return TransactionRead.model_validate(service.create_transaction(payload))
