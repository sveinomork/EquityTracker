from enum import StrEnum


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND_REINVEST = "DIVIDEND_REINVEST"
