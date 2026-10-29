class OtpError(Exception):
    """Base class for OTP failures."""


class InvalidPhoneError(OtpError):
    pass


class OtpCooldownError(OtpError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("OTP requested too soon")
        self.retry_after = retry_after


class InvalidOtpError(OtpError):
    """Wrong, expired, used or locked-out code. Deliberately one generic error."""
