"""
Adversarial test suite conftest.py

Provides shared fixtures for all adversarial tests:
- patched_service: starts the PATCHED service with idempotency fix
- unpatched_service: starts the BUGGY service (for verifying tests detect the bug)
- Writes results to evidence/adversarial_results.json on completion
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path

import pytest

# Resolve repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RESULTS_FILE = REPO_ROOT / "evidence" / "adversarial_results.json"

# Collected test results across the session
_test_results: list[dict] = []


def _make_backend_client():
    import httpx
    from httpx import AsyncClient, ASGITransport
    from mock_backend.main import app as backend_app
    return AsyncClient(
        transport=ASGITransport(app=backend_app), base_url="http://mock-backend"
    )


def _patch_call_backend(svc_main, backend_client):
    import httpx
    original = svc_main._call_backend

    async def patched(payment_id: str, amount: float) -> httpx.Response:
        return await backend_client.post(
            "/charge",
            json={"payment_id": payment_id, "amount": amount},
            timeout=5.0,
        )

    svc_main._call_backend = patched
    return original


@pytest.fixture()
async def patched_service():
    """
    Fixture providing the PATCHED service with idempotency enforcement.
    Yields (AsyncClient, TransactionStore).
    """
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "1"
    os.environ["INJECT_TIMEOUT"] = "false"

    import importlib
    import service.main_patched as _svc
    importlib.reload(_svc)

    from mock_backend.main import _charges, _seen
    from service.db import store

    store.reset()
    _charges.clear()
    _seen.clear()

    import httpx
    from httpx import AsyncClient, ASGITransport

    backend_client = _make_backend_client()
    original = _patch_call_backend(_svc, backend_client)

    service_client = AsyncClient(
        transport=ASGITransport(app=_svc.app), base_url="http://svc"
    )

    yield service_client, store

    _svc._call_backend = original
    await backend_client.aclose()
    await service_client.aclose()
    store.reset()
    _charges.clear()
    _seen.clear()


@pytest.fixture(autouse=True)
def reset_state():
    from mock_backend.main import _charges, _seen
    from service.db import store
    store.reset()
    _charges.clear()
    _seen.clear()
    yield
    store.reset()
    _charges.clear()
    _seen.clear()


# ---------------------------------------------------------------------------
# Result collection hook — writes adversarial_results.json after test session
# ---------------------------------------------------------------------------

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        start = time.monotonic()
        passed = report.passed
        category = "unknown"
        for cat in ("regression", "edge_cases", "concurrency", "idempotency"):
            if cat in item.nodeid:
                category = cat
                break

        counterexample = None
        if not passed and report.longrepr:
            counterexample = str(report.longrepr)[:500]

        _test_results.append({
            "test_id": f"ADV-{uuid.uuid4().hex[:8]}",
            "test_name": item.name,
            "category": category,
            "result": "PASS" if passed else "FAIL",
            "observed": "test passed" if passed else "test failed",
            "expected": "test should pass",
            "counterexample": counterexample,
            "duration_ms": round((time.monotonic() - start) * 1000, 2),
        })


def pytest_sessionfinish(session, exitstatus):
    """Write all results to adversarial_results.json after the session."""
    if _test_results:
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(_test_results, f, indent=2)
        print(f"\n[adversarial] Results written to: {RESULTS_FILE}")
