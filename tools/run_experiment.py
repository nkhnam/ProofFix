"""
Experiment runner CLI — invoked by Bob as a deterministic tool.

Usage:
    python tools/run_experiment.py --template disable_frontend_retry
    python tools/run_experiment.py --template inject_backend_timeout
    python tools/run_experiment.py --template disable_frontend_retry --output evidence/evidence_H1.json

Templates:
    disable_frontend_retry  → tests H1 (client retry hypothesis)
    inject_backend_timeout  → tests H2 (service retry hypothesis)

Output:
    Writes a JSON evidence file matching schemas/evidence_schema.json.
    Prints a human-readable summary to stdout.

Exit codes:
    0 — experiment completed and evidence written
    1 — experiment failed or template not found
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Resolve repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEMPLATES = {
    "disable_frontend_retry": {
        "hypothesis_id": "H1",
        "module": "experiment_templates.disable_frontend_retry",
        "intervention": "MAX_RETRIES=0 — client sends payment request exactly once, no client-side retry",
        "baseline": "Client retries payment on failure (MAX_RETRIES=1); service retry loop active",
    },
    "inject_backend_timeout": {
        "hypothesis_id": "H2",
        "module": "experiment_templates.inject_backend_timeout",
        "intervention": "SERVICE_RETRY_ON_TIMEOUT=1 — service retry loop executes multiple backend calls per request",
        "baseline": "SERVICE_RETRY_ON_TIMEOUT=0 — service makes exactly one backend call per request",
    },
}

DEFAULT_OUTPUT = {
    "disable_frontend_retry": "evidence/evidence_H1.json",
    "inject_backend_timeout": "evidence/evidence_H2.json",
}


def build_evidence(template_name: str, result: dict) -> dict:
    """Construct the full evidence document from template metadata + experiment result."""
    meta = TEMPLATES[template_name]
    now = datetime.now(timezone.utc).isoformat()

    return {
        "experiment_id": f"{template_name}_{uuid.uuid4().hex[:8]}",
        "hypothesis_id": meta["hypothesis_id"],
        "template_name": template_name,
        "intervention": meta["intervention"],
        "baseline": meta["baseline"],
        "transactions_created": result["transactions_created"],
        "duplicate_count": result["duplicate_count"],
        "retry_log_entries": result["retry_log_entries"],
        "backend_calls": result["backend_calls"],
        "result": result["result"],
        "reason": result["reason"],
        "raw_evidence": result.get("raw_evidence", []),
        "timestamp": now,
    }


async def run_template(template_name: str) -> dict:
    """Dynamically import and run the experiment template."""
    import importlib
    meta = TEMPLATES[template_name]
    module = importlib.import_module(meta["module"])
    return await module.run()


def print_summary(evidence: dict) -> None:
    """Print a human-readable summary of the experiment result."""
    result = evidence["result"]
    color_code = "\033[32m" if result == "SUPPORTED" else "\033[31m" if result == "FALSIFIED" else "\033[33m"
    reset = "\033[0m"

    print()
    print("=" * 70)
    print(f"  EXPERIMENT: {evidence['template_name']}")
    print(f"  Hypothesis: {evidence['hypothesis_id']}")
    print(f"  Intervention: {evidence['intervention']}")
    print("-" * 70)
    print(f"  Transactions created : {evidence['transactions_created']}")
    print(f"  Duplicate count      : {evidence['duplicate_count']}")
    print(f"  Backend calls        : {evidence['backend_calls']}")
    print(f"  Result               : {color_code}{result}{reset}")
    print(f"  Reason               : {evidence['reason']}")
    print("=" * 70)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="BUG COURT experiment runner")
    parser.add_argument(
        "--template",
        required=True,
        choices=list(TEMPLATES.keys()),
        help="Experiment template to run",
    )
    parser.add_argument(
        "--output",
        help="Path to write evidence JSON (default: evidence/evidence_H{1,2}.json)",
    )
    args = parser.parse_args()

    template_name = args.template
    output_path = Path(args.output) if args.output else REPO_ROOT / DEFAULT_OUTPUT[template_name]

    print(f"[BUG COURT] Running experiment: {template_name}")
    print(f"[BUG COURT] Evidence will be written to: {output_path}")

    try:
        result = asyncio.run(run_template(template_name))
    except Exception as exc:
        print(f"[BUG COURT] ERROR: experiment failed: {exc}", file=sys.stderr)
        return 1

    evidence = build_evidence(template_name, result)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, default=str)

    print_summary(evidence)
    print(f"[BUG COURT] Evidence written to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
