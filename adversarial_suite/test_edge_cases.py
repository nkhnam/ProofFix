"""
Edge case tests — adversarially test boundary conditions of the patch.

These tests must pass against the PATCHED service.
"""
import pytest


@pytest.mark.asyncio
async def test_zero_amount_payment_rejected(patched_service):
    """Payments with amount <= 0 must be rejected (pydantic validation)."""
    client, store = patched_service

    r = await client.post("/payment", json={"payment_id": "EDGE-001", "amount": 0})
    assert r.status_code == 422, (
        f"Expected 422 for zero amount, got {r.status_code}: {r.text}"
    )
    assert store.count() == 0


@pytest.mark.asyncio
async def test_negative_amount_payment_rejected(patched_service):
    """Payments with negative amount must be rejected."""
    client, store = patched_service

    r = await client.post("/payment", json={"payment_id": "EDGE-002", "amount": -50.0})
    assert r.status_code == 422
    assert store.count() == 0


@pytest.mark.asyncio
async def test_missing_payment_id_rejected(patched_service):
    """Payment without payment_id must be rejected."""
    client, store = patched_service

    r = await client.post("/payment", json={"amount": 25.0})
    assert r.status_code == 422
    assert store.count() == 0


@pytest.mark.asyncio
async def test_missing_amount_rejected(patched_service):
    """Payment without amount must be rejected."""
    client, store = patched_service

    r = await client.post("/payment", json={"payment_id": "EDGE-004"})
    assert r.status_code == 422
    assert store.count() == 0


@pytest.mark.asyncio
async def test_same_payment_id_five_retries_one_transaction(patched_service):
    """Five sequential retries of the same payment_id must produce exactly 1 transaction."""
    client, store = patched_service

    for i in range(5):
        r = await client.post("/payment", json={"payment_id": "EDGE-005", "amount": 100.0})
        assert r.status_code == 200, f"Retry {i} failed: {r.text}"

    txs = store.list()
    assert len(txs) == 1, (
        f"5 retries of same payment_id should produce 1 transaction, got {len(txs)}"
    )


@pytest.mark.asyncio
async def test_very_large_amount_accepted(patched_service):
    """Large amounts should be accepted (no upper bound validation in this service)."""
    client, store = patched_service

    r = await client.post("/payment", json={"payment_id": "EDGE-006", "amount": 9_999_999.99})
    assert r.status_code == 200
    assert store.count() == 1
