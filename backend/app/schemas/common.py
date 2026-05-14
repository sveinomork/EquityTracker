from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class APIModel(BaseModel):
    """Base Pydantic model with ORM support and JSON-friendly decimals."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value: object) -> object:
        """Convert Decimal values to float during JSON serialization."""
        if isinstance(value, Decimal):
            return float(value)
        return value
