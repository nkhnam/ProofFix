"""
Mock payment processor backend.

Simple, deterministic mock — always processes charges and returns 200.
No idempotency enforcement (intentional — that's the bug to fix in the service).

When the service receives two requests for the same payment_id (due to client
retry after timeout), it calls this backend twice. The backend records both
charges and bills the customer twice.
"""
from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Payment Processor")

# Charges recorded by the backend
_charges: list[dict] = []

# Used for 504 injection — tracks which payment_ids have had their first call
_seen: set[str] = set()


class ChargeRequest(BaseModel):
    payment_id: str
    amount: float


@app.post("/charge")
def charge(req: ChargeRequest):
    """
    Process a charge.

    Normal mode (INJECT_TIMEOUT=false): always returns 200 + records charge.
    Timeout mode (INJECT_TIMEOUT=true): first call per payment_id → 504 (no charge),
    subsequent calls → 200 + records charge.

    INJECT_TIMEOUT is read at call time so that test/experiment env overrides take effect
    even when the module was imported before the env var was set.
    """
    inject_timeout: bool = os.environ.get("INJECT_TIMEOUT", "false").lower() == "true"
    if inject_timeout and req.payment_id not in _seen:
        _seen.add(req.payment_id)
        return JSONResponse(
            status_code=504,
            content={"detail": "Gateway Timeout (injected)"},
        )

    charge_record = {
        "charge_id": f"chg_{req.payment_id}_{len(_charges) + 1}",
        "payment_id": req.payment_id,
        "amount": req.amount,
        "status": "processed",
    }
    _charges.append(charge_record)
    return charge_record


@app.get("/charges")
def list_charges():
    """Return all backend charges — used by experiments."""
    return {"total": len(_charges), "charges": _charges}


@app.post("/admin/reset")
def reset():
    """Reset all state between experiment runs."""
    _charges.clear()
    _seen.clear()
    return {"status": "reset"}


@app.get("/health")
def health():
    inject_timeout: bool = os.environ.get("INJECT_TIMEOUT", "false").lower() == "true"
    return {"status": "ok", "inject_timeout": inject_timeout}
