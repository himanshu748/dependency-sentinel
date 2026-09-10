import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

async function reopenWithMode(execution: unknown, status = "completed") {
  window.location.hash = "#main";
  const run = { id: "recorded-run", task_type: "dependency_upgrade", input_summary: "/controlled/repo", status, created_at: "2026-09-08T00:00:00Z", updated_at: "2026-09-08T00:00:00Z" };
  const events = [
    { id: "source", kind: "repository_inspected", payload: execution === undefined ? {} : { execution } },
    { id: "candidate", kind: "candidate_selected", payload: { package: "sample", current_version: "1.0", target_version: "1.1", advisory_identifier: "controlled", rationale: "Saved review" } },
  ];
  vi.spyOn(globalThis, "fetch").mockImplementation(async input => {
    const url = String(input);
    if (url === "/api/health") return new Response(JSON.stringify({ fixture_mode: false, runtime_mode: "openai-compatible", evidence_mode: "live", repository_root: "/controlled" }));
    if (url.endsWith("/events")) return new Response(JSON.stringify(events));
    return new Response(JSON.stringify(url === "/api/runs" ? [run] : run));
  });
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Saved runs" }));
  fireEvent.click(await screen.findByRole("button", { name: "repo /controlled/repo" }));
  return screen.findByRole("note", { name: "Recorded run mode" });
}

it("labels a pending fixture run from its saved event even when health reports live mode", async () => {
  const mode = await reopenWithMode({ model_mode: "fixture", evidence_mode: "fixture" }, "waiting_for_approval");
  expect(mode).toHaveTextContent("Scripted model · Fixture advisory data");
  fireEvent.click(screen.getByRole("button", { name: "Connection details" }));
  await screen.findByText(/Live OSV\/PyPI evidence/);
  expect(mode).toHaveTextContent("Scripted model · Fixture advisory data");
});

it.each([
  ["bedrock", "Bedrock model"],
  ["openai-compatible", "External model"],
  ["agentcore", "AgentCore model"],
  ["fixture", "Scripted model"],
])("labels completed %s runs separately from their live evidence mode", async (model, label) => {
  expect(await reopenWithMode({ model_mode: model, evidence_mode: "live" }))
    .toHaveTextContent(`${label} · Live advisory data`);
});

it.each([undefined, null, {}, { model_mode: "future", evidence_mode: "live" }, { model_mode: "fixture" }])("does not infer missing or unknown recorded mode: %j", async execution => {
  expect(await reopenWithMode(execution)).toHaveTextContent("Recorded mode unavailable");
});
