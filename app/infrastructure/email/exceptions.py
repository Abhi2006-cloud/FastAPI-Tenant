"""Email infrastructure exceptions."""


class EmailException(Exception):
    """Base exception for email operations."""

    pass


class EmailDeliveryException(EmailException):
    """Raised when an email provider fails to send an email."""

    pass


class EmailConfigurationException(EmailException):
    """Raised when email settings are missing or invalid."""

    pass


class EmailRateLimitException(EmailException):
    """Raised when invitation or email rate limit per org is exceeded."""

    pass
