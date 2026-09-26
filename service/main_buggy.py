"""
Payment service — intentionally missing idempotency enforcement.

BUG: process_payment() retries on backend 504 and records every successful
     charge independently. There is no idempotency key check. If the backend
     times out and the service retries, the same payment is charged twice.
"""
from __future__ import annotations

import uuid
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from service.db import store, Transaction
from service import config

app = FastAPI(title="Payment Service (buggy)")


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

    INTENTIONAL BUG: This function calls the backend and retries on 504.
    Each successful backend call creates a new transaction — there is no
    idempotency key check. A single payment_id can result in multiple
    transactions if a 504 triggers a retry.
    """
    created_tx_ids: list[str] = []
    last_status: int | None = None

    attempts = config.get_service_retry_on_timeout() + 1  # initial + retries

    for attempt in range(attempts):
        try:
            response = await _call_backend(req.payment_id, req.amount)
            last_status = response.status_code

            if response.status_code == 504:
                # Backend timed out — will retry
                continue

            response.raise_for_status()

            # Record the successful charge — NO idempotency key check here
            tx = Transaction(
                transaction_id=str(uuid.uuid4()),
                payment_id=req.payment_id,
                amount=req.amount,
                status="charged",
            )
            store.add(tx)
            created_tx_ids.append(tx.transaction_id)

        except (httpx.HTTPStatusError, httpx.RequestError):
            continue

    if not created_tx_ids:
        raise HTTPException(
            status_code=502,
            detail=f"Backend charge failed after {attempts} attempts (last status: {last_status})",
        )

    return PaymentResponse(
        payment_id=req.payment_id,
        transaction_ids=created_tx_ids,
        status="ok" if len(created_tx_ids) == 1 else "duplicate_charge_warning",
    )


@app.get("/transactions")
def list_transactions() -> dict:
    """Return current transaction store state — used by experiments."""
    txs = store.list()
    return {
        "count": len(txs),
        "transactions": [t.to_dict() for t in txs],
    }


@app.post("/admin/reset")
def reset_store() -> dict:
    """Reset in-memory store — used between experiment runs."""
    store.reset()
    return {"status": "reset"}
