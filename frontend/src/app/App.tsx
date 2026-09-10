import { useEffect, useRef, useState } from "react";
import { ConnectionDetails } from "../features/connection/ConnectionDetails";

import { createRun, decideApproval, downloadReview, getEvents, getRun, listRuns, type ReviewExport } from "../api/client";
import type { AgentRun, CandidateSelection, RunEnvelope, RunEvent } from "../api/types";
import { ApprovalGate } from "../features/approval/ApprovalGate";
import { DiffViewer } from "../features/diff/DiffViewer";
import { EvidencePanel } from "../features/evidence/EvidencePanel";
import { Landing } from "../features/landing/Landing";
import { RepositoryHeader } from "../features/repository/RepositoryHeader";
import { RiskQueue } from "../features/risk/RiskQueue";
import { ExecutionTimeline } from "../features/run/ExecutionTimeline";
import { RecordedRunMode } from "../features/run/RecordedRunMode";
import { ValidationPanel } from "../features/run/ValidationPanel";
import { ShieldIcon, ThemeIcon } from "../ui/Icons";
import { applyTheme, getInitialTheme, type Theme } from "../ui/theme";

type ViewState = "idle" | "scanning" | "paused" | "deciding" | "completed" | "rejected" | "failed" | "error";
type Surface = "landing" | "demo";

const defaultRepository = import.meta.env.VITE_DEMO_REPOSITORY || "";

function eventOf(events: RunEvent[], kind: string) {
  return events.find((event) => event.kind === kind);
}

function dependencies(events: RunEvent[]) {
  const event = eventOf(events, "manifest_scanned");
  return (event?.payload.dependencies as { name: string; resolved_version?: string }[] | undefined) || [];
}

function viewFor(run: AgentRun): ViewState {
  return run.status === "waiting_for_approval" ? "paused" : run.status === "completed" ? "completed" : run.status === "cancelled" ? "rejected" : run.status === "running" || run.status === "queued" ? "scanning" : "failed";
}

