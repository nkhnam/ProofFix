/**
 * Static evidence data derived from the real evidence/*.json files.
 * Used in Demo Mode so the full flow works without a live backend.
 * All data is verbatim from the repository evidence artifacts.
 */

import type {
  Hypothesis,
  ExperimentEvidence,
  AdversarialResult,
  EvidenceLedger,
} from "./types";

export const HYPOTHESES: Hypothesis[] = [
  {
    id: "H1",
    claim: "The duplicate is caused by frontend/client retry behavior.",
    causal_mechanism:
      "Client retries POST /payment with the same payment_id after a timeout. The service processes both requests independently.",
    observable_if_true:
      "Disabling client retry (MAX_RETRIES=0, single request) eliminates the duplicate.",
    observable_if_false:
      "A single client request still creates 2 transactions.",
    experiment_template: "disable_frontend_retry",
    status: "FALSIFIED",
    evidence_file: "evidence/evidence_H1.json",
    evidence_summary:
      "H1 FALSIFIED: duplicate_count=1 even with client retry disabled (MAX_RETRIES=0). The service retry loop (SERVICE_RETRY_ON_TIMEOUT=1) still executed 2 backend calls, creating 2 transactions. Client retry behavior is NOT the root cause.",
  },
  {
    id: "H2",
    claim:
      "The duplicate is caused by service-layer retry behavior with no idempotency check.",
    causal_mechanism:
      "The service's retry loop (SERVICE_RETRY_ON_TIMEOUT) executes all configured attempts even after a successful charge, without checking if payment_id was already processed.",
    observable_if_true:
      "A single client request (no client retry) with SERVICE_RETRY_ON_TIMEOUT=1 creates 2 transactions.",
    observable_if_false:
      "Service retry disabled (SERVICE_RETRY_ON_TIMEOUT=0) and single request creates only 1 transaction.",
    experiment_template: "inject_backend_timeout",
    status: "SUPPORTED",
    evidence_file: "evidence/evidence_H2.json",
    evidence_summary:
      "H2 SUPPORTED: duplicate_count=1 from a SINGLE client request (no client retry). The service retry loop executed 2 backend calls, creating 2 transactions. Root cause: service/main.py process_payment() loop does not break after first successful charge — no idempotency check prevents duplicate transactions.",
  },
];

export const EVIDENCE_H1: ExperimentEvidence = {
  experiment_id: "disable_frontend_retry_c9346f2f",
  hypothesis_id: "H1",
  template_name: "disable_frontend_retry",
  intervention:
    "MAX_RETRIES=0 — client sends payment request exactly once, no client-side retry",
  baseline:
    "Client retries payment on failure (MAX_RETRIES=1); service retry loop active",
  transactions_created: 2,
  duplicate_count: 1,
  retry_log_entries: [
    "attempt 1: POST /charge payment_id=EXP-A-001",
    "attempt 1: response status=200",
    "attempt 2: POST /charge payment_id=EXP-A-001",
    "attempt 2: response status=200",
  ],
  backend_calls: 2,
  result: "FALSIFIED",
  reason:
    "H1 FALSIFIED: duplicate_count=1 even with client retry disabled (MAX_RETRIES=0). The service retry loop (SERVICE_RETRY_ON_TIMEOUT=1) still executed 2 backend calls, creating 2 transactions. Client retry behavior is NOT the root cause.",
  raw_evidence: [
    {
      transaction_id: "0670ac18-cce7-466d-b4f7-0e2d185da5fc",
      payment_id: "EXP-A-001",
      amount: 50.0,
      status: "charged",
      created_at: 1790403472.3231685,
    },
    {
      transaction_id: "339f0344-307e-47a3-99a4-65642cfd7f45",
      payment_id: "EXP-A-001",
      amount: 50.0,
      status: "charged",
      created_at: 1790403472.3244333,
    },
  ],
  timestamp: "2026-09-26T06:17:52.325155+00:00",
};

