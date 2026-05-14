from enum import StrEnum


class TransactionType(StrEnum):
    """Supported transaction categories used across the domain."""
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND_REINVEST = "DIVIDEND_REINVEST"
