"""
Evidence Ledger HTML renderer.

Reads evidence/evidence_ledger.json and produces evidence/ledger.html —
a self-contained static HTML page showing the complete BUG COURT audit trail.

Usage:
    python tools/render_ledger.py
    python tools/render_ledger.py --input evidence/evidence_ledger.json --output evidence/ledger.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "evidence" / "evidence_ledger.json"
DEFAULT_OUTPUT = REPO_ROOT / "evidence" / "ledger.html"


def status_badge(status: str) -> str:
    colors = {
        "SUPPORTED": "#16a34a",
        "FALSIFIED": "#dc2626",
        "PENDING": "#d97706",
        "PATCH_VERIFIED": "#16a34a",
        "PATCH_REJECTED": "#dc2626",
        "PASS": "#16a34a",
        "FAIL": "#dc2626",
        "H2": "#16a34a",
        "H1": "#dc2626",
    }
    color = colors.get(status, "#6b7280")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:3px;font-weight:600;font-size:0.85em;">{status}</span>'
    )


def render(ledger: dict) -> str:
    hypotheses = ledger.get("hypotheses", [])
    experiments = ledger.get("experiments", [])
    root_cause = ledger.get("root_cause") or "Not yet determined"
    patch_desc = ledger.get("patch_description") or "No patch applied"
    adversarial = ledger.get("adversarial_results") or []
    verdict = ledger.get("final_verdict", "PENDING")
    bug_summary = ledger.get("bug_report_summary", "")

    # Hypothesis rows
    hyp_rows = ""
    for h in hypotheses:
        hyp_rows += f"""
        <tr>
          <td style="padding:10px;font-weight:600;">{h.get('id','')}</td>
          <td style="padding:10px;">{h.get('claim','')}</td>
          <td style="padding:10px;">{h.get('causal_mechanism','')}</td>
          <td style="padding:10px;">{h.get('experiment_template','')}</td>
          <td style="padding:10px;">{status_badge(h.get('status','PENDING'))}</td>
        </tr>"""

    # Experiment rows
    exp_rows = ""
    for e in experiments:
        exp_rows += f"""
        <tr>
          <td style="padding:10px;font-family:monospace;font-size:0.85em;">{e.get('experiment_id','')}</td>
          <td style="padding:10px;">{e.get('hypothesis_id','')}</td>
          <td style="padding:10px;">{e.get('template_name','')}</td>
          <td style="padding:10px;">{e.get('transactions_created','')}</td>
          <td style="padding:10px;">{e.get('duplicate_count','')}</td>
          <td style="padding:10px;">{status_badge(e.get('result',''))}</td>
        </tr>"""

    if not exp_rows:
        exp_rows = '<tr><td colspan="6" style="padding:10px;color:#6b7280;">No experiments run yet.</td></tr>'

    # Adversarial test rows
    adv_rows = ""
    for t in adversarial:
        ce = t.get("counterexample") or ""
        adv_rows += f"""
        <tr>
          <td style="padding:10px;font-family:monospace;font-size:0.85em;">{t.get('test_id','')}</td>
          <td style="padding:10px;">{t.get('test_name','')}</td>
          <td style="padding:10px;">{t.get('category','')}</td>
          <td style="padding:10px;">{status_badge(t.get('result',''))}</td>
          <td style="padding:10px;">{t.get('observed','')}</td>
          <td style="padding:10px;color:#dc2626;">{ce}</td>
        </tr>"""

    if not adv_rows:
        adv_rows = '<tr><td colspan="6" style="padding:10px;color:#6b7280;">No adversarial tests run yet.</td></tr>'

    verdict_color = "#16a34a" if verdict == "PATCH_VERIFIED" else "#dc2626" if verdict == "PATCH_REJECTED" else "#d97706"

    regression = ledger.get("regression_results")
    reg_html = ""
    if regression:
        passed = regression.get("passed", 0)
        failed = regression.get("failed", 0)
        reg_html = f"""
        <section>
          <h2>Regression Tests</h2>
          <p>Passed: <strong>{passed}</strong> &nbsp; Failed: <strong>{failed}</strong></p>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BUG COURT — Evidence Ledger</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; font-size: 14px;
         line-height: 1.6; background: #f7f8fa; color: #1f2328; margin: 0; padding: 24px; }}
  .container {{ max-width: 960px; margin: 0 auto; background: #fff; border: 1px solid #e5e7eb;
                border-radius: 6px; padding: 32px; }}
  h1 {{ font-size: 1.6em; margin: 0 0 4px; }}
  .subtitle {{ color: #57606a; margin: 0 0 32px; font-size: 0.95em; }}
  h2 {{ font-size: 1.1em; color: #1f2328; border-bottom: 2px solid #e5e7eb;
        padding-bottom: 6px; margin: 32px 0 16px; }}
  section {{ margin-bottom: 32px; }}
  .flow {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
           background: #f7f8fa; border: 1px solid #e5e7eb; border-radius: 6px;
           padding: 16px 20px; margin-bottom: 24px; }}
  .flow-step {{ background: #3b82d4; color: #fff; padding: 4px 12px; border-radius: 3px;
                font-size: 0.85em; font-weight: 600; }}
  .flow-arrow {{ color: #57606a; font-size: 1.1em; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th {{ background: #f7f8fa; text-align: left; padding: 10px; font-weight: 600;
        border-bottom: 2px solid #e5e7eb; color: #57606a; font-size: 0.85em;
        text-transform: uppercase; letter-spacing: 0.04em; }}
  tr:nth-child(even) {{ background: #f7f8fa; }}
  td {{ border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
  .verdict-box {{ text-align: center; padding: 24px; border-radius: 6px;
                  border: 2px solid {verdict_color}; margin-top: 32px; }}
  .verdict-label {{ font-size: 2em; font-weight: 700; color: {verdict_color}; }}
  .bug-box {{ background: #fff5f5; border: 1px solid #fecaca; border-radius: 6px;
              padding: 16px; margin-bottom: 8px; }}
  .root-cause-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;
                     padding: 16px; }}
  .patch-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px;
                padding: 16px; }}
  .footer {{ text-align: center; color: #57606a; font-size: 0.78em; margin-top: 40px;
             padding-top: 16px; border-top: 1px solid #e5e7eb; }}
</style>
</head>
<body>
<div class="container">
  <h1>BUG COURT — Evidence Ledger</h1>
  <p class="subtitle">Scientific debugging audit trail &mdash; generated automatically</p>

  <!-- Causal chain flow -->
  <div class="flow">
    <span class="flow-step">BUG</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">HYPOTHESES</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">EXPERIMENTS</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">EVIDENCE</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">FALSIFICATION</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">PATCH</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">ADVERSARIAL TESTS</span>
    <span class="flow-arrow">&#8594;</span>
    <span class="flow-step">{verdict}</span>
  </div>

  <!-- Bug Report -->
  <section>
    <h2>Bug Report</h2>
    <div class="bug-box">
      <strong>Symptom:</strong> {bug_summary}
    </div>
  </section>

  <!-- Hypotheses -->
  <section>
    <h2>Competing Hypotheses</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th><th>Claim</th><th>Causal Mechanism</th><th>Experiment</th><th>Status</th>
        </tr>
      </thead>
      <tbody>{hyp_rows}</tbody>
    </table>
  </section>

  <!-- Experiments -->
  <section>
    <h2>Controlled Experiments &amp; Evidence</h2>
    <table>
      <thead>
        <tr>
          <th>Experiment ID</th><th>Hyp.</th><th>Template</th>
          <th>Txns Created</th><th>Duplicates</th><th>Result</th>
        </tr>
      </thead>
      <tbody>{exp_rows}</tbody>
    </table>
  </section>

  <!-- Root Cause -->
  <section>
    <h2>Root Cause Conclusion</h2>
    <div class="root-cause-box">
      {root_cause}
    </div>
  </section>

  <!-- Patch -->
  <section>
    <h2>Applied Patch</h2>
    <div class="patch-box">
      {patch_desc}
    </div>
  </section>

  {reg_html}

  <!-- Adversarial Tests -->
  <section>
    <h2>Adversarial Verification Results</h2>
    <table>
      <thead>
        <tr>
          <th>Test ID</th><th>Test Name</th><th>Category</th>
          <th>Result</th><th>Observed</th><th>Counterexample</th>
        </tr>
      </thead>
      <tbody>{adv_rows}</tbody>
    </table>
  </section>

  <!-- Final Verdict -->
  <div class="verdict-box">
    <div class="verdict-label">{verdict}</div>
    <p style="color:#57606a;margin:8px 0 0;">
      {'All adversarial tests passed. The patch is verified.' if verdict == 'PATCH_VERIFIED' else
       'Some adversarial tests failed. The patch requires revision.' if verdict == 'PATCH_REJECTED' else
       'Verification in progress.'}
    </p>
  </div>

  <div class="footer">Made with IBM Bob</div>
</div>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="BUG COURT Evidence Ledger HTML renderer")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to evidence_ledger.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write ledger.html")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[render_ledger] ERROR: ledger file not found: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, encoding="utf-8") as f:
        ledger = json.load(f)

    html = render(ledger)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[render_ledger] HTML rendered: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