export const EVIDENCE_H2: ExperimentEvidence = {
  experiment_id: "inject_backend_timeout_05303f1d",
  hypothesis_id: "H2",
  template_name: "inject_backend_timeout",
  intervention:
    "SERVICE_RETRY_ON_TIMEOUT=1 — service retry loop executes multiple backend calls per request",
  baseline:
    "SERVICE_RETRY_ON_TIMEOUT=0 — service makes exactly one backend call per request",
  transactions_created: 2,
  duplicate_count: 1,
  retry_log_entries: [
    "attempt 1: POST /charge payment_id=EXP-B-001",
    "attempt 1: response status=200",
    "attempt 2: POST /charge payment_id=EXP-B-001",
    "attempt 2: response status=200",
  ],
  backend_calls: 2,
  result: "SUPPORTED",
  reason:
    "H2 SUPPORTED: duplicate_count=1 from a SINGLE client request (no client retry). The service retry loop executed 2 backend calls, creating 2 transactions. Root cause: service/main.py process_payment() loop does not break after first successful charge — no idempotency check prevents duplicate transactions.",
  raw_evidence: [
    {
      transaction_id: "3b188b22-eb44-4c3a-a60f-74506ea070ac",
      payment_id: "EXP-B-001",
      amount: 50.0,
      status: "charged",
      created_at: 1790403473.08556,
    },
    {
      transaction_id: "6082c196-600b-42f5-97b0-bac2397fe0f7",
      payment_id: "EXP-B-001",
      amount: 50.0,
      status: "charged",
      created_at: 1790403473.0866024,
    },
  ],
  timestamp: "2026-09-26T06:17:53.087400+00:00",
};

