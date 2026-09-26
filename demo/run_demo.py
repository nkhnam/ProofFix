"""
BUG COURT — End-to-End Demo Runner

Runs the complete workflow from bug reproduction to verified patch in one command.

Usage:
    python demo/run_demo.py           # Full live demo
    python demo/run_demo.py --dry-run # Uses pre-generated evidence (fallback mode)

Flow:
    1. Show original bug (duplicate payment)
    2. Run Experiment A (H1 falsified)
    3. Run Experiment B (H2 supported)
    4. Apply idempotency patch
    5. Run adversarial verification suite
    6. Finalize Evidence Ledger
    7. Render ledger.html
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"


def banner(text: str, color: str = CYAN) -> None:
    width = 70
    print()
    print(color + "=" * width + RESET)
    print(color + f"  {text}" + RESET)
    print(color + "=" * width + RESET)


def step(n: int, text: str) -> None:
    print(f"\n{BOLD}{CYAN}[Step {n}]{RESET} {text}")


def ok(text: str) -> None:
    print(f"  {GREEN}[OK]{RESET} {text}")


def fail(text: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {text}")


def info(text: str) -> None:
    print(f"  {YELLOW}[INFO]{RESET} {text}")


def run_python(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a python command from REPO_ROOT."""
    result = subprocess.run(
        [sys.executable] + cmd,
        cwd=REPO_ROOT,
        capture_output=False,
    )
    if check and result.returncode != 0:
        fail(f"Command failed: {' '.join(cmd)}")
        sys.exit(1)
    return result


def run_python_capture(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable] + cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout + result.stderr


def restore_buggy_service() -> None:
    """Ensure service/main.py is the BUGGY version before starting demo."""
    buggy = REPO_ROOT / "service" / "main_buggy.py"
    dst = REPO_ROOT / "service" / "main.py"
    shutil.copy2(buggy, dst)


def demo_step_1_show_bug() -> None:
    """Step 1: Demonstrate the original bug."""
    step(1, "ORIGINAL BUG — Duplicate Payment Reproduction")
    info("Simulating client-side retry: same payment_id submitted twice...")
    info("Service has no idempotency check — both requests are processed.")
    print()

    import asyncio
    os.environ["SERVICE_RETRY_ON_TIMEOUT"] = "0"
    os.environ["INJECT_TIMEOUT"] = "false"

    async def reproduce():
        import importlib
        from mock_backend.main import app as backend_app, _charges, _seen
        from service.db import store
        import service.main_buggy as svc_main
        importlib.reload(svc_main)
        import httpx
        from httpx import AsyncClient, ASGITransport

        store.reset()
        _charges.clear()
        _seen.clear()

        backend_client = AsyncClient(
            transport=ASGITransport(app=backend_app), base_url="http://mock-backend"
        )

        async def patched_call_backend(payment_id, amount):
            return await backend_client.post(
                "/charge", json={"payment_id": payment_id, "amount": amount}, timeout=5.0
            )

        original = svc_main._call_backend
        svc_main._call_backend = patched_call_backend
        svc_client = AsyncClient(transport=ASGITransport(app=svc_main.app), base_url="http://svc")

        try:
            await svc_client.post("/payment", json={"payment_id": "DEMO-001", "amount": 99.99})
            await svc_client.post("/payment", json={"payment_id": "DEMO-001", "amount": 99.99})
            count = store.count()
        finally:
            svc_main._call_backend = original
            await backend_client.aclose()
            await svc_client.aclose()
            store.reset()

        return count

    count = asyncio.run(reproduce())

    print(f"  {BOLD}Expected logical payments : 1{RESET}")
    print(f"  {BOLD}Actual transactions       : {count}{RESET}")
    if count >= 2:
        print(f"\n  {RED}{BOLD}BUG CONFIRMED: {count} transactions for 1 payment{RESET}")
    else:
        fail("Bug did not reproduce!")
        sys.exit(1)


