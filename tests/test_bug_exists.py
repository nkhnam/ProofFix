"""
Tests proving the duplicate-payment bug exists in the unpatched service.

THE BUG MODEL:
  - A client retries the same payment_id after a timeout.
  - The service has no idempotency check.
  - Both requests are processed, creating 2 transactions.

ALSO TESTS:
  - Service-layer retry (Experiment B trigger): when the backend times out,
    the service retries, and with no idempotency check, also creates duplicates.

These tests run entirely in-process — no Docker, no real ports.

Run with:
    pytest tests/test_bug_exists.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from httpx import AsyncClient, ASGITransport


def _make_backend_client():
    from mock_backend.main import app as backend_app
    return AsyncClient(
        transport=ASGITransport(app=backend_app), base_url="http://mock-backend"
    )


def _patch_service(svc_main, backend_client):
    """Patch _call_backend to route to in-process backend. Returns original."""
    original = svc_main._call_backend

    async def patched(payment_id: str, amount: float) -> httpx.Response:
        return await backend_client.post(
            "/charge",
            json={"payment_id": payment_id, "amount": amount},
            timeout=5.0,
        )

    svc_main._call_backend = patched
    return original


@pytest.fixture(autouse=True)
def reset_state():
    """Reset stores before every test."""
    from mock_backend.main import _charges, _seen
    from service.db import store
    store.reset()
    _charges.clear()
    _seen.clear()
    yield
    store.reset()
    _charges.clear()
    _seen.clear()


@pytest.fixture()
async def service_no_retry():
    """
    Service fixture: SERVICE_RETRY_ON_TIMEOUT=0, INJECT_TIMEOUT=false.
    Uses main_buggy (intentionally broken service) to prove the bug exists.
    Service will NOT retry on backend 504. Only client-side retries cause duplicates.
    """
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "0"
    os.environ["INJECT_TIMEOUT"] = "false"

    import importlib
    from mock_backend.main import app as backend_app
    import service.main_buggy as svc_main
    importlib.reload(svc_main)
    from service.db import store

    backend_client = _make_backend_client()
    original = _patch_service(svc_main, backend_client)

    service_client = AsyncClient(
        transport=ASGITransport(app=svc_main.app), base_url="http://svc"
    )
    yield service_client, store

    svc_main._call_backend = original
    await backend_client.aclose()
    await service_client.aclose()


@pytest.fixture()
async def service_with_retry():
    """
    Service fixture: SERVICE_RETRY_ON_TIMEOUT=1, INJECT_TIMEOUT=false.
    Uses main_buggy — the service runs ALL retry attempts even after a success (the bug).
    A single client request -> 2 backend calls -> 2 transactions.
    """
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "1"
    os.environ["INJECT_TIMEOUT"] = "false"

    import importlib
    from mock_backend.main import app as backend_app
    import service.main_buggy as svc_main
    importlib.reload(svc_main)
    from service.db import store

    backend_client = _make_backend_client()
    original = _patch_service(svc_main, backend_client)

    service_client = AsyncClient(
        transport=ASGITransport(app=svc_main.app), base_url="http://svc"
    )
    yield service_client, store

    svc_main._call_backend = original
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "0"
    os.environ["INJECT_TIMEOUT"] = "false"
    await backend_client.aclose()
    await service_client.aclose()


# ---------------------------------------------------------------------------
# Bug-existence tests: CLIENT RETRY scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_retry_creates_duplicate_transactions(service_no_retry):
    """
    Core bug: client retries same payment_id → service processes both → 2 transactions.
    This is the direct client-retry scenario.
    """
    service_client, store = service_no_retry

    # Simulate client-side retry: send the same payment_id twice
    r1 = await service_client.post("/payment", json={"payment_id": "PAY-001", "amount": 50.0})
    r2 = await service_client.post("/payment", json={"payment_id": "PAY-001", "amount": 50.0})

    assert r1.status_code == 200
    assert r2.status_code == 200

    txs = store.list()
    assert len(txs) == 2, (
        f"Expected 2 transactions from client retry, got {len(txs)}: "
        f"{[t.to_dict() for t in txs]}"
    )


@pytest.mark.asyncio
async def test_duplicate_transactions_have_same_payment_id(service_no_retry):
    """Both duplicate transactions must reference the same logical payment_id."""
    service_client, store = service_no_retry

    await service_client.post("/payment", json={"payment_id": "PAY-002", "amount": 75.0})
    await service_client.post("/payment", json={"payment_id": "PAY-002", "amount": 75.0})

    txs = store.list()
    assert len(txs) == 2
    assert all(tx.payment_id == "PAY-002" for tx in txs)


@pytest.mark.asyncio
async def test_duplicate_transactions_have_different_transaction_ids(service_no_retry):
    """Duplicate transactions must have distinct transaction_ids."""
    service_client, store = service_no_retry

    await service_client.post("/payment", json={"payment_id": "PAY-003", "amount": 100.0})
    await service_client.post("/payment", json={"payment_id": "PAY-003", "amount": 100.0})

    txs = store.list()
    assert len(txs) == 2
    assert txs[0].transaction_id != txs[1].transaction_id


@pytest.mark.asyncio
async def test_different_payment_ids_are_not_duplicates(service_no_retry):
    """
    Two requests with different payment_ids are legitimate separate payments.
    Both should create exactly 1 transaction each (2 total).
    """
    service_client, store = service_no_retry

    await service_client.post("/payment", json={"payment_id": "PAY-A", "amount": 10.0})
    await service_client.post("/payment", json={"payment_id": "PAY-B", "amount": 20.0})

    txs = store.list()
    assert len(txs) == 2
    payment_ids = {tx.payment_id for tx in txs}
    assert payment_ids == {"PAY-A", "PAY-B"}


@pytest.mark.asyncio
async def test_bug_reproduces_deterministically_three_times(service_no_retry):
    """Bug must reproduce every time, not just occasionally."""
    service_client, store = service_no_retry
    from mock_backend.main import _charges, _seen

    for run in range(3):
        store.reset()
        _charges.clear()
        _seen.clear()

        pid = f"PAY-RUN-{run}"
        await service_client.post("/payment", json={"payment_id": pid, "amount": 10.0})
        await service_client.post("/payment", json={"payment_id": pid, "amount": 10.0})

        assert store.count() == 2, f"Run {run}: expected 2 transactions, got {store.count()}"


# ---------------------------------------------------------------------------
# Bug-existence tests: SERVICE RETRY scenario (backend timeout triggers retry)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_retry_loop_creates_duplicate_on_single_request(service_with_retry):
    """
    Service-layer bug: the retry loop runs all `attempts` even after a success.
    With SERVICE_RETRY_ON_TIMEOUT=1 (no backend timeout), a SINGLE client request
    triggers 2 backend calls → 2 transactions recorded.

    This proves the bug exists at the service layer independently of client retries (H2).
    """
    service_client, store = service_with_retry

    # Single client request — no client-side retry needed
    r = await service_client.post("/payment", json={"payment_id": "PAY-SVC-001", "amount": 50.0})
    assert r.status_code == 200

    txs = store.list()
    assert len(txs) == 2, (
        f"Service retry loop should create 2 transactions, got {len(txs)}: "
        f"{[t.to_dict() for t in txs]}"
    )
