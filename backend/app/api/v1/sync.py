from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SessionDependency
from app.services.yahoo_sync_service import SyncResult, sync_yahoo_prices

router = APIRouter(prefix="/sync", tags=["sync"])

StartDateQuery = Annotated[date | None, Query()]


@router.post("/yahoo", response_model=list[SyncResult])
def trigger_yahoo_sync(
    session: SessionDependency,
    start_date: StartDateQuery = None,
) -> list[SyncResult]:
    """Fetch latest prices from Yahoo Finance for all known tickers and store in DB."""
    return sync_yahoo_prices(session, start_date=start_date)
