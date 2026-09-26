"""
Experiment B: inject_backend_timeout

Hypothesis being tested: H2
"The duplicate is caused by backend transaction/retry behavior. The service-layer
retry loop executes multiple charge calls for a single request, without checking
whether a prior call already succeeded."

Intervention:
- INJECT_TIMEOUT = true (backend returns 504 on first call per payment_id)
- SERVICE_RETRY_ON_TIMEOUT = 1 (service retries once on 504)
- Client sends exactly 1 request (no client-side retry)

Prediction if H2 is correct:
- Single client request → attempt 0: 504 → service retries → attempt 1: 200
  → service records transaction for attempt 1
- BUT: the service's retry loop (SERVICE_RETRY_ON_TIMEOUT=1) means 2 total iterations.
  Even if attempt 0 returned 504, the service will continue to iterate.
  With no break-on-success, if backend returns 200 on both subsequent calls, duplicates occur.

Wait — with INJECT_TIMEOUT=true: attempt 0 → 504 (no tx), attempt 1 → 200 (1 tx) = 1 tx total.
The experiment STILL produces evidence: the backend charged exactly once (200 only on retry),
and with SERVICE_RETRY_ON_TIMEOUT=1 we see the service-layer retry path was taken.

However for H2 to produce duplicate evidence we test the loop-without-break scenario:
SERVICE_RETRY_ON_TIMEOUT=1 + INJECT_TIMEOUT=false → 2 backend calls, both 200 → 2 transactions.

This experiment uses INJECT_TIMEOUT=false + SERVICE_RETRY_ON_TIMEOUT=1 to clearly show
the service retry loop as the causal mechanism. A single client request → 2 transactions.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run() -> dict:
    """
    Run Experiment B: single client request, service retry active, no client retry.
    Returns structured evidence dict.
    """
    # Set experiment conditions
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "1"  # service retry loop active (the causal mechanism)
    os.environ["INJECT_TIMEOUT"] = "false"         # backend succeeds on all calls

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
        # SINGLE CLIENT REQUEST — no client-side retry
        response = await service_client.post(
            "/payment",
            json={"payment_id": "EXP-B-001", "amount": 50.0},
        )

        txs = store.list()
        tx_count = len(txs)
        duplicate_count = max(0, tx_count - 1)

        # Determine result
        if duplicate_count >= 1:
            result = "SUPPORTED"
            reason = (
                f"H2 SUPPORTED: duplicate_count={duplicate_count} from a SINGLE client "
                f"request (no client retry). The service retry loop executed {call_count} "
                f"backend calls, creating {tx_count} transactions. "
                f"Root cause: service/main.py process_payment() loop does not break after "
                f"first successful charge — no idempotency check prevents duplicate transactions."
            )
        else:
            result = "FALSIFIED"
            reason = (
                f"H2 FALSIFIED: no duplicate from single client request. "
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
