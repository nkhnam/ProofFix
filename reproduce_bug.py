"""
Deterministic in-process bug reproduction harness.

THE BUG MODEL:
  A client sends POST /payment for payment_id="PAY-001".
  Due to a network timeout at the HTTP layer, the client retries the same request.
  The service receives the same payment_id twice.
  The service has no idempotency check — it processes both and creates 2 transactions.

This harness runs both services in-process via ASGI transport.
No real network, no ports, no Docker required.

Usage:
    python reproduce_bug.py

Expected output:
    Expected logical payments : 1
    Actual transactions       : 2
    BUG REPRODUCED ✓
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("INJECT_TIMEOUT", "false")   # no backend timeout needed for base bug
os.environ.setdefault("SERVICE_RETRY_ON_TIMEOUT", "0")  # service does NOT retry — only client retries
os.environ.setdefault("BACKEND_URL", "http://mock-backend")


async def reproduce() -> int:
    """
    Simulate client retry: send the same payment_id twice.
    Returns the number of transactions in the store.
    """
    from mock_backend.main import app as backend_app, _charges, _seen
    from service.db import store
    import service.main_buggy as svc_main

    # Reset state
    store.reset()
    _charges.clear()
    _seen.clear()

    import httpx
    from httpx import AsyncClient, ASGITransport

    backend_client = AsyncClient(
        transport=ASGITransport(app=backend_app), base_url="http://mock-backend"
    )

    async def patched_call_backend(payment_id: str, amount: float) -> httpx.Response:
        return await backend_client.post(
            "/charge",
            json={"payment_id": payment_id, "amount": amount},
            timeout=5.0,
        )

    original = svc_main._call_backend
    svc_main._call_backend = patched_call_backend

    service_client = AsyncClient(
        transport=ASGITransport(app=svc_main.app), base_url="http://payment-service"
    )

    try:
        # CLIENT RETRY: same payment_id sent twice (simulating timeout + retry)
        r1 = await service_client.post(
            "/payment",
            json={"payment_id": "PAY-001", "amount": 99.99},
        )
        r2 = await service_client.post(
            "/payment",
            json={"payment_id": "PAY-001", "amount": 99.99},
        )
        return store.count()
    finally:
        svc_main._call_backend = original
        await backend_client.aclose()
        await service_client.aclose()


def main():
    count = asyncio.run(reproduce())
    print()
    print("=" * 50)
    print(f"  Expected logical payments : 1")
    print(f"  Actual transactions       : {count}")
    print("=" * 50)
    if count >= 2:
        print("  BUG REPRODUCED [OK]")
        print("=" * 50)
        sys.exit(0)
    else:
        print(f"  !! Bug did NOT reproduce (count={count})")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
