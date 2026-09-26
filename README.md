# ProofFix — BUG COURT

> **Scientific debugging workflow powered by IBM Bob: hypothesis → controlled experiment → evidence → verified patch.**

BUG COURT is a structured debugging framework that forces an AI agent (IBM Bob) to *prove* a root cause before writing a single line of fix. Every decision is backed by experimental evidence and recorded in an auditable **Evidence Ledger**.

---

## The Problem It Solves

Most AI debuggers follow the same broken loop:

```
see bug → guess cause → write patch → hope it works
```

BUG COURT replaces guessing with science:

```
bug → competing hypotheses → controlled experiment → falsification → causal patch → adversarial verification
```

---

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn httpx pydantic pytest pytest-asyncio anyio

# 1. Reproduce the bug
python reproduce_bug.py

# 2. Run all tests (23 total)
python -m pytest tests/ adversarial_suite/ -v

# 3. Run the full end-to-end demo (~3.5 seconds)
python demo/run_demo.py

# 4. Open the Evidence Ledger in a browser
start evidence/ledger.html   # Windows
open evidence/ledger.html    # macOS
```

---

## The Bug

`POST /payment` has no idempotency check. When the service's internal retry loop fires after a successful charge, it charges the backend a second time — creating two transactions for one logical payment.

```
Expected logical payments : 1
Actual transactions       : 2
BUG REPRODUCED [OK]
```

---

## The Workflow

### Step 1 — Reproduce the Bug
`reproduce_bug.py` demonstrates the duplicate-payment bug deterministically.

### Step 2 — Generate Competing Hypotheses
IBM Bob reads the bug report and generates two mutually exclusive hypotheses:

| ID | Claim | Experiment |
|----|-------|------------|
| **H1** | Duplicate caused by **client-side retry** | `disable_frontend_retry` |
| **H2** | Duplicate caused by **service-layer retry loop** with no idempotency check | `inject_backend_timeout` |

### Step 3 — Run Controlled Experiments

**Experiment A** — disable client retry completely, service retry loop active:
```
H1 FALSIFIED: duplicate_count=1 even with client retry disabled.
The service loop still executed 2 backend calls.
```

**Experiment B** — single client request, service retry loop active:
```
H2 SUPPORTED: duplicate_count=1 from a SINGLE client request.
Root cause: process_payment() loop does not break after first successful charge.
```

### Step 4 — Apply the Patch
Only after both experiments produce evidence does Bob generate the fix:

- **Idempotency check**: if a transaction for `payment_id` already exists, return it immediately
- **Per-payment lock**: `asyncio.Lock` per `payment_id` prevents TOCTOU race in concurrent requests
- **Break after success**: retry loop exits after the first successful charge

### Step 5 — Adversarial Verification
An independent verifier (separate Bob session) tries to *break* the patch across 4 categories:

| Category | Tests | Result |
|----------|-------|--------|
| Regression | 3 | ✅ PASS |
| Edge cases | 6 | ✅ PASS |
| Idempotency | 5 | ✅ PASS |
| Concurrency | 3 | ✅ PASS |
| **Total** | **17** | **17/17 PASS** |

### Step 6 — Evidence Ledger
All evidence is written to `evidence/ledger.html` — a self-contained HTML audit trail:

```
H1 FALSIFIED (red) → H2 SUPPORTED (green) → PATCH VERIFIED (green)
```

---

## Repository Structure

```
├── reproduce_bug.py              # Bug reproduction script
├── bug_report.md                 # Bug report with H1/H2 hypotheses
├── pytest.ini
│
├── service/
│   ├── main_buggy.py             # Original buggy service
│   ├── main_patched.py           # Fixed service (idempotency enforced)
│   ├── main.py                   # Active service (switched by demo)
│   ├── db.py                     # In-memory transaction store
│   └── config.py                 # Runtime config (env vars)
│
├── mock_backend/
│   └── main.py                   # Simulated payment backend
│
├── experiment_templates/
│   ├── disable_frontend_retry.py # Experiment A — tests H1
│   └── inject_backend_timeout.py # Experiment B — tests H2
│
├── tests/
│   └── test_bug_exists.py        # 6 tests proving the bug exists
│
├── adversarial_suite/
│   ├── conftest.py               # Fixture: patched service + result writer
│   ├── test_regression.py        # Normal payment still works
│   ├── test_edge_cases.py        # Boundary conditions
│   ├── test_idempotency.py       # Same payment_id semantics
│   └── test_concurrency.py       # Concurrent duplicate requests
│
├── tools/
│   ├── ledger_cli.py             # CLI for updating the Evidence Ledger
│   ├── render_ledger.py          # Renders evidence_ledger.json → ledger.html
│   └── run_experiment.py         # Runs a named experiment template
│
├── bob/
│   ├── orchestrator_prompt.md    # IBM Bob system prompt (debugging orchestrator)
│   └── verifier_prompt.md        # IBM Bob system prompt (adversarial verifier)
│
├── evidence/
│   ├── hypotheses_H1_H2.json     # Generated hypotheses
│   ├── evidence_H1.json          # Experiment A output
│   ├── evidence_H2.json          # Experiment B output
│   ├── adversarial_results.json  # 17 adversarial test results
│   ├── evidence_ledger.json      # Complete audit record
│   └── ledger.html               # Human-readable Evidence Ledger
│
├── demo/
│   ├── run_demo.py               # End-to-end demo runner
│   ├── presenter_script.md       # 3-minute narration script
│   └── reference_ledger.html     # Pre-generated ledger (dry-run fallback)
│
└── schemas/                      # JSON schemas for all evidence artifacts
```

---

## IBM Bob's Role

Bob performs the **reasoning** work. Deterministic Python tooling performs the **measurement** work.

| Bob does | Python tooling does |
|----------|---------------------|
| Hypothesis generation | Experiment execution |
| Experiment selection | Evidence collection |
| Evidence interpretation | Test execution |
| Causal conclusion | Ledger generation |
| Patch generation | HTML rendering |
| Adversarial orchestration | Result writing |

Bob does **not** perform measurements. Bob interprets measurements and makes decisions.

---

## Test Results

```
tests/test_bug_exists.py                         6 passed
adversarial_suite/test_concurrency.py            3 passed
adversarial_suite/test_edge_cases.py             6 passed
adversarial_suite/test_idempotency.py            5 passed
adversarial_suite/test_regression.py             3 passed
─────────────────────────────────────────────────────────
TOTAL                                           23 passed
```

---

## Evidence Chain

```
BUG (reproduce_bug.py)
 ↓
H1 / H2 (hypotheses_H1_H2.json)
 ↓
Experiment A → evidence_H1.json → H1 FALSIFIED
 ↓
Experiment B → evidence_H2.json → H2 SUPPORTED
 ↓
Causal conclusion → root_cause in evidence_ledger.json
 ↓
Patch (service/main_patched.py)
 ↓
23 tests pass
 ↓
adversarial_results.json → PATCH_VERIFIED
 ↓
ledger.html
```

Every link is executable. No step is fabricated.

---

## Built With

- [IBM Bob](https://www.ibm.com/products/watsonx-ai) — AI orchestration and reasoning
- [FastAPI](https://fastapi.tiangolo.com/) — Payment service and mock backend
- [pytest](https://pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) — Test execution
- [httpx](https://www.python-httpx.org/) — Async HTTP client
