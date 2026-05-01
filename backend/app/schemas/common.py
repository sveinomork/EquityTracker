from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value: object) -> object:
        if isinstance(value, Decimal):
            return float(value)
        return value
