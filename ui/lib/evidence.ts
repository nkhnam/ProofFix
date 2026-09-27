import adversarialResults from "../../evidence/adversarial_results.json";
import evidenceH1 from "../../evidence/evidence_H1.json";
import evidenceH2 from "../../evidence/evidence_H2.json";
import evidenceLedger from "../../evidence/evidence_ledger.json";
import hypotheses from "../../evidence/hypotheses_H1_H2.json";

export const REPOSITORY_EVIDENCE = {
  adversarialResults,
  evidenceH1,
  evidenceH2,
  evidenceLedger,
  hypotheses,
} as const;

export const ADVERSARIAL_COUNT = REPOSITORY_EVIDENCE.adversarialResults.length;
export const TOTAL_TEST_COUNT = 23;
export const BUG_TEST_COUNT = TOTAL_TEST_COUNT - ADVERSARIAL_COUNT;

export const PATCH_DIFF = {
  before: [
    "# BUG: No idempotency check here -- we go straight to the backend",
    "try:",
    "    backend_resp = _call_backend(req.payment_id, req.amount, req.currency, attempt)",
    "except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:",
    "    raise HTTPException(status_code=502, detail=f\"Backend call failed: {exc}\")",
    "",
    "# Record the transaction unconditionally -- no duplicate check",
    "tx = Transaction(...)",
    "store.add(tx)",
  ],
  after: [
    "# Acquire per-payment_id lock to prevent TOCTOU race in concurrent requests",
    "lock = await _get_payment_lock(req.payment_id)",
    "async with lock:",
    "    # IDEMPOTENCY CHECK: return existing transaction if already processed",
    "    existing = [tx for tx in store.list() if tx.payment_id == req.payment_id]",
    "    if existing:",
    "        return PaymentResponse(transaction_ids=[tx.transaction_id for tx in existing], ...)",
    "",
    "    response = await _call_backend(req.payment_id, req.amount)",
    "    store.add(tx)",
    "    # FIX 3: return immediately after first successful charge",
    "    return PaymentResponse(transaction_ids=[tx.transaction_id], status=\"ok\")",
  ],
} as const;

export type EvidenceRecord = (typeof REPOSITORY_EVIDENCE.adversarialResults)[number];

export function categoryLabel(category: string): string {
  return category.replace("_", " ").toUpperCase();
}
