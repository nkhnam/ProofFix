# BUG COURT — Presenter Script

## One-Sentence Pitch

> **BUG COURT forces AI-generated debugging through scientific falsification and adversarial verification — producing an auditable Evidence Ledger that proves not just *what* was fixed, but *why*.**

---

## Demo Setup (before presenting)

```bash
cd bug-court
pip install fastapi uvicorn httpx pydantic pytest pytest-asyncio anyio
python demo/run_demo.py  # run once to verify setup
```

Open `evidence/ledger.html` in a browser to confirm it renders correctly.

---

## Narration Script

### 0:00 — Introduction (30s)

> "Every AI debugger today works the same way: see a bug, generate a hypothesis, write a patch.
> But what if the hypothesis is wrong?
> BUG COURT changes that. It's a scientific workflow that *forces* the AI to run controlled experiments
> before it's allowed to write a single line of fix."

---

### 0:30 — Show the Bug (30s)

*[Terminal shows Step 1]*

> "Here's the bug: a customer submits a payment. A timeout occurs. The client retries.
> The service has no idempotency check. Result: two charges for one payment."

*[Console shows:]*
```
Expected logical payments : 1
Actual transactions       : 2
BUG CONFIRMED
```

---

### 1:00 — Competing Hypotheses (30s)

*[Terminal shows Step 2]*

> "Most tools would immediately generate a fix. BUG COURT forces Bob to generate two *competing* hypotheses.
> H1: the duplicate is the client's fault — it retried.
> H2: the duplicate is the service's fault — it has a broken retry loop with no idempotency check.
> These are different bugs. They require different fixes. Only one is true."

---

### 1:30 — H1 Falsified (30s)

*[Terminal shows Step 4 — Experiment A]*

> "BUG COURT runs a controlled experiment. It disables client retry completely and sends the
> payment exactly once. Watch what happens."

*[Console shows:]*
```
H1 FALSIFIED: duplicate_count=1 even with client retry disabled.
```

> "The duplicate still occurred. Client retry is NOT the root cause. H1 is falsified with evidence."

---

### 2:00 — H2 Supported (30s)

*[Terminal shows Step 5 — Experiment B]*

> "The second experiment: keep the service retry loop active and send a single request.
> One request. No client retry."

*[Console shows:]*
```
H2 SUPPORTED: duplicate_count=1 from a SINGLE client request.
Root cause: service/main.py retry loop does not break after first successful charge.
```

> "Now we have causal evidence. The bug is in the service. Only now can Bob generate a patch."

---

### 2:30 — Patch + Adversarial Verification (45s)

*[Terminal shows Steps 6-7]*

> "Bob applies the fix: an idempotency check plus a per-payment lock.
> But we don't just run happy-path tests. We spawn an *independent adversarial verifier*
> whose entire job is to break the patch."

*[17 tests run across 4 categories]*

> "Regression, edge cases, concurrency, idempotency. 17 tests. All pass."

---

### 3:15 — Evidence Ledger (15s)

*[Browser opens ledger.html]*

> "The Evidence Ledger is the artifact. Every claim is traceable to an experiment.
> Every hypothesis status has evidence. Every test result is here.
> Not just 'the bug is fixed' — but *why* it was caused, *how* it was confirmed, and *who* verified it."

*[Shows: H1 FALSIFIED (red) → H2 SUPPORTED (green) → PATCH VERIFIED (green)]*

---

## Key Demo Points

| Moment | What to Highlight |
|---|---|
| Step 1 | Bug reproduces deterministically — this is not flaky |
| Step 4 | H1 FALSIFIED — the AI cannot skip to patching |
| Step 5 | H2 SUPPORTED with *evidence* — causal claim backed by data |
| Step 7 | Concurrency test — would fail against unpatched service |
| ledger.html | Full audit trail — show red/green hypothesis status |

---

## Backup Plan (if live demo fails)

```bash
python demo/run_demo.py --dry-run
```

Open `evidence/ledger.html` in browser — pre-generated from last successful run.

---

## Total Demo Time: ~3.5 seconds execution + narration = 3 minutes

The command completes in 3-4 seconds. The rest is narration.
