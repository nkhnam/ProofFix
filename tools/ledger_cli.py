"""
Evidence Ledger CLI — invoked by Bob to update the ledger incrementally.

Usage:
    python tools/ledger_cli.py init
    python tools/ledger_cli.py update-hypotheses --input evidence/hypotheses_H1_H2.json
    python tools/ledger_cli.py update-evidence --hypothesis H1 --evidence-file evidence/evidence_H1.json
    python tools/ledger_cli.py update-evidence --hypothesis H2 --evidence-file evidence/evidence_H2.json
    python tools/ledger_cli.py add-patch --description "Added idempotency check"
    python tools/ledger_cli.py add-adversarial --results evidence/adversarial_results.json
    python tools/ledger_cli.py finalize --verdict PATCH_VERIFIED

The ledger is written to evidence/evidence_ledger.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "evidence" / "evidence_ledger.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if LEDGER_PATH.exists():
        with open(LEDGER_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(data: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"[ledger_cli] Ledger updated: {LEDGER_PATH}")


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    """Initialize an empty ledger."""
    ledger = {
        "bug_report_summary": "POST /payment retry-induced duplicate payment bug.",
        "hypotheses": [],
        "experiments": [],
        "root_cause": None,
        "patch_description": None,
        "patch_file": None,
        "regression_results": None,
        "adversarial_results": None,
        "final_verdict": "PENDING",
        "created_at": _now(),
        "updated_at": _now(),
    }
    _save(ledger)
    print("[ledger_cli] Ledger initialized.")


def cmd_update_hypotheses(args) -> None:
    """Load hypotheses from a JSON file and write them to the ledger."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ledger_cli] ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        hypotheses = json.load(f)

    if not isinstance(hypotheses, list):
        # Support both array and {hypotheses: [...]} formats
        hypotheses = hypotheses.get("hypotheses", hypotheses)

    ledger = _load()
    if not ledger:
        cmd_init(args)
        ledger = _load()

    ledger["hypotheses"] = hypotheses
    _save(ledger)
    print(f"[ledger_cli] Hypotheses updated ({len(hypotheses)} hypotheses).")


