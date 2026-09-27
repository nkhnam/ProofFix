"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronRight,
  CircleDot,
  FlaskConical,
  Gavel,
  LockKeyhole,
  Play,
  RotateCcw,
  Scale,
  ShieldCheck,
  Terminal,
  X,
  Zap,
} from "lucide-react";
import { getTransactions, postPayment, resetStore } from "../lib/api";
import {
  ADVERSARIAL_COUNT,
  BUG_TEST_COUNT,
  PATCH_DIFF,
  REPOSITORY_EVIDENCE,
  TOTAL_TEST_COUNT,
  categoryLabel,
} from "../lib/evidence";
import type { Stage, Transaction } from "../lib/types";

const stages: { id: Stage; label: string; icon: typeof Activity }[] = [
  { id: "landing", label: "Case intake", icon: Gavel },
  { id: "reproduce", label: "Reproduce bug", icon: AlertTriangle },
  { id: "hypotheses", label: "Competing hypotheses", icon: Scale },
  { id: "experiments", label: "Controlled experiments", icon: FlaskConical },
  { id: "patch", label: "Bob repair proposal", icon: Zap },
  { id: "adversarial", label: "Adversarial verification", icon: ShieldCheck },
  { id: "verdict", label: "Final verdict", icon: Gavel },
];

const stageIndex = (stage: Stage) => stages.findIndex((item) => item.id === stage);

