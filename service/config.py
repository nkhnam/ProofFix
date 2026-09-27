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
    hostport = os.environ.get("BACKEND_HOSTPORT")
    if hostport:
        return hostport if "://" in hostport else f"http://{hostport}"
    return os.environ.get("BACKEND_URL", "http://localhost:8001")


def get_frontend_origins() -> list[str]:
    configured = os.environ.get("FRONTEND_ORIGIN", "")
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *[origin.strip() for origin in configured.split(",") if origin.strip()],
    ]


SERVICE_PORT: int = int(os.environ.get("SERVICE_PORT", "8000"))