export function App() {
  const [surface, setSurface] = useState<Surface>(window.location.hash === "#overview" ? "landing" : "demo");
  const [repository, setRepository] = useState("");
  const [trusted, setTrusted] = useState(false);
  const [saved, setSaved] = useState<AgentRun[] | null>(null);
  const [utilityBusy, setUtilityBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState<ReviewExport | null>(null);
  const [exportError, setExportError] = useState<{ message: string; kind: ReviewExport } | null>(null);
  const [exportNotice, setExportNotice] = useState("");
  const exportInFlight = useRef(false);
  const scanRequest = useRef<{ repository: string; key: string; created?: RunEnvelope } | null>(null);
  const operationBusy = useRef(false);
  const activityRequest = useRef(0);
  const [retryChoice, setRetryChoice] = useState<"approved" | "rejected" | null>(null);
  const [state, setState] = useState<ViewState>("idle");
  const [outcome, setOutcome] = useState<RunEnvelope | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState("");
  const [utilityError, setUtilityError] = useState<{ message: string; retry: () => void; retryLabel?: string } | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => applyTheme(theme), [theme]);
  useEffect(() => { setExportError(null); setExportNotice(""); }, [outcome?.run.id]);
  useEffect(() => {
    function syncSurface() {
      if (window.location.hash === "#overview") setSurface("landing");
      if (window.location.hash === "#main") setSurface("demo");
    }
    window.addEventListener("hashchange", syncSurface);
    return () => window.removeEventListener("hashchange", syncSurface);
  }, []);

  function openSurface(next: Surface) {
    setSurface(next);
    window.history.replaceState(null, "", next === "landing" ? "#overview" : "#main");
  }

  const snapshot = eventOf(events, "repository_inspected")?.payload;
  const candidate = outcome?.candidate;
  const validation = eventOf(events, "validation_completed");
  const diff = (eventOf(events, "upgrade_staged")?.payload.diff as string | undefined) || "";
  const evidence = eventOf(events, "evidence_collected");
  const dependencyRows = dependencies(events);

  async function scan() {
    if (operationBusy.current) return;
    if (!trusted) { setError("Confirm that you trust this repository before executing its tests."); return; }
    setRetryChoice(null);
    if (!navigator.onLine) {
      setError("You are offline. Reconnect, then retry the scan.");
      setState("error");
      return;
    }
    setState("scanning");
    setError("");
    operationBusy.current = true;
    try {
      const path = repository.trim();
      if (!scanRequest.current || scanRequest.current.repository !== path) { activityRequest.current += 1; setUtilityError(null); scanRequest.current = { repository: path, key: crypto.randomUUID() }; setOutcome(null); setEvents([]); }
      const request = scanRequest.current;
      const created = request.created || await createRun(path, request.key);
      request.created = created;
      setOutcome(created);
      const timeline = await getEvents(created.run.id);
      setEvents(timeline);
      setState(viewFor(created.run));
      scanRequest.current = null;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The scan could not be completed");
      setState("error");
    } finally {
      operationBusy.current = false;
    }
  }

  async function decide(choice: "approved" | "rejected") {
    if (!outcome?.approval_id || operationBusy.current) return;
    operationBusy.current = true;
    setRetryChoice(choice);
    setState("deciding");
    setError("");
    try {
      const run = await decideApproval(outcome.run.id, outcome.approval_id, choice);
      setOutcome({ ...outcome, run });
      setRetryChoice(null);
      setState(viewFor(run));
      await refreshActivity(run.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The decision could not be recorded");
      setState("error");
    } finally {
      operationBusy.current = false;
    }
  }

  async function refreshActivity(runId: string) {
    const requestId = ++activityRequest.current;
    setUtilityError(null);
    try {
      const timeline = await getEvents(runId);
      if (requestId === activityRequest.current) setEvents(timeline);
    } catch {
      if (requestId === activityRequest.current) setUtilityError({
        message: "Decision saved. Run activity could not refresh.",
        retryLabel: "Retry activity",
        retry: () => void refreshActivity(runId),
      });
    }
  }

  async function loadSaved() {
    setUtilityError(null);
    setUtilityBusy(true);
    try { setSaved(await listRuns()); } catch { setUtilityError({ message: "Run history could not load. Check the local service.", retry: () => void loadSaved() }); } finally { setUtilityBusy(false); }
  }
  async function reopen(run: AgentRun) {
    if (operationBusy.current) return;
    operationBusy.current = true;
    activityRequest.current += 1;
    setUtilityError(null);
    setUtilityBusy(true);
    try {
      const [current, timeline] = await Promise.all([getRun(run.id), getEvents(run.id)]);
      const selection = eventOf(timeline, "candidate_selected")?.payload as unknown as CandidateSelection;
      const approval = eventOf(timeline, "approval_required")?.payload.approval_id as string | undefined;
      setOutcome({ run: current, candidate: selection || null, approval_id: approval || null }); setEvents(timeline); setRepository(current.input_summary); setSaved(null); setError(""); setRetryChoice(null); scanRequest.current = null;
      setState(viewFor(current));
    } catch { setUtilityError({ message: "This run could not be reopened.", retry: () => void reopen(run) }); } finally { setUtilityBusy(false); operationBusy.current = false; }
  }
  async function exportReview(kind: ReviewExport) {
    if (state !== "completed" || !outcome || exportInFlight.current) return;
    exportInFlight.current = true;
    setExportBusy(kind); setExportError(null); setExportNotice("");
    try {
      await downloadReview(outcome.run.id, kind);
      setExportNotice(`${kind === "receipt" ? "Review receipt" : "Reviewed patch"} download started for ${outcome.run.id}.`);
    } catch (caught) {
      setExportError({ message: caught instanceof Error ? caught.message : "The review could not be downloaded. Retry the download.", kind });
    } finally { setExportBusy(null); exportInFlight.current = false; }
  }
  function toggleTheme() {
    setTheme((current) => current === "light" ? "dark" : "light");
  }

  const busy = state === "scanning" || state === "deciding";
  const failure = eventOf(events, "run_failed")?.payload.message;

  if (surface === "landing") {
    return (
      <div className="app-shell console-shell">
        <header className="console-topbar">
          <a className="console-wordmark" href="#main" onClick={() => openSurface("demo")}><ShieldIcon /><h1>Dependency Sentinel</h1></a>
          <nav className="console-nav" aria-label="Section navigation">
            <a href="#pipeline-title">Pipeline</a>
            <a href="#architecture-title">Architecture</a>
            <a href="#invariants-title">Invariants</a>
          </nav>
          <button type="button" className="nav-action" onClick={() => openSurface("demo")}>Open workspace</button>
          <button
            type="button"
            className="theme-action"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
          >
            <ThemeIcon />
          </button>
        </header>
        <Landing onStart={() => openSurface("demo")} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <RepositoryHeader
        onBack={() => openSurface("landing")}
        repository={repository}
        onRepositoryChange={(value) => { setRepository(value); scanRequest.current = null; }}
        onScan={scan}
        isScanning={busy}
        retry={state === "error"}
        trusted={trusted}
        onTrustedChange={setTrusted}
        branch={snapshot?.branch as string | undefined}
        head={snapshot?.head as string | undefined}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <section className="workspace-controls" aria-label="Repository review controls">
        <div className="workspace-toolbar">
          <button type="button" disabled={utilityBusy || busy || !!exportBusy} onClick={loadSaved}>{utilityBusy ? "Loading records…" : "Saved runs"}</button>
          {defaultRepository && <button type="button" disabled={busy} onClick={() => { setRepository(defaultRepository); scanRequest.current = null; }}>Use sample repository</button>}
          {state === "completed" && <div className="review-exports" aria-label="Approved review downloads" aria-busy={!!exportBusy}>
            <button type="button" disabled={!!exportBusy} onClick={() => void exportReview("patch")}>{exportBusy === "patch" ? "Preparing patch…" : "Download reviewed patch"}</button>
            <button type="button" disabled={!!exportBusy} onClick={() => void exportReview("receipt")}>{exportBusy === "receipt" ? "Preparing receipt…" : "Download review receipt"}</button>
          </div>}
        </div>
        {exportNotice && <p className="export-notice" role="status">{exportNotice}</p>}
        {exportError && <div className="export-error" role="alert"><p><strong>Download unavailable.</strong> {exportError.message}</p><button type="button" disabled={!!exportBusy} onClick={() => void exportReview(exportError.kind)}>Retry download</button><button type="button" onClick={() => setExportError(null)}>Dismiss</button></div>}
      </section>
      <ConnectionDetails />
      {utilityError && <div className="error-banner" role="alert"><span>{utilityError.message}</span><button type="button" onClick={utilityError.retry}>{utilityError.retryLabel || "Retry request"}</button><button type="button" onClick={() => setUtilityError(null)}>Dismiss</button></div>}
      {saved && <section className="saved-records"><header><div><h2>Saved runs</h2><p>Latest 50 reviews, stored on this machine.</p></div><button type="button" onClick={() => setSaved(null)}>Close saved runs</button></header>{saved.length ? <ul>{saved.map(run => <li key={run.id}><button type="button" disabled={utilityBusy} onClick={() => void reopen(run)}><strong>{run.input_summary.split("/").filter(Boolean).at(-1) || run.input_summary}</strong><small>{run.input_summary}</small></button><time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time><span className={`run-status ${run.status}`}>{run.status.replaceAll("_", " ")}</span></li>)}</ul> : <p>No saved runs yet. Your first repository review will appear here.</p>}</section>}
      {error && (
        <div className="error-banner" role="alert">
          <span><strong>{retryChoice ? "Decision not confirmed." : "Review needs attention."}</strong> {error}</span>
          <button type="button" onClick={() => retryChoice ? void decide(retryChoice) : void scan()}>{retryChoice ? "Retry decision" : "Try scan again"}</button>
        </div>
      )}

      {state === "scanning" ? (
        <main className="loading-state" aria-live="polite" aria-busy="true">
          <h2>Inspecting repository</h2>
          <p>Checking the manifest, evidence sources and isolated validation path. Test execution can take several minutes; do not submit another scan.</p>
          {outcome?.run.status === "running" && <button className="primary-action" type="button" onClick={() => void reopen(outcome.run)}>Refresh run status</button>}
          <div className="instrument-skeleton" aria-hidden="true">
            <span /><span /><span /><span /><span /><span /><span />
          </div>
        </main>
      ) : !candidate ? (
        <main className="workspace-arrival">
          <section className="empty-state">
          <div className="empty-instrument" aria-hidden="true"><ShieldIcon /></div>
          <h2>{state === "failed" ? "Run did not produce a patch" : "Review your next dependency upgrade"}</h2>
          <p>{typeof failure === "string" ? failure : "Choose a local Python repository with pyproject.toml and uv.lock, then scan for one evidence-backed upgrade."}</p>
          <ol aria-label="Scan safety contract">
            <li>Read the source checkout</li>
            <li>Stage changes in isolation</li>
            <li>Pause before acceptance</li>
          </ol>
          </section>
          <aside className="repository-requirements" aria-labelledby="requirements-title"><h2 id="requirements-title">Before you scan</h2><dl><div><dt>Local Git repository</dt><dd>A committed checkout inside your configured allowed root. Remote URLs are not accepted.</dd></div><div><dt>Python project + uv lockfile</dt><dd><code>pyproject.toml</code> and <code>uv.lock</code> must be tracked. Only one dependency upgrade is selected per review.</dd></div><div><dt>Explicit human decision</dt><dd>Review the advisory, proposed diff and test results. Approval unlocks patch download; nothing is applied to your checkout.</dd></div></dl><p>Bedrock access is not required for local deterministic selection. Open Connection details to inspect the backend’s current evidence mode.</p></aside>
        </main>
      ) : (
        <main className="review-workspace">
          <header className="run-summary"><div><h2>{candidate.package} <span>{candidate.current_version} → {candidate.target_version}</span></h2><p>{candidate.rationale}</p><RecordedRunMode snapshot={snapshot} /></div><div className="run-receipt"><span className={`run-status ${outcome?.run.status}`}>{outcome?.run.status.replaceAll("_", " ")}</span><code>{outcome?.run.id}</code></div></header>
          <div className="operations-grid">
          <RiskQueue dependencies={dependencyRows} candidate={candidate as CandidateSelection} />

          <section className="execution-surface" aria-label="Upgrade execution">
            <ExecutionTimeline events={events} status={outcome?.run.status} />
            {state === "paused" || state === "deciding" ? (
              <ApprovalGate busy={state === "deciding"} onDecision={decide} />
            ) : (
              <section className={`decision-result ${state}`} aria-live="polite">
                <ShieldIcon />
                <div>
                  <h3>{state === "completed" ? "Approved report complete" : state === "failed" || state === "error" ? "Review incomplete" : "Patch rejected"}</h3>
                  <p>
                    {state === "completed"
                      ? "The approved evidence and validation record is complete. The source checkout remains unchanged."
                      : state === "failed" || state === "error" ? "This run did not complete successfully. Inspect the evidence and validation output before starting another run." : "No action was taken. The source checkout remains unchanged."}
                  </p>
                </div>
              </section>
            )}
            <section className="source-safe">
              <ShieldIcon />
              <div><strong>Source checkout unchanged</strong><span>No files, commits or branches were created in your working directory.</span></div>
            </section>
          </section>

          <aside className="evidence-column" aria-label="Evidence and changes">
            <EvidencePanel event={evidence} />
            <ValidationPanel event={validation} />
            <DiffViewer key={outcome?.run.id} diff={diff} />
          </aside>
          </div>
        </main>
      )}
    </div>
  );
}
