"""
Concurrency tests — adversarially test concurrent duplicate requests.

THE KEY DIFFERENTIATOR: these tests would FAIL against the unpatched service
and must PASS against the patched service.

Two threads send the same payment_id simultaneously. The patch must ensure
exactly 1 transaction is created regardless of race conditions.
"""
import asyncio
import pytest


@pytest.mark.asyncio
async def test_concurrent_duplicate_requests_create_one_transaction(patched_service):
    """
    Two concurrent POST /payment for the same payment_id must produce exactly 1 transaction.
    This is the hardest test for the patch — it exercises the race condition window.
    """
    client, store = patched_service

    async def submit():
        return await client.post(
            "/payment",
            json={"payment_id": "CONC-001", "amount": 50.0},
        )

    # Fire both requests concurrently
    r1, r2 = await asyncio.gather(submit(), submit())

    assert r1.status_code == 200, f"Request 1 failed: {r1.text}"
    assert r2.status_code == 200, f"Request 2 failed: {r2.text}"

    txs = store.list()
    assert len(txs) == 1, (
        f"Concurrent duplicate requests should produce 1 transaction, got {len(txs)}. "
        f"Transactions: {[t.to_dict() for t in txs]}"
    )


@pytest.mark.asyncio
async def test_concurrent_different_payments_both_succeed(patched_service):
    """
    Two concurrent requests with DIFFERENT payment_ids must each create exactly 1 transaction.
    The patch must not accidentally block legitimate concurrent payments.
    """
    client, store = patched_service

    async def pay(pid, amount):
        return await client.post("/payment", json={"payment_id": pid, "amount": amount})

    r1, r2 = await asyncio.gather(
        pay("CONC-002", 25.0),
        pay("CONC-003", 75.0),
    )

    assert r1.status_code == 200
    assert r2.status_code == 200

    txs = store.list()
    assert len(txs) == 2, (
        f"Two different payments should produce 2 transactions, got {len(txs)}"
    )
    pids = {tx.payment_id for tx in txs}
    assert pids == {"CONC-002", "CONC-003"}


@pytest.mark.asyncio
async def test_high_concurrency_duplicate_creates_one_transaction(patched_service):
    """
    Five concurrent requests for the same payment_id must produce exactly 1 transaction.
    """
    client, store = patched_service

    async def submit():
        return await client.post(
            "/payment",
            json={"payment_id": "CONC-004", "amount": 99.0},
        )

    results = await asyncio.gather(*[submit() for _ in range(5)])

    for r in results:
        assert r.status_code == 200, f"One request failed: {r.text}"

    txs = store.list()
    assert len(txs) == 1, (
        f"5 concurrent duplicate requests should produce 1 transaction, got {len(txs)}"
    )
