import type { RunEvent } from "../../api/types";
import { hasSuccessfulValidation, validationResults } from "./validation";

export function ValidationPanel({ event }: { event?: RunEvent }) {
  const results = validationResults(event);
  const failed = !hasSuccessfulValidation(event);
  const badge = !event ? "not run" : failed ? "not passed" : results.map(result => typeof result.stdout === "string" ? result.stdout.match(/\b\d+ passed\b/)?.[0] : undefined).find(Boolean) || "passed";
  return <section id="validation-output" className="validation-output">
    <header><h2>Validation output</h2><span>{badge}</span></header>
    {results.length ? results.map((result, index) => <details className="command-result" open={index === 0 || result.exit_code !== 0} key={index}>
      <summary><svg className="command-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m5 3 5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg><span>{Array.isArray(result.command) ? result.command.filter(part => typeof part === "string").join(" ") || `Validation command ${index + 1}` : `Validation command ${index + 1}`}</span><span>{result.timed_out ? "Timed out" : result.exit_code == null ? "Exit unavailable" : `Exit ${result.exit_code}`}{typeof result.duration_seconds === "number" && Number.isFinite(result.duration_seconds) ? ` · ${result.duration_seconds.toFixed(2)}s` : ""}</span></summary>
      <pre><code>{typeof result.stdout === "string" && result.stdout || "No standard output."}{typeof result.stderr === "string" && result.stderr ? `\n\nStandard error\n${result.stderr}` : ""}</code></pre>
    </details>) : <p className="panel-empty">No command output was recorded for this run. Nothing has been validated yet.</p>}
  </section>;
}
