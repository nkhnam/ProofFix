"""
Idempotency tests — adversarially verify the idempotency key semantics of the patch.

These tests verify:
1. Same payment_id submitted twice → exactly 1 transaction (idempotency)
2. Different payment_ids → independent transactions (no cross-contamination)
3. Timeout + retry scenario → 1 transaction (the original bug scenario fixed)
"""
import os
import pytest


@pytest.mark.asyncio
async def test_same_payment_id_twice_creates_one_transaction(patched_service):
    """
    The core idempotency guarantee: the same payment_id submitted twice must
    produce exactly 1 transaction record.
    """
    client, store = patched_service

    r1 = await client.post("/payment", json={"payment_id": "IDEM-001", "amount": 50.0})
    r2 = await client.post("/payment", json={"payment_id": "IDEM-001", "amount": 50.0})

    assert r1.status_code == 200
    assert r2.status_code == 200

    txs = store.list()
    assert len(txs) == 1, (
        f"Same payment_id submitted twice should create 1 transaction, got {len(txs)}"
    )
    assert txs[0].payment_id == "IDEM-001"


@pytest.mark.asyncio
async def test_idempotency_both_responses_return_same_transaction_id(patched_service):
    """
    Both responses for the same payment_id must reference the same transaction_id.
    This proves the second response is a replay, not a new charge.
    """
    client, store = patched_service

    r1 = await client.post("/payment", json={"payment_id": "IDEM-002", "amount": 75.0})
    r2 = await client.post("/payment", json={"payment_id": "IDEM-002", "amount": 75.0})

    assert r1.status_code == 200
    assert r2.status_code == 200

    ids1 = set(r1.json()["transaction_ids"])
    ids2 = set(r2.json()["transaction_ids"])

    assert ids1 == ids2, (
        f"Both responses should return the same transaction_id. "
        f"First: {ids1}, Second: {ids2}"
    )


@pytest.mark.asyncio
async def test_different_payment_ids_are_independent(patched_service):
    """
    Two different payment_ids must produce 2 separate transactions.
    The patch must not use a global dedup that blocks all payments.
    """
    client, store = patched_service

    r1 = await client.post("/payment", json={"payment_id": "IDEM-003", "amount": 10.0})
    r2 = await client.post("/payment", json={"payment_id": "IDEM-004", "amount": 20.0})

    assert r1.status_code == 200
    assert r2.status_code == 200

    txs = store.list()
    assert len(txs) == 2, (
        f"Two different payments should produce 2 transactions, got {len(txs)}"
    )
    assert txs[0].transaction_id != txs[1].transaction_id


@pytest.mark.asyncio
async def test_idempotency_survives_service_retry_loop(patched_service):
    """
    Even with SERVICE_RETRY_ON_TIMEOUT=1 (retry loop active), a single payment_id
    must produce exactly 1 transaction. The patch must work even when the retry
    loop would otherwise create duplicates.
    """
    client, store = patched_service

    # Service retry is active (SERVICE_RETRY_ON_TIMEOUT=1 set in conftest)
    r = await client.post("/payment", json={"payment_id": "IDEM-005", "amount": 99.0})
    assert r.status_code == 200

    txs = store.list()
    assert len(txs) == 1, (
        f"With service retry active, single payment should still create 1 transaction, "
        f"got {len(txs)}"
    )


@pytest.mark.asyncio
async def test_original_bug_scenario_fixed(patched_service):
    """
    Simulate the original bug scenario: same payment_id submitted twice (client retry).
    Must produce exactly 1 transaction — proving the bug is fixed.
    """
    client, store = patched_service

    # Original bug: client sends payment twice (simulating retry after timeout)
    r1 = await client.post("/payment", json={"payment_id": "IDEM-ORIG", "amount": 50.0})
    r2 = await client.post("/payment", json={"payment_id": "IDEM-ORIG", "amount": 50.0})

    assert r1.status_code == 200
    assert r2.status_code == 200

    txs = store.list()
    assert len(txs) == 1, (
        f"BUG FIX VERIFICATION: duplicate client request should not create duplicate transaction. "
        f"Got {len(txs)} transactions."
    )
