export function RecordedRunMode({ snapshot }: { snapshot?: Record<string, unknown> }) {
  const value = snapshot?.execution;
  const execution = value && typeof value === "object" && !Array.isArray(value)
    ? value as { model_mode?: unknown; evidence_mode?: unknown }
    : null;
  const model = execution?.model_mode === "fixture" ? "Scripted model"
    : execution?.model_mode === "bedrock" ? "Bedrock model"
    : execution?.model_mode === "openai-compatible" ? "External model"
    : execution?.model_mode === "agentcore" ? "AgentCore model" : null;
  const evidence = execution?.evidence_mode === "fixture" ? "Fixture advisory data"
    : execution?.evidence_mode === "live" ? "Live advisory data" : null;

  return <p className="recorded-run-mode" role="note" aria-label="Recorded run mode">
    {model && evidence ? <><strong>Recorded mode:</strong> {model} · {evidence}</> : "Recorded mode unavailable"}
  </p>;
}