def demo_step_2_hypotheses() -> None:
    """Step 2: Generate competing hypotheses."""
    step(2, "HYPOTHESIS GENERATION — Two Competing Hypotheses")

    hypotheses = [
        {
            "id": "H1",
            "claim": "The duplicate is caused by frontend/client retry behavior.",
            "causal_mechanism": "Client retries POST /payment with the same payment_id after a timeout. The service processes both requests independently.",
            "observable_if_true": "Disabling client retry (MAX_RETRIES=0, single request) eliminates the duplicate.",
            "observable_if_false": "A single client request still creates 2 transactions.",
            "experiment_template": "disable_frontend_retry",
            "status": "PENDING",
            "evidence_file": None,
        },
        {
            "id": "H2",
            "claim": "The duplicate is caused by service-layer retry behavior with no idempotency check.",
            "causal_mechanism": "The service's retry loop (SERVICE_RETRY_ON_TIMEOUT) executes all configured attempts even after a successful charge, without checking if payment_id was already processed.",
            "observable_if_true": "A single client request (no client retry) with SERVICE_RETRY_ON_TIMEOUT=1 creates 2 transactions.",
            "observable_if_false": "Service retry disabled (SERVICE_RETRY_ON_TIMEOUT=0) and single request creates only 1 transaction.",
            "experiment_template": "inject_backend_timeout",
            "status": "PENDING",
            "evidence_file": None,
        },
    ]

    out_path = REPO_ROOT / "evidence" / "hypotheses_H1_H2.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hypotheses, f, indent=2)

    for h in hypotheses:
        info(f"{h['id']}: {h['claim']}")

    ok("Hypotheses written to evidence/hypotheses_H1_H2.json")


def demo_step_3_init_ledger() -> None:
    step(3, "EVIDENCE LEDGER — Initialize")
    run_python(["tools/ledger_cli.py", "init"])
    run_python(["tools/ledger_cli.py", "update-hypotheses", "--input", "evidence/hypotheses_H1_H2.json"])
    ok("Ledger initialized with hypotheses.")


def demo_step_4_experiment_a() -> None:
    step(4, "EXPERIMENT A — Test H1 (disable_frontend_retry)")
    info("Intervention: send payment ONCE (no client retry). Service retry loop active.")
    info("Question: does the duplicate still occur without client retry?")
    print()
    run_python(["tools/run_experiment.py", "--template", "disable_frontend_retry"])
    run_python(["tools/ledger_cli.py", "update-evidence", "--hypothesis", "H1", "--evidence-file", "evidence/evidence_H1.json"])

    ev = json.loads((REPO_ROOT / "evidence" / "evidence_H1.json").read_text())
    if ev["result"] == "FALSIFIED":
        print(f"\n  {RED}{BOLD}H1 FALSIFIED:{RESET} {ev['reason']}")
    else:
        info(f"H1 result: {ev['result']}")


def demo_step_5_experiment_b() -> None:
    step(5, "EXPERIMENT B — Test H2 (inject_backend_timeout)")
    info("Intervention: single client request, service retry loop active.")
    info("Question: does a single request cause duplicate transactions?")
    print()
    run_python(["tools/run_experiment.py", "--template", "inject_backend_timeout"])
    run_python(["tools/ledger_cli.py", "update-evidence", "--hypothesis", "H2", "--evidence-file", "evidence/evidence_H2.json"])

    ev = json.loads((REPO_ROOT / "evidence" / "evidence_H2.json").read_text())
    if ev["result"] == "SUPPORTED":
        print(f"\n  {GREEN}{BOLD}H2 SUPPORTED:{RESET} {ev['reason']}")
    else:
        info(f"H2 result: {ev['result']}")

    # Show ledger root cause
    ledger_path = REPO_ROOT / "evidence" / "evidence_ledger.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        rc = ledger.get("root_cause")
        if rc:
            print(f"\n  {BOLD}ROOT CAUSE IDENTIFIED:{RESET}")
            print(f"  {rc}")


def demo_step_6_apply_patch() -> None:
    step(6, "PATCH GENERATION — Apply Idempotency Fix")
    info("Copying main_patched.py over main.py to apply the fix...")

    src = REPO_ROOT / "service" / "main_patched.py"
    dst = REPO_ROOT / "service" / "main.py"

    # Back up original
    bak = REPO_ROOT / "service" / "main_buggy.py"
    if not bak.exists():
        shutil.copy2(dst, bak)

    shutil.copy2(src, dst)

    patch_desc = (
        "Idempotency fix: (1) Check for existing transaction with same payment_id before charging. "
        "(2) Per-payment_id asyncio.Lock prevents TOCTOU race in concurrent requests. "
        "(3) Return after first successful charge — do not continue retry loop."
    )

    run_python(["tools/ledger_cli.py", "add-patch", "--description", patch_desc])
    ok("Patch applied: service/main.py now has idempotency enforcement.")


