"""
Experiment A: disable_frontend_retry

Hypothesis being tested: H1
"The duplicate is caused by frontend/client retry behavior. Disabling client
retry will stop duplicates."

Intervention:
- MAX_RETRIES = 0 (client sends the payment request exactly once — no retry)
- SERVICE_RETRY_ON_TIMEOUT = 1 (service internal retry loop is still active)
- INJECT_TIMEOUT = false (backend always succeeds)

Prediction if H1 is correct:
- With no client retry, only 1 request reaches the service → 1 transaction → no duplicate.

Actual expected result:
- Service retry loop still runs both attempts even after first success.
- With SERVICE_RETRY_ON_TIMEOUT=1, a SINGLE request creates 2 transactions.
- H1 is FALSIFIED: the duplicate persists even without client retry.

Causal conclusion:
- The source of the duplicate is the service-layer retry loop, not client behavior.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run() -> dict:
    """
    Run Experiment A: disable client retry, keep service retry active.
    Returns structured evidence dict.
    """
    # Set experiment conditions
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "1"  # service retry stays active
    os.environ["INJECT_TIMEOUT"] = "false"         # backend always succeeds
    # MAX_RETRIES=0 is enforced by the caller (client sends only 1 request)

    from mock_backend.main import app as backend_app, _charges, _seen
    import service.main_buggy as svc_main
    from service.db import store

    # Reset state
    store.reset()
    _charges.clear()
    _seen.clear()

    import httpx
    from httpx import AsyncClient, ASGITransport

    backend_client = AsyncClient(
        transport=ASGITransport(app=backend_app), base_url="http://mock-backend"
    )

    call_log: list[str] = []
    call_count = 0

    async def tracked_call_backend(payment_id: str, amount: float) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        entry = f"attempt {call_count}: POST /charge payment_id={payment_id}"
        call_log.append(entry)
        r = await backend_client.post(
            "/charge",
            json={"payment_id": payment_id, "amount": amount},
            timeout=5.0,
        )
        call_log.append(f"attempt {call_count}: response status={r.status_code}")
        return r

    original = svc_main._call_backend
    svc_main._call_backend = tracked_call_backend

    service_client = AsyncClient(
        transport=ASGITransport(app=svc_main.app), base_url="http://svc"
    )

    try:
        # CLIENT RETRY DISABLED: send payment exactly ONCE (MAX_RETRIES=0)
        response = await service_client.post(
            "/payment",
            json={"payment_id": "EXP-A-001", "amount": 50.0},
        )

        txs = store.list()
        tx_count = len(txs)
        duplicate_count = max(0, tx_count - 1)

        # Determine result
        if duplicate_count >= 1:
            result = "FALSIFIED"
            reason = (
                f"H1 FALSIFIED: duplicate_count={duplicate_count} even with client retry "
                f"disabled (MAX_RETRIES=0). The service retry loop (SERVICE_RETRY_ON_TIMEOUT=1) "
                f"still executed {call_count} backend calls, creating {tx_count} transactions. "
                f"Client retry behavior is NOT the root cause."
            )
        else:
            result = "SUPPORTED"
            reason = (
                f"H1 SUPPORTED: no duplicate with client retry disabled. "
                f"transactions_created={tx_count}, backend_calls={call_count}."
            )

        return {
            "transactions_created": tx_count,
            "duplicate_count": duplicate_count,
            "backend_calls": call_count,
            "retry_log_entries": call_log,
            "result": result,
            "reason": reason,
            "raw_evidence": [t.to_dict() for t in txs],
        }

    finally:
        svc_main._call_backend = original
        await backend_client.aclose()
        await service_client.aclose()


if __name__ == "__main__":
    import json
    evidence = asyncio.run(run())
    print(json.dumps(evidence, indent=2, default=str))
