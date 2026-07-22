class CreovaError(Exception):
    """Base exception for expected domain and application failures."""


class AccessDenied(CreovaError):
    pass


class InvalidStateTransition(CreovaError):
    pass


class QuotaExceeded(CreovaError):
    pass


class BudgetExceeded(CreovaError):
    pass
