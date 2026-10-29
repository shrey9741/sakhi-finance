from typing import Protocol

from app.core.config import Settings


class OtpProvider(Protocol):
    async def send(self, phone_e164: str, code: str) -> None: ...


class ConsoleOtpProvider:
    """Development only: prints the code. Refuses to run outside development."""

    def __init__(self, settings: Settings) -> None:
        if settings.app_env != "development":
            raise RuntimeError("ConsoleOtpProvider is for development only")

    async def send(self, phone_e164: str, code: str) -> None:
        print(f"[DEV OTP] {phone_e164}: {code}")
