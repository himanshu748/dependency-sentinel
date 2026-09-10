import type { RunEvent, ValidationResult } from "../../api/types";

export function ValidationPanel({ event }: { event?: RunEvent }) {
  const results = (event?.payload.results as ValidationResult[] | undefined) || [];
  const failed = event?.payload.passed !== true || results.some(result => result.timed_out || (result.exit_code != null && result.exit_code !== 0));
  const badge = !event ? "not run" : failed ? "not passed" : results.map(result => result.stdout?.match(/\b\d+ passed\b/)?.[0]).find(Boolean) || "passed";
  return <section className="validation-output">
    <header><h2>Validation output</h2><span>{badge}</span></header>
    {results.length ? results.map((result, index) => <details className="command-result" open={index === 0 || result.exit_code !== 0} key={index}>
      <summary><svg className="command-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m5 3 5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg><span>{result.command?.join(" ") || `Validation command ${index + 1}`}</span><span>{result.timed_out ? "Timed out" : result.exit_code == null ? "Exit unavailable" : `Exit ${result.exit_code}`}{result.duration_seconds != null ? ` · ${result.duration_seconds.toFixed(2)}s` : ""}</span></summary>
      <pre><code>{result.stdout || "No standard output."}{result.stderr ? `\n\nStandard error\n${result.stderr}` : ""}</code></pre>
    </details>) : <p className="panel-empty">No command output was recorded for this run. Nothing has been validated yet.</p>}
  </section>;
}