def cmd_update_evidence(args) -> None:
    """Attach experiment evidence to a hypothesis in the ledger."""
    evidence_path = Path(args.evidence_file)
    if not evidence_path.exists():
        print(f"[ledger_cli] ERROR: evidence file not found: {evidence_path}", file=sys.stderr)
        sys.exit(1)

    with open(evidence_path, encoding="utf-8") as f:
        evidence = json.load(f)

    ledger = _load()
    if not ledger:
        print("[ledger_cli] ERROR: ledger not initialized. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    hypothesis_id = args.hypothesis
    result = evidence.get("result", "UNKNOWN")
    status_map = {"FALSIFIED": "FALSIFIED", "SUPPORTED": "SUPPORTED", "UNKNOWN": "PENDING"}
    new_status = status_map.get(result, "PENDING")

    # Update hypothesis status
    updated = False
    for h in ledger.get("hypotheses", []):
        if h.get("id") == hypothesis_id:
            h["status"] = new_status
            h["evidence_file"] = str(evidence_path)
            h["evidence_summary"] = evidence.get("reason", "")
            updated = True
            break

    if not updated:
        print(f"[ledger_cli] WARNING: hypothesis {hypothesis_id} not found in ledger.")

    # Add to experiments list
    exp_entry = {
        "experiment_id": evidence.get("experiment_id", ""),
        "hypothesis_id": evidence.get("hypothesis_id", hypothesis_id),
        "template_name": evidence.get("template_name", ""),
        "result": evidence.get("result", ""),
        "duplicate_count": evidence.get("duplicate_count", 0),
        "transactions_created": evidence.get("transactions_created", 0),
        "backend_calls": evidence.get("backend_calls", 0),
        "reason": evidence.get("reason", ""),
        "timestamp": evidence.get("timestamp", _now()),
    }
    ledger.setdefault("experiments", []).append(exp_entry)

    # Set root cause if H2 is SUPPORTED and H1 is FALSIFIED
    h_map = {h["id"]: h for h in ledger.get("hypotheses", [])}
    if h_map.get("H1", {}).get("status") == "FALSIFIED" and h_map.get("H2", {}).get("status") == "SUPPORTED":
        ledger["root_cause"] = (
            "H2 CONFIRMED: The service-layer retry loop in process_payment() executes all "
            "configured retry attempts even after a successful charge, without checking for "
            "an existing transaction for the same payment_id. This is the root cause of "
            "duplicate payments. Client-side retry (H1) was experimentally excluded."
        )

    _save(ledger)
    print(f"[ledger_cli] Evidence for {hypothesis_id} updated: status={new_status}")


def cmd_add_patch(args) -> None:
    """Record the patch applied to fix the bug."""
    ledger = _load()
    if not ledger:
        print("[ledger_cli] ERROR: ledger not initialized.", file=sys.stderr)
        sys.exit(1)

    ledger["patch_description"] = args.description
    if hasattr(args, "file") and args.file:
        ledger["patch_file"] = args.file

    _save(ledger)
    print(f"[ledger_cli] Patch recorded: {args.description}")


def cmd_add_adversarial(args) -> None:
    """Load adversarial test results and attach to ledger."""
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"[ledger_cli] ERROR: results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    ledger = _load()
    if not ledger:
        print("[ledger_cli] ERROR: ledger not initialized.", file=sys.stderr)
        sys.exit(1)

    ledger["adversarial_results"] = results
    _save(ledger)
    print(f"[ledger_cli] Adversarial results attached ({len(results)} test results).")


def cmd_finalize(args) -> None:
    """Set the final verdict on the ledger."""
    verdict = args.verdict
    valid = {"PATCH_VERIFIED", "PATCH_REJECTED"}
    if verdict not in valid:
        print(f"[ledger_cli] ERROR: invalid verdict '{verdict}'. Must be one of: {valid}", file=sys.stderr)
        sys.exit(1)

    ledger = _load()
    if not ledger:
        print("[ledger_cli] ERROR: ledger not initialized.", file=sys.stderr)
        sys.exit(1)

    # Guard: require adversarial results before PATCH_VERIFIED
    if verdict == "PATCH_VERIFIED" and not ledger.get("adversarial_results"):
        print(
            "[ledger_cli] ERROR: cannot set PATCH_VERIFIED without adversarial_results. "
            "Run adversarial tests first.",
            file=sys.stderr,
        )
        sys.exit(1)

    ledger["final_verdict"] = verdict
    _save(ledger)
    print(f"[ledger_cli] Final verdict set: {verdict}")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="BUG COURT Evidence Ledger CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    sub.add_parser("init", help="Initialize an empty ledger")

    # update-hypotheses
    p = sub.add_parser("update-hypotheses", help="Load hypotheses from JSON file")
    p.add_argument("--input", required=True, help="Path to hypotheses JSON file")

    # update-evidence
    p = sub.add_parser("update-evidence", help="Attach evidence to a hypothesis")
    p.add_argument("--hypothesis", required=True, help="Hypothesis ID (H1 or H2)")
    p.add_argument("--evidence-file", required=True, help="Path to evidence JSON file")

    # add-patch
    p = sub.add_parser("add-patch", help="Record the applied patch")
    p.add_argument("--description", required=True, help="Patch description")
    p.add_argument("--file", help="Path to patch file (optional)")

    # add-adversarial
    p = sub.add_parser("add-adversarial", help="Attach adversarial test results")
    p.add_argument("--results", required=True, help="Path to adversarial results JSON")

    # finalize
    p = sub.add_parser("finalize", help="Set final verdict")
    p.add_argument(
        "--verdict",
        required=True,
        choices=["PATCH_VERIFIED", "PATCH_REJECTED"],
        help="Final verdict",
    )

    args = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "update-hypotheses": cmd_update_hypotheses,
        "update-evidence": cmd_update_evidence,
        "add-patch": cmd_add_patch,
        "add-adversarial": cmd_add_adversarial,
        "finalize": cmd_finalize,
    }

    try:
        dispatch[args.command](args)
        return 0
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[ledger_cli] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
