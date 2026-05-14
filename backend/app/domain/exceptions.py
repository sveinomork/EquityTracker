class DomainError(Exception):
    """Base exception for domain-level application errors."""
    pass


class NotFoundError(DomainError):
    """Raised when a requested domain entity does not exist."""
    pass


class ValidationError(DomainError):
    """Raised when business validation rules are violated."""
    pass