export const ADVERSARIAL_RESULTS: AdversarialResult[] = [
  {
    test_id: "ADV-97b49ae9",
    test_name: "test_concurrent_duplicate_requests_create_one_transaction",
    category: "concurrency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.04,
  },
  {
    test_id: "ADV-8dbdefca",
    test_name: "test_concurrent_different_payments_both_succeed",
    category: "concurrency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-d6342246",
    test_name: "test_high_concurrency_duplicate_creates_one_transaction",
    category: "concurrency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
  {
    test_id: "ADV-68507ba3",
    test_name: "test_zero_amount_payment_rejected",
    category: "edge_cases",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-99a87a4f",
    test_name: "test_negative_amount_payment_rejected",
    category: "edge_cases",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-7336e512",
    test_name: "test_missing_payment_id_rejected",
    category: "edge_cases",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
  {
    test_id: "ADV-92ff5bfb",
    test_name: "test_missing_amount_rejected",
    category: "edge_cases",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-5acea319",
    test_name: "test_same_payment_id_five_retries_one_transaction",
    category: "edge_cases",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-6384ddce",
    test_name: "test_very_large_amount_accepted",
    category: "edge_cases",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.05,
  },
  {
    test_id: "ADV-1ab35fbd",
    test_name: "test_same_payment_id_twice_creates_one_transaction",
    category: "idempotency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
  {
    test_id: "ADV-020d68aa",
    test_name: "test_idempotency_both_responses_return_same_transaction_id",
    category: "idempotency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
  {
    test_id: "ADV-278b95f3",
    test_name: "test_different_payment_ids_are_independent",
    category: "idempotency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
  {
    test_id: "ADV-32a228cd",
    test_name: "test_idempotency_survives_service_retry_loop",
    category: "idempotency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
  {
    test_id: "ADV-bb430eb6",
    test_name: "test_original_bug_scenario_fixed",
    category: "idempotency",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-2fe8648f",
    test_name: "test_normal_payment_creates_one_transaction",
    category: "regression",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.02,
  },
  {
    test_id: "ADV-5cedd6c9",
    test_name: "test_different_payments_are_independent",
    category: "regression",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.03,
  },
  {
    test_id: "ADV-e89d9d06",
    test_name: "test_payment_response_contains_transaction_id",
    category: "regression",
    result: "PASS",
    observed: "test passed",
    expected: "test should pass",
    counterexample: null,
    duration_ms: 0.01,
  },
];

export const EVIDENCE_LEDGER: EvidenceLedger = {
  bug_report_summary: "POST /payment retry-induced duplicate payment bug.",
  hypotheses: HYPOTHESES,
  experiments: [
    {
      experiment_id: "disable_frontend_retry_c9346f2f",
      hypothesis_id: "H1",
      template_name: "disable_frontend_retry",
      result: "FALSIFIED",
      duplicate_count: 1,
      transactions_created: 2,
      backend_calls: 2,
      reason:
        "H1 FALSIFIED: duplicate_count=1 even with client retry disabled (MAX_RETRIES=0). The service retry loop (SERVICE_RETRY_ON_TIMEOUT=1) still executed 2 backend calls, creating 2 transactions. Client retry behavior is NOT the root cause.",
      timestamp: "2026-09-26T06:17:52.325155+00:00",
    },
    {
      experiment_id: "inject_backend_timeout_05303f1d",
      hypothesis_id: "H2",
      template_name: "inject_backend_timeout",
      result: "SUPPORTED",
      duplicate_count: 1,
      transactions_created: 2,
      backend_calls: 2,
      reason:
        "H2 SUPPORTED: duplicate_count=1 from a SINGLE client request (no client retry). The service retry loop executed 2 backend calls, creating 2 transactions. Root cause: service/main.py process_payment() loop does not break after first successful charge — no idempotency check prevents duplicate transactions.",
      timestamp: "2026-09-26T06:17:53.087400+00:00",
    },
  ],
  root_cause:
    "H2 CONFIRMED: The service-layer retry loop in process_payment() executes all configured retry attempts even after a successful charge, without checking for an existing transaction for the same payment_id. This is the root cause of duplicate payments. Client-side retry (H1) was experimentally excluded.",
  patch_description:
    "Idempotency fix: (1) Check for existing transaction with same payment_id before charging. (2) Per-payment_id asyncio.Lock prevents TOCTOU race in concurrent requests. (3) Return after first successful charge — do not continue retry loop.",
  patch_file: null,
  regression_results: null,
  adversarial_results: ADVERSARIAL_RESULTS,
  final_verdict: "PATCH_VERIFIED",
  created_at: "2026-09-26T06:17:51.624420+00:00",
  updated_at: "2026-09-26T06:17:54.868602+00:00",
};

// Real code diff: main_buggy.py → main_patched.py (key section)
export const BUGGY_CODE = `@app.post("/payment", response_model=PaymentResponse)
async def process_payment(req: PaymentRequest) -> PaymentResponse:
    """
    INTENTIONAL BUG: retries on 504 but records every
    successful charge — no idempotency key check.
    """
    created_tx_ids: list[str] = []
    last_status: int | None = None
    attempts = config.get_service_retry_on_timeout() + 1

    for attempt in range(attempts):
        try:
            response = await _call_backend(req.payment_id, req.amount)
            last_status = response.status_code

            if response.status_code == 504:
                continue  # retry on timeout

            response.raise_for_status()

            # NO idempotency check — records every charge
            tx = Transaction(
                transaction_id=str(uuid.uuid4()),
                payment_id=req.payment_id,
                amount=req.amount,
                status="charged",
            )
            store.add(tx)
            created_tx_ids.append(tx.transaction_id)
            # BUG: loop continues — does not break here

        except (httpx.HTTPStatusError, httpx.RequestError):
            continue

    if not created_tx_ids:
        raise HTTPException(status_code=502, detail="...")

    return PaymentResponse(
        payment_id=req.payment_id,
        transaction_ids=created_tx_ids,
        status="ok" if len(created_tx_ids) == 1
               else "duplicate_charge_warning",
    )`;

export const PATCHED_CODE = `# Per-payment_id locks — prevent concurrent TOCTOU races
_payment_locks: dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()

@app.post("/payment", response_model=PaymentResponse)
async def process_payment(req: PaymentRequest) -> PaymentResponse:
    """
    FIX 1: Idempotency check — return existing tx if already processed.
    FIX 2: Per-payment_id lock prevents concurrent TOCTOU races.
    FIX 3: Return immediately after first successful charge.
    """
    # FIX 2: acquire per-payment_id lock
    lock = await _get_payment_lock(req.payment_id)
    async with lock:
        # FIX 1: idempotency check
        existing = [tx for tx in store.list()
                    if tx.payment_id == req.payment_id]
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

                # FIX 3: return after first successful charge
                return PaymentResponse(
                    payment_id=req.payment_id,
                    transaction_ids=[tx.transaction_id],
                    status="ok",
                )

            except (httpx.HTTPStatusError, httpx.RequestError):
                continue

        raise HTTPException(status_code=502, detail="...")`;
