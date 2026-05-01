import uuid

from pydantic import Field

from app.schemas.common import APIModel


class FundCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    ticker: str = Field(min_length=1, max_length=32)


class FundRead(APIModel):
    id: uuid.UUID
    name: str
    ticker: str
