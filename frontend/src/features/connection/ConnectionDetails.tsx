import { useEffect, useId, useRef, useState } from "react";
import "./connection.css";

type Description = { title: string; detail: string; evidence: string };
function describe(value: unknown): Description {
  const info = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const evidence = info.evidence_mode === "live"
    ? "Live OSV/PyPI evidence is configured; this check does not fetch advisories."
    : info.evidence_mode === "fixture" ? "Fixture advisory data; no current vulnerability lookup." : "";
  if (info.fixture_mode === true && info.runtime_mode === "local") {
    return { title: "Scripted responses · no model inference",
      detail: "Strands uses a scripted provider. Local rules and approval actions still run. This mode does not demonstrate live AI.", evidence };
  }
  const providers: Record<string, string> = {
    "openai-compatible": "External model", bedrock: "Bedrock", agentcore: "AgentCore",
  };
  const provider = typeof info.runtime_mode === "string" ? providers[info.runtime_mode] : undefined;
  if (provider && info.fixture_mode === false) {
    return { title: `${provider} configured · inference not verified`,
      detail: "Model requests go to your configured endpoint through Strands. This health check does not call the model or verify access, credits, or billing coverage. Stored runs retain their original execution mode.", evidence };
  }
  return { title: "Execution mode unavailable",
    detail: "The service did not return a recognized runtime configuration. Do not assume this is local or live inference.", evidence };
}

export function ConnectionDetails() {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [description, setDescription] = useState<Description | null>(null);
  const [error, setError] = useState(false);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => {
    const controller = pending.current;
    pending.current = null;
    controller?.abort();
  }, []);

  async function check() {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true); setError(false); setDescription(null);
    const timer = window.setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch("/api/health", { signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error("Health request failed");
      const result: unknown = await response.json();
      if (!controller.signal.aborted) setDescription(describe(result));
    } catch {
      if (pending.current === controller) setError(true);
    } finally {
      window.clearTimeout(timer);
      if (pending.current === controller) { pending.current = null; setLoading(false); }
    }
  }
  function toggle() {
    if (open) {
      const controller = pending.current;
      pending.current = null; controller?.abort(); setLoading(false); setOpen(false);
    } else { setOpen(true); void check(); }
  }
  return <div className="connection-inspector">
    <button type="button" aria-expanded={open} aria-controls={id} onClick={toggle}>Connection details</button>
    {open && <section id={id} className="connection-panel" aria-label="Runtime configuration" aria-busy={loading}>
      {loading ? <p role="status">Checking local service configuration…</p> : error
        ? <div role="alert"><p>Connection status unavailable. Check that the local service is running. No model request was made.</p><button type="button" onClick={() => void check()}>Retry connection check</button></div>
        : description && <div role="status"><strong>{description.title}</strong><p>{description.detail}</p>{description.evidence && <p>{description.evidence}</p>}</div>}
    </section>}
  </div>;
}
