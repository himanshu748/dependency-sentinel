import { useEffect, useState } from "react";
import "./hosted.css";

function Notice() {
  const [available, setAvailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 5000);
    void fetch("/api/hosting", { signal: controller.signal, cache: "no-store" })
      .then(response => response.ok ? response.json() : null)
      .then(info => { if (!controller.signal.aborted) setAvailable(info?.hosted === true); })
      .catch(() => {})
      .finally(() => window.clearTimeout(timer));
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, []);
  return <aside className="hosted-notice" aria-label="Dependency Sentinel privacy and usage">
    <span>No sign-up needed</span>
    <details><summary>Privacy &amp; usage</summary>
      <p>Your reviews are saved on the server and linked to this browser by a cookie. Clearing cookies loses access. Please use fictional or non-sensitive inputs.</p>
      <p>Daily AI allowance: 10 requests in this browser, 20 per network and 50 across Dependency Sentinel. Saved reviews and approvals remain available when the daily AI allowance runs out.</p>
      <p>This workspace reviews the included sample repository. To review your own trusted code, use the local build.</p>
      <p className="hosted-provider">{available ? "AI provider: Groq via AWS AgentCore. No API key needed." : "Open Connection details in the workspace to check AI availability."}</p>
    </details>
  </aside>;
}

export function HostedNotice() {
  return import.meta.env.VITE_HOSTED === "true" ? <Notice /> : null;
}
