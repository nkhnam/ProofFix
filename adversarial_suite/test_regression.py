"""
Regression tests — verify normal payment behavior still works after patching.

These tests must pass against the PATCHED service.
"""
import pytest


@pytest.mark.asyncio
async def test_normal_payment_creates_one_transaction(patched_service):
    """A simple payment with no retry or concurrency must create exactly 1 transaction."""
    client, store = patched_service

    r = await client.post("/payment", json={"payment_id": "REG-001", "amount": 49.99})
    assert r.status_code == 200

    body = r.json()
    assert body["payment_id"] == "REG-001"
    assert body["status"] == "ok"
    assert len(body["transaction_ids"]) == 1

    txs = store.list()
    assert len(txs) == 1
    assert txs[0].payment_id == "REG-001"
    assert txs[0].amount == 49.99


@pytest.mark.asyncio
async def test_different_payments_are_independent(patched_service):
    """Two different payment_ids must each produce exactly 1 transaction."""
    client, store = patched_service

    r1 = await client.post("/payment", json={"payment_id": "REG-002", "amount": 10.0})
    r2 = await client.post("/payment", json={"payment_id": "REG-003", "amount": 20.0})

    assert r1.status_code == 200
    assert r2.status_code == 200

    txs = store.list()
    assert len(txs) == 2
    pids = {tx.payment_id for tx in txs}
    assert pids == {"REG-002", "REG-003"}


@pytest.mark.asyncio
async def test_payment_response_contains_transaction_id(patched_service):
    """Payment response must include a transaction_id."""
    client, store = patched_service

    r = await client.post("/payment", json={"payment_id": "REG-004", "amount": 75.0})
    assert r.status_code == 200

    body = r.json()
    assert "transaction_ids" in body
    assert len(body["transaction_ids"]) >= 1
    assert len(body["transaction_ids"][0]) > 0
