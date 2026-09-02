import { useState } from "react";

import { createRun, decideApproval, getEvents } from "../api/client";
import type { CandidateSelection, RunEnvelope, RunEvent } from "../api/types";
import { ApprovalGate } from "../features/approval/ApprovalGate";
import { DiffViewer } from "../features/diff/DiffViewer";
import { EvidencePanel } from "../features/evidence/EvidencePanel";
import { RepositoryHeader } from "../features/repository/RepositoryHeader";
import { RiskQueue } from "../features/risk/RiskQueue";
import { ExecutionTimeline } from "../features/run/ExecutionTimeline";
import { ShieldIcon } from "../ui/Icons";

type ViewState = "idle" | "scanning" | "paused" | "deciding" | "completed" | "rejected" | "error";

const defaultRepository = import.meta.env.VITE_DEMO_REPOSITORY || "/tmp/dependency-sentinel-demo";

function eventOf(events: RunEvent[], kind: string) {
  return events.find((event) => event.kind === kind);
}

function dependencies(events: RunEvent[]) {
  const event = eventOf(events, "manifest_scanned");
  return (event?.payload.dependencies as { name: string; resolved_version?: string }[] | undefined) || [];
}

export function App() {
  const [repository, setRepository] = useState(defaultRepository);
  const [state, setState] = useState<ViewState>("idle");
  const [outcome, setOutcome] = useState<RunEnvelope | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const snapshot = eventOf(events, "repository_inspected")?.payload;
  const candidate = outcome?.candidate;
  const validation = eventOf(events, "validation_completed");
  const validationResults = validation?.payload.results as { stdout?: string }[] | undefined;
  const validationSummary = validationResults?.[0]?.stdout || "Validation output unavailable";
  const validationBadge = validationSummary.match(/\b\d+ passed\b/)?.[0] ||
    (validation?.payload.passed ? "passed" : "not passed");
  const diff = (eventOf(events, "upgrade_staged")?.payload.diff as string | undefined) || "";
  const evidence = eventOf(events, "evidence_collected");
  const dependencyRows = dependencies(events);

  async function scan() {
    if (!navigator.onLine) {
      setError("You are offline. Reconnect, then retry the scan.");
      setState("error");
      return;
    }
    setState("scanning");
    setError("");
    try {
      const created = await createRun(repository);
      const timeline = await getEvents(created.run.id);
      setOutcome(created);
      setEvents(timeline);
      setState(created.run.status === "waiting_for_approval" ? "paused" : "completed");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The scan could not be completed");
      setState("error");
    }
  }

  async function decide(choice: "approved" | "rejected") {
    if (!outcome?.approval_id) return;
    setState("deciding");
    setError("");
    try {
      const run = await decideApproval(outcome.run.id, outcome.approval_id, choice);
      setOutcome({ ...outcome, run });
      setState(choice === "approved" ? "completed" : "rejected");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The decision could not be recorded");
      setState("error");
    }
  }

  function toggleTheme() {
    const nextTheme = theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = nextTheme;
    setTheme(nextTheme);
  }

  return (
    <div className="app-shell">
      <RepositoryHeader
        repository={repository}
        onRepositoryChange={setRepository}
        onScan={scan}
        isScanning={state === "scanning"}
        retry={state === "error"}
        branch={snapshot?.branch as string | undefined}
        head={snapshot?.head as string | undefined}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {error && (
        <div className="error-banner" role="alert">
          <span><strong>Scan stopped.</strong> {error}</span>
          <button type="button" onClick={scan}>Try scan again</button>
        </div>
      )}

      {state === "scanning" ? (
        <main className="loading-state" aria-live="polite" aria-busy="true">
          <h2>Inspecting repository</h2>
          <p>Checking the manifest, evidence sources and isolated validation path.</p>
          <div className="instrument-skeleton" aria-hidden="true">
            <span /><span /><span /><span /><span /><span /><span />
          </div>
        </main>
      ) : !candidate ? (
        <main className="empty-state">
          <div className="empty-instrument" aria-hidden="true"><ShieldIcon /><span>01</span></div>
          <h2>No maintenance run yet</h2>
          <p>Choose a local Python repository, then scan for one evidence-backed upgrade.</p>
          <ol aria-label="Scan safety contract">
            <li>Read the source checkout</li>
            <li>Stage changes in isolation</li>
            <li>Pause before acceptance</li>
          </ol>
        </main>
      ) : (
        <main className="operations-grid">
          <RiskQueue dependencies={dependencyRows} candidate={candidate as CandidateSelection} />

          <section className="execution-surface" aria-label="Upgrade execution">
            <ExecutionTimeline events={events} />
            {state === "paused" || state === "deciding" ? (
              <ApprovalGate busy={state === "deciding"} onDecision={decide} />
            ) : (
              <section className={`decision-result ${state}`} aria-live="polite">
                <ShieldIcon />
                <div>
                  <h3>{state === "completed" ? "Approved report complete" : "Patch rejected"}</h3>
                  <p>
                    {state === "completed"
                      ? "The approved evidence and validation record is complete. The source checkout remains unchanged."
                      : "No action was taken. The source checkout remains unchanged."}
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
            <DiffViewer diff={diff} />
            <section className="validation-output">
              <header><h2>Validation output</h2><span>{validationBadge}</span></header>
              <pre><code>$ python -m pytest -q{"\n\n"}{validationSummary}</code></pre>
            </section>
          </aside>
        </main>
      )}
    </div>
  );
}