def demo_step_7_adversarial_verification() -> None:
    step(7, "ADVERSARIAL VERIFICATION — Independent Test Suite Attacks the Patch")
    info("Running all 4 adversarial test categories:")
    info("  - regression: normal payment still works")
    info("  - edge_cases: boundary conditions")
    info("  - concurrency: concurrent duplicate requests")
    info("  - idempotency: same payment_id semantics")
    print()

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "adversarial_suite/", "-v", "--tb=short"],
        cwd=REPO_ROOT,
    )

    if result.returncode == 0:
        print(f"\n  {GREEN}{BOLD}ALL ADVERSARIAL TESTS PASSED{RESET}")
    else:
        fail("Some adversarial tests FAILED — patch is rejected.")
        sys.exit(1)

    run_python(["tools/ledger_cli.py", "add-adversarial", "--results", "evidence/adversarial_results.json"])


def demo_step_8_finalize() -> None:
    step(8, "FINALIZE — Evidence Ledger and HTML Report")

    run_python(["tools/ledger_cli.py", "finalize", "--verdict", "PATCH_VERIFIED"])
    run_python(["tools/render_ledger.py"])

    ledger_html = REPO_ROOT / "evidence" / "ledger.html"
    print(f"\n  {GREEN}{BOLD}PATCH VERIFIED{RESET}")
    print(f"\n  Evidence Ledger: {ledger_html}")
    ok("ledger.html rendered. Open it in a browser to view the full audit trail.")


def demo_dry_run() -> None:
    """Dry run using pre-generated evidence — safe fallback for demos."""
    banner("BUG COURT DEMO (DRY RUN — pre-generated evidence)", YELLOW)
    print(f"\n  {YELLOW}Dry run mode: using pre-generated evidence files.{RESET}")

    # Ensure evidence files exist
    evidence_dir = REPO_ROOT / "evidence"
    required = ["evidence_H1.json", "evidence_H2.json", "adversarial_results.json"]
    missing = [f for f in required if not (evidence_dir / f).exists()]

    if missing:
        info(f"Missing pre-generated evidence: {missing}")
        info("Running live experiments to generate evidence first...")
        run_demo()
        return

    # Show results from existing files
    banner("RESULTS (from pre-generated evidence)", CYAN)

    h1 = json.loads((evidence_dir / "evidence_H1.json").read_text())
    h2 = json.loads((evidence_dir / "evidence_H2.json").read_text())
    adv = json.loads((evidence_dir / "adversarial_results.json").read_text())

    print(f"\n  H1 result : {RED}{h1['result']}{RESET} — {h1['reason'][:80]}...")
    print(f"  H2 result : {GREEN}{h2['result']}{RESET} — {h2['reason'][:80]}...")
    print(f"\n  Adversarial tests: {sum(1 for t in adv if t['result']=='PASS')}/{len(adv)} passed")

    run_python(["tools/render_ledger.py"])
    ok("ledger.html re-rendered from pre-generated evidence.")


def run_demo() -> None:
    """Run the complete live demo."""
    start = time.monotonic()
    banner("BUG COURT — Scientific Debugging Workflow", CYAN)
    print(f"  {CYAN}bug -> hypotheses -> controlled experiment -> evidence -> falsification -> repair -> verified{RESET}")

    restore_buggy_service()
    demo_step_1_show_bug()
    demo_step_2_hypotheses()
    demo_step_3_init_ledger()
    demo_step_4_experiment_a()
    demo_step_5_experiment_b()
    demo_step_6_apply_patch()
    demo_step_7_adversarial_verification()
    demo_step_8_finalize()

    elapsed = time.monotonic() - start
    banner(f"DEMO COMPLETE in {elapsed:.1f}s", GREEN)
    print(f"\n  Total time: {elapsed:.1f}s {'(under 3 min!)' if elapsed < 180 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BUG COURT end-to-end demo")
    parser.add_argument("--dry-run", action="store_true", help="Use pre-generated evidence")
    args = parser.parse_args()

    if args.dry_run:
        demo_dry_run()
    else:
        run_demo()


if __name__ == "__main__":
    main()
