"""
Payment service — PATCHED with idempotency enforcement.

FIX 1: process_payment() checks whether a transaction for the given payment_id
already exists before creating a new one. If a transaction exists, it is returned
directly without calling the backend again.

FIX 2: An in-process lock prevents concurrent requests for the same payment_id
from both passing the idempotency check simultaneously (TOCTOU protection).

FIX 3: The retry loop breaks after the first successful charge.
"""
from __future__ import annotations

import asyncio
import uuid
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from service.db import store, Transaction
from service import config

app = FastAPI(title="Payment Service (patched)")

# Per-payment_id locks to prevent concurrent TOCTOU races
_payment_locks: dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def _get_payment_lock(payment_id: str) -> asyncio.Lock:
    """Get or create a per-payment_id lock."""
    async with _locks_lock:
        if payment_id not in _payment_locks:
            _payment_locks[payment_id] = asyncio.Lock()
        return _payment_locks[payment_id]


class PaymentRequest(BaseModel):
    payment_id: str = Field(..., description="Logical payment identifier from client")
    amount: float = Field(..., gt=0, description="Amount in USD")


class PaymentResponse(BaseModel):
    payment_id: str
    transaction_ids: list[str]
    status: str


async def _call_backend(payment_id: str, amount: float) -> httpx.Response:
    """Call the backend charge endpoint. Replaceable in tests."""
    async with httpx.AsyncClient() as client:
        return await client.post(
            f"{config.get_backend_url()}/charge",
            json={"payment_id": payment_id, "amount": amount},
            timeout=5.0,
        )


@app.post("/payment", response_model=PaymentResponse)
async def process_payment(req: PaymentRequest) -> PaymentResponse:
    """
    Accept a payment request.

    FIX 1: Idempotency check — if a transaction for this payment_id already exists,
    return it immediately without creating a duplicate.
    FIX 2: Per-payment_id lock prevents concurrent TOCTOU races.
    FIX 3: Break after first successful charge.
    """
    # Acquire per-payment_id lock to prevent TOCTOU race in concurrent requests
    lock = await _get_payment_lock(req.payment_id)
    async with lock:
        # IDEMPOTENCY CHECK: return existing transaction if payment_id already processed
        existing = [tx for tx in store.list() if tx.payment_id == req.payment_id]
        if existing:
            return PaymentResponse(
                payment_id=req.payment_id,
                transaction_ids=[tx.transaction_id for tx in existing],
                status="ok",
            )

        last_status: int | None = None
        attempts = config.get_service_retry_on_timeout() + 1

        for attempt in range(attempts):
            try:
                response = await _call_backend(req.payment_id, req.amount)
                last_status = response.status_code

                if response.status_code == 504:
                    continue

                response.raise_for_status()

                tx = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    payment_id=req.payment_id,
                    amount=req.amount,
                    status="charged",
                )
                store.add(tx)

                # FIX 3: return immediately after first successful charge
                return PaymentResponse(
                    payment_id=req.payment_id,
                    transaction_ids=[tx.transaction_id],
                    status="ok",
                )

            except (httpx.HTTPStatusError, httpx.RequestError):
                continue

        raise HTTPException(
            status_code=502,
            detail=f"Backend charge failed after {attempts} attempts (last status: {last_status})",
        )


@app.get("/transactions")
def list_transactions() -> dict:
    txs = store.list()
    return {"count": len(txs), "transactions": [t.to_dict() for t in txs]}


@app.post("/admin/reset")
def reset_store() -> dict:
    store.reset()
    return {"status": "reset"}
