// ─── Evidence & Ledger types ──────────────────────────────────────────────────

export type HypothesisStatus = "PENDING" | "SUPPORTED" | "FALSIFIED";

export interface Hypothesis {
  id: string;
  claim: string;
  causal_mechanism: string;
  observable_if_true: string;
  observable_if_false: string;
  experiment_template: string;
  status: HypothesisStatus;
  evidence_file: string | null;
  evidence_summary?: string;
}

export interface ExperimentEvidence {
  experiment_id: string;
  hypothesis_id: string;
  template_name: string;
  intervention: string;
  baseline: string;
  transactions_created: number;
  duplicate_count: number;
  retry_log_entries: string[];
  backend_calls: number;
  result: "SUPPORTED" | "FALSIFIED";
  reason: string;
  raw_evidence: Transaction[];
  timestamp: string;
}

export interface AdversarialResult {
  test_id: string;
  test_name: string;
  category: "regression" | "idempotency" | "concurrency" | "edge_cases";
  result: "PASS" | "FAIL";
  observed: string;
  expected: string;
  counterexample: string | null;
  duration_ms: number;
}

export interface LedgerExperiment {
  experiment_id: string;
  hypothesis_id: string;
  template_name: string;
  result: "SUPPORTED" | "FALSIFIED";
  duplicate_count: number;
  transactions_created: number;
  backend_calls: number;
  reason: string;
  timestamp: string;
}

export interface EvidenceLedger {
  bug_report_summary: string;
  hypotheses: Hypothesis[];
  experiments: LedgerExperiment[];
  root_cause: string;
  patch_description: string;
  patch_file: string | null;
  regression_results: unknown | null;
  adversarial_results: AdversarialResult[];
  final_verdict: string;
  created_at: string;
  updated_at: string;
}

// ─── Backend API types ────────────────────────────────────────────────────────

export interface Transaction {
  transaction_id: string;
  payment_id: string;
  amount: number;
  status: string;
  created_at: number;
  currency?: string;
  backend_charge_id?: string | null;
}

export interface PaymentResponse {
  payment_id: string;
  transaction_ids: string[];
  status: string;
  amount?: number;
  currency?: string;
  attempt?: number;
  transactions_in_store?: number;
}

export interface TransactionsResponse {
  count: number;
  transactions: Transaction[];
}

// ─── UI state ─────────────────────────────────────────────────────────────────

export type Stage =
  | "landing"
  | "reproduce"
  | "hypotheses"
  | "experiments"
  | "patch"
  | "adversarial"
  | "verdict";

export type StageStatus = "pending" | "active" | "complete";

export interface WorkflowStage {
  id: Stage;
  label: string;
  shortLabel: string;
  status: StageStatus;
}
