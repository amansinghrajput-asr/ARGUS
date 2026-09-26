"""Domain exceptions for ARGUS Backend 1."""


class ArgusDomainError(Exception):
    """Base exception for domain errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EntityNotFoundError(ArgusDomainError):
    """Raised when an entity is not found."""

    def __init__(self, message: str = "Entity not found") -> None:
        super().__init__(message=message, status_code=404)


class DuplicateEntityError(ArgusDomainError):
    """Raised when an entity already exists."""

    def __init__(self, message: str = "Entity already exists") -> None:
        super().__init__(message=message, status_code=409)


class ValidationError(ArgusDomainError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Invalid input data") -> None:
        super().__init__(message=message, status_code=400)
