"""
Configuration for the payment service — read from environment variables.
Values are read at call time (via functions) to allow test overrides.
"""
import os


def get_service_retry_on_timeout() -> int:
    """How many times the SERVICE LAYER retries a backend call on 504."""
    return int(os.environ.get("SERVICE_RETRY_ON_TIMEOUT", "1"))


def get_max_retries() -> int:
    """Maximum retries the CLIENT (caller of /payment) is allowed."""
    return int(os.environ.get("MAX_RETRIES", "1"))


def get_backend_url() -> str:
    """URL of the mock payment processor backend."""
    return os.environ.get("BACKEND_URL", "http://localhost:8001")


SERVICE_PORT: int = int(os.environ.get("SERVICE_PORT", "8000"))