export default function Page() {
  const [stage, setStage] = useState<Stage>("landing");
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [reproductionDone, setReproductionDone] = useState(false);
  const [adversarialVisible, setAdversarialVisible] = useState(0);
  const [ledgerOpen, setLedgerOpen] = useState(false);

  const currentIndex = stageIndex(stage);
  const demoEvidence = REPOSITORY_EVIDENCE.evidenceH2;
  const categories = useMemo(() => {
    const grouped = new Map<string, number>();
    for (const result of REPOSITORY_EVIDENCE.adversarialResults) {
      grouped.set(result.category, (grouped.get(result.category) ?? 0) + 1);
    }
    return [...grouped.entries()];
  }, []);

  useEffect(() => {
    if (stage !== "adversarial" || mode !== "demo") return;
    setAdversarialVisible(0);
    const timer = window.setInterval(() => {
      setAdversarialVisible((value) => {
        if (value >= ADVERSARIAL_COUNT) {
          window.clearInterval(timer);
          return value;
        }
        return value + 1;
      });
    }, 70);
    return () => window.clearInterval(timer);
  }, [stage, mode]);

  function goTo(next: Stage) {
    setError("");
    setNotice("");
    setStage(next);
  }

  async function runLiveReproduction() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await resetStore();
      await postPayment("PAY-001", 100, 1);
      await postPayment("PAY-001", 100, 2);
      const result = await getTransactions();
      setTransactions(result.transactions);
      setReproductionDone(result.count >= 2);
      setNotice(`Live runtime observed ${result.count} transaction records.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Live reproduction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runReproduction() {
    if (mode === "demo") {
      setBusy(true);
      setError("");
      setNotice("");
      window.setTimeout(() => {
        setReproductionDone(true);
        setBusy(false);
        setNotice("Repository evidence loaded. Demo result is deterministic.");
      }, 420);
      return;
    }
    await runLiveReproduction();
  }

  function startDemo() {
    setMode("demo");
    setReproductionDone(false);
    goTo("reproduce");
  }

  const workflowComplete = currentIndex >= 6;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark"><Gavel size={17} /></div>
          <span>PROOFFIX</span><b>/</b><strong>BUG COURT</strong>
        </div>
        <div className="topbar-meta">
          <span className="bob-chip"><CircleDot size={13} /> IBM Bob <em>evidence agent</em></span>
          <span className="ready"><span className="status-dot" /> SYSTEM READY</span>
        </div>
      </header>

      <div className="body-grid">
        <aside className="sidebar">
          <div className="case-kicker">ACTIVE CASE <span>001</span></div>
          <h1>Duplicate<br />Payment</h1>
          <p className="case-id">PAY-001 <span>·</span> HIGH SEVERITY</p>

          <div className="mode-switch" role="group" aria-label="Execution mode">
            <button className={mode === "demo" ? "selected" : ""} onClick={() => setMode("demo")}><Zap size={13} /> DEMO</button>
            <button className={mode === "live" ? "selected" : ""} onClick={() => setMode("live")}><Activity size={13} /> LIVE</button>
          </div>
          <p className="mode-note">{mode === "demo" ? "Repository evidence · deterministic" : "FastAPI runtime · observed now"}</p>

          <nav className="workflow-nav" aria-label="Investigation workflow">
            <div className="nav-label">INVESTIGATION PATH</div>
            {stages.map((item, index) => {
              const Icon = item.icon;
              const complete = index < currentIndex || (item.id === "reproduce" && reproductionDone);
              const active = item.id === stage;
              return (
                <button key={item.id} className={`stage-nav ${active ? "active" : ""}`} onClick={() => index <= currentIndex && goTo(item.id)} disabled={index > currentIndex}>
                  <span className={`stage-number ${complete ? "complete" : ""}`}>{complete ? <Check size={13} /> : <Icon size={13} />}</span>
                  <span>{item.label}</span>
                  {active && <ChevronRight size={14} className="nav-arrow" />}
                </button>
              );
            })}
          </nav>

          <div className="sidebar-foot">
            <div><span>Evidence items</span><strong>{TOTAL_TEST_COUNT}</strong></div>
            <div><span>Adversarial</span><strong>{ADVERSARIAL_COUNT}/{ADVERSARIAL_COUNT}</strong></div>
            <div><span>Verdict</span><strong className={workflowComplete ? "green" : "amber"}>{workflowComplete ? "VERIFIED" : "OPEN"}</strong></div>
          </div>
        </aside>

        <section className="workspace">
          <div className="workspace-head">
            <div><span className="eyebrow">CASE FILE / PAY-001</span><h2>{stageTitle(stage)}</h2></div>
            <div className="source-badge"><span className={mode === "demo" ? "amber-dot" : "green-dot"} /> {mode === "demo" ? "DEMO MODE" : "LIVE MODE"}</div>
          </div>
          {error && <div className="alert error"><AlertTriangle size={16} /><span>{error}</span><button onClick={runReproduction}><RotateCcw size={14} /> RETRY</button></div>}
          {notice && <div className="alert success"><Check size={16} /><span>{notice}</span></div>}
          <div className="workspace-scroll">
            {stage === "landing" && <Landing onStart={startDemo} />}
            {stage === "reproduce" && <Reproduce busy={busy} done={reproductionDone} mode={mode} transactions={transactions} onRun={runReproduction} onNext={() => goTo("hypotheses")} />}
            {stage === "hypotheses" && <Hypotheses onNext={() => goTo("experiments")} />}
            {stage === "experiments" && <Experiments onNext={() => goTo("patch")} />}
            {stage === "patch" && <Patch onNext={() => goTo("adversarial")} />}
            {stage === "adversarial" && <Adversarial visible={mode === "demo" ? adversarialVisible : ADVERSARIAL_COUNT} categories={categories} onNext={() => goTo("verdict")} />}
            {stage === "verdict" && <Verdict onEvidence={() => setLedgerOpen(true)} onRestart={() => { setStage("landing"); setReproductionDone(false); }} />}
          </div>
        </section>
      </div>

      <footer className="statusbar"><span><Terminal size={13} /> EVIDENCE LEDGER <b>CONNECTED</b></span><span>source: repository / evidence/*.json</span><span>{BUG_TEST_COUNT} regression <i>·</i> {ADVERSARIAL_COUNT} adversarial <i>·</i> {workflowComplete ? "VERIFIED" : "INVESTIGATION OPEN"}</span></footer>
      {ledgerOpen && <Ledger onClose={() => setLedgerOpen(false)} />}
    </main>
  );
}

function stageTitle(stage: Stage) {
  return ({ landing: "Case intake", reproduce: "Reproduce the failure", hypotheses: "Competing explanations", experiments: "Controlled experiments", patch: "Proposed repair", adversarial: "Adversarial verification", verdict: "Court verdict" })[stage];
}

function Landing({ onStart }: { onStart: () => void }) {
  return <div className="landing-stage fade-in"><div className="hero-copy"><div className="stamp"><span className="status-dot" /> CASE OPEN / 2026.09.27</div><h3>One payment.<br /><em>Two charges.</em></h3><p>A payment request may be processed more than once when the backend times out after successfully processing the first request.</p><button className="primary-cta" onClick={onStart}><Play size={16} fill="currentColor" /> START INVESTIGATION <ArrowRight size={16} /></button></div><div className="case-facts"><div className="facts-heading">CASE STATUS <span>OPEN</span></div><Fact label="Component" value="Payment Service" /><Fact label="Detected" value="Duplicate transaction" /><Fact label="Investigation" value="Not started" /><div className="chain-preview"><span>BUG</span><ArrowRight size={14} /><span>CAUSE</span><ArrowRight size={14} /><span>PROOF</span></div></div></div>;
}
function Fact({ label, value }: { label: string; value: string }) { return <div className="fact"><span>{label}</span><strong>{value}</strong></div>; }

function Reproduce({ busy, done, mode, transactions, onRun, onNext }: { busy: boolean; done: boolean; mode: string; transactions: Transaction[]; onRun: () => void; onNext: () => void }) {
  return <StageFrame eyebrow="01 / REPRODUCTION" title="Can we make it happen?" description="Establish the failure before forming a theory. Same logical payment, repeated execution path." action={<button className="primary-cta compact" onClick={onRun} disabled={busy}>{busy ? <><span className="spinner" /> RUNNING...</> : <><Play size={15} fill="currentColor" /> RUN REPRODUCTION</>}</button>} footer={done ? <button className="text-cta" onClick={onNext}>Continue to hypotheses <ArrowRight size={15} /></button> : null}>
    <div className="repro-grid"><div className="code-panel"><div className="panel-bar"><span><span className="window-dot red" /><span className="window-dot amber" /><span className="window-dot green" /></span><span>request.json</span><span>POST /payment</span></div><pre><code><span className="dim">POST</span> /payment{"\n\n"}{"{"}{"\n"}  <span className="key">"payment_id"</span>: <span className="string">"PAY-001"</span>,{"\n"}  <span className="key">"amount"</span>: <span className="number">100</span>,{"\n"}  <span className="key">"currency"</span>: <span className="string">"USD"</span>{"\n"}{"}"}</code></pre></div><div className={`result-panel ${done ? "failed" : ""}`}><div className="result-label">{done ? <><X size={17} /> BUG REPRODUCED</> : <><CircleDot size={16} /> AWAITING RUN</>}</div>{done ? <><div className="metric-pair"><div><span>Expected transactions</span><strong>1</strong></div><div><span>Actual transactions</span><strong className="red-text">{mode === "live" ? transactions.length : 2}</strong></div></div><p className="result-note">Duplicate charge detected for one logical payment.</p><div className="flow-line"><span>REQUEST</span><ArrowRight size={13} /><span>CHARGE</span><ArrowRight size={13} /><span className="red-text">RETRY</span><ArrowRight size={13} /><span className="red-text">DUPLICATE</span></div></> : <p className="empty-copy">Run the controlled reproduction to observe the transaction count.</p>}</div></div>
  </StageFrame>;
}

function StageFrame({ eyebrow, title, description, action, footer, children }: { eyebrow: string; title: string; description: string; action?: React.ReactNode; footer?: React.ReactNode; children: React.ReactNode }) { return <div className="stage-frame fade-in"><div className="stage-intro"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3><p>{description}</p></div>{action}</div>{children}{footer && <div className="stage-footer">{footer}</div>}</div>; }

function Hypotheses({ onNext }: { onNext: () => void }) {
  const hs = REPOSITORY_EVIDENCE.hypotheses.map((hypothesis) => ({
    ...hypothesis,
    status: hypothesis.id === "H1" ? REPOSITORY_EVIDENCE.evidenceH1.result : REPOSITORY_EVIDENCE.evidenceH2.result,
  }));
  return <StageFrame eyebrow="02 / HYPOTHESES" title="Two explanations enter." description="No guess becomes a conclusion until a controlled intervention separates it from the alternative." action={<button className="text-cta" onClick={onNext}>Run experiments <ArrowRight size={15} /></button>}><div className="hypothesis-grid">{hs.map((h) => <article className={`hypothesis ${h.status === "FALSIFIED" ? "falsified" : "supported"}`} key={h.id}><div className="hypothesis-top"><span className="hypothesis-id">{h.id}</span><span className="pill pending">EVIDENCE LOADED</span></div><h4>{h.claim}</h4><p>{h.causal_mechanism}</p><div className="hypothesis-rule"><span>OBSERVABLE IF TRUE</span>{h.observable_if_true}</div><div className="hypothesis-result"><span>REPOSITORY VERDICT</span><strong>{h.status === "FALSIFIED" ? <><X size={14} /> FALSIFIED</> : <><Check size={14} /> SUPPORTED</>}</strong></div></article>)}</div></StageFrame>;
}

function Experiments({ onNext }: { onNext: () => void }) { const experiments = [REPOSITORY_EVIDENCE.evidenceH1, REPOSITORY_EVIDENCE.evidenceH2]; return <StageFrame eyebrow="03 / EXPERIMENTS" title="Change one variable." description="The ledger records what was changed, what was held constant, and what the service actually did." action={<button className="text-cta" onClick={onNext}>Review repair <ArrowRight size={15} /></button>}><div className="experiment-list">{experiments.map((e, index) => <article className="experiment" key={e.experiment_id}><div className="experiment-id">E-0{index + 1}</div><div className="experiment-main"><div className="experiment-title"><h4>{e.hypothesis_id} / {e.template_name.replaceAll("_", " ")}</h4><span className={`pill ${e.result === "SUPPORTED" ? "pass" : "fail"}`}>{e.result}</span></div><div className="experiment-details"><div><span>INTERVENTION</span>{e.intervention}</div><div><span>OBSERVED</span>{e.transactions_created} transactions / {e.backend_calls} backend calls</div></div><div className="terminal-log">{e.retry_log_entries.map((line) => <div key={line}><span className="log-time">[evidence]</span> {line}</div>)}<div className="log-result">&gt; {e.result === "SUPPORTED" ? "Root cause supported." : "Hypothesis eliminated."}</div></div></div></article>)}</div></StageFrame>; }

function Patch({ onNext }: { onNext: () => void }) { return <StageFrame eyebrow="04 / IBM BOB REPAIR" title="A repair with a reason." description="Bob proposes a causal fix only after the evidence points to the retry path. The diff below is derived from the repository implementation." action={<button className="primary-cta compact" onClick={onNext}><LockKeyhole size={15} /> ACCEPT PATCH</button>}><div className="root-cause"><span>ROOT CAUSE IDENTIFIED</span><strong>{String(REPOSITORY_EVIDENCE.evidenceLedger.root_cause)}</strong></div><div className="diff-grid"><DiffColumn label="main_buggy.py" tone="before" lines={PATCH_DIFF.before} /><DiffColumn label="main_patched.py" tone="after" lines={PATCH_DIFF.after} /></div><div className="bob-note"><div className="bob-avatar">B</div><div><strong>IBM Bob / repair proposal</strong><p>Idempotency check + per-payment lock + return after first successful charge.</p></div><span className="pill pass">EVIDENCE-BOUND</span></div></StageFrame>; }
function DiffColumn({ label, tone, lines }: { label: string; tone: string; lines: readonly string[] }) { return <div className={`diff-column ${tone}`}><div className="panel-bar"><span>{tone === "before" ? "−" : "+"} {label}</span><span>{tone === "before" ? "BUGGY" : "PATCHED"}</span></div><pre>{lines.map((line, index) => <code key={`${line}-${index}`}><span className="line-no">{String(index + 1).padStart(2, "0")}</span>{line || " "}{"\n"}</code>)}</pre></div>; }

function Adversarial({ visible, categories, onNext }: { visible: number; categories: [string, number][]; onNext: () => void }) { const results = REPOSITORY_EVIDENCE.adversarialResults.slice(0, visible); return <StageFrame eyebrow="05 / ADVERSARIAL VERIFICATION" title="Can the repair survive attack?" description="An independent suite tries duplicate requests, races, invalid inputs and regression paths against the patched implementation." action={visible >= ADVERSARIAL_COUNT ? <button className="primary-cta compact" onClick={onNext}><Gavel size={15} /> ISSUE VERDICT</button> : <span className="running-label"><span className="spinner" /> ATTACK SUITE RUNNING</span>}><div className="attack-summary"><div className="attack-count"><strong>{visible}</strong><span>/ {ADVERSARIAL_COUNT} tests passed</span></div><div className="progress-track"><div style={{ width: `${(visible / ADVERSARIAL_COUNT) * 100}%` }} /></div><div className="attack-status">{visible >= ADVERSARIAL_COUNT ? <><Check size={16} /> ALL ATTACKS REJECTED</> : "Enumerating attack surface..."}</div></div><div className="category-row">{categories.map(([category, count]) => <div key={category}><span className="green-dot" />{categoryLabel(category)}<strong>{visible >= ADVERSARIAL_COUNT ? `${count}/${count}` : "—"}</strong></div>)}</div><div className="test-stream">{results.map((result) => <div className="test-row" key={result.test_id}><Check size={14} /><span>{result.test_name.replace("test_", "")}</span><small>{categoryLabel(result.category)}</small><b>PASS</b></div>)}</div></StageFrame>; }

function Verdict({ onEvidence, onRestart }: { onEvidence: () => void; onRestart: () => void }) { return <div className="verdict-stage fade-in"><div className="verdict-seal"><Gavel size={26} /><span>CASE #001</span><strong>VERIFIED</strong><small>PATCH SURVIVED ADVERSARIAL REVIEW</small></div><div className="verdict-chain">{["BUG", "CAUSE IDENTIFIED", "PATCH APPLIED", "ATTACKED", "SURVIVED", "VERIFIED"].map((item, index) => <div key={item}><span className={index === 5 ? "chain-final" : ""}>{index < 5 ? <Check size={14} /> : <ShieldCheck size={14} />}</span>{item}{index < 5 && <ArrowRight size={14} />}</div>)}</div><div className="verdict-grid"><Fact label="Root cause" value="Retry path without idempotency" /><Fact label="Patch" value="Lock + existing transaction check" /><Fact label="Verification" value={`${TOTAL_TEST_COUNT} tests passed`} /><Fact label="Adversarial" value={`${ADVERSARIAL_COUNT}/${ADVERSARIAL_COUNT} passed`} /></div><div className="verdict-actions"><button className="primary-cta" onClick={onEvidence}>VIEW EVIDENCE LEDGER <ArrowRight size={16} /></button><button className="secondary-cta" onClick={onRestart}><RotateCcw size={15} /> RUN AGAIN</button></div></div>; }

function Ledger({ onClose }: { onClose: () => void }) { const ledger = REPOSITORY_EVIDENCE.evidenceLedger; return <div className="ledger-backdrop" onClick={onClose}><aside className="ledger-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-head"><div><span className="eyebrow">AUDIT TRAIL</span><h3>Evidence Ledger</h3></div><button className="icon-button" onClick={onClose} aria-label="Close ledger"><X size={18} /></button></div><p>{String(ledger.bug_report_summary)}</p><div className="ledger-chain">{["HYPOTHESIS", "EXPERIMENT", "OBSERVATION", "PATCH", "VERIFICATION"].map((item) => <div key={item}><span><Check size={13} /></span>{item}</div>)}</div><div className="ledger-rows">{ledger.experiments.map((experiment) => <div key={experiment.experiment_id}><span>{experiment.hypothesis_id}</span><strong>{experiment.result}</strong><small>{experiment.transactions_created} transactions / {experiment.backend_calls} backend calls</small></div>)}</div><div className="drawer-verdict"><span>FINAL VERDICT</span><strong>{String(ledger.final_verdict)}</strong></div></aside></div>; }
