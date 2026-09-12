import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { RunEvent } from "../../api/types";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { ValidationPanel } from "./ValidationPanel";
import { RiskQueue } from "../risk/RiskQueue";
import { ApprovalGate } from "../approval/ApprovalGate";
import { hasSuccessfulValidation } from "./validation";
import { ReviewCheckpoints } from "./ReviewCheckpoints";

afterEach(cleanup);
function event(kind: string, payload = {}): RunEvent {
  return { id: kind, run_id: "test", sequence: 1, kind, summary: kind, payload, idempotency_key: kind, created_at: "2026-09-08T00:00:00Z" };
}

it("does not label failed validation as passing", () => {
  render(<ExecutionTimeline status="failed" events={[event("validation_completed", { passed: false })]} />);
  expect(screen.getByText("Validation failed")).toBeInTheDocument();
  expect(screen.queryByText("Validation passed")).not.toBeInTheDocument();
});

it("does not leave completed approvals paused", () => {
  render(<ExecutionTimeline status="completed" events={[event("approval_required")]} />);
  expect(screen.getByText("Patch approved")).toBeInTheDocument();
  expect(screen.queryByText("Paused")).not.toBeInTheDocument();
});

it("shows actual command, stderr, timeout and elapsed time", () => {
  render(<ValidationPanel event={event("validation_completed", { passed: false, results: [{ command: ["uv", "run", "pytest"], stdout: "one failure", stderr: "test timed out", exit_code: 124, duration_seconds: 30, timed_out: true }] })} />);
  expect(screen.getByText("uv run pytest")).toBeInTheDocument();
  expect(screen.getByText(/Timed out · 30.00s/)).toBeInTheDocument();
  expect(screen.getByText(/test timed out/)).toBeInTheDocument();
  expect(screen.queryByText(/python -m pytest/)).not.toBeInTheDocument();
});

it.each([
  { passed: false, results: [{ stdout: "1 failed, 1 passed", exit_code: 1 }] },
  { passed: false, results: [{ stdout: "8 passed", exit_code: 124, timed_out: true }] },
  { passed: false, results: [{ stdout: "12 passed", exit_code: 0 }, { stdout: "1 failed", exit_code: 1 }] },
  { passed: true, results: [{ stdout: "12 passed", exit_code: 0 }, { stdout: "stopped", exit_code: 1 }] },
  { passed: true, results: [] },
  { passed: true, results: [null] },
  { passed: true, results: [{ stdout: "12 passed", exit_code: null }] },
  { passed: true, results: [{ stdout: "12 passed", exit_code: 0 }] },
  { passed: true, results: [{ command: [], exit_code: 0, timed_out: false, duration_seconds: 1 }] },
  { passed: true, results: [{ command: ["echo", "pytest"], exit_code: "0", timed_out: false, duration_seconds: 1 }] },
])("prioritizes validation failure over passed-test substrings: %j", (payload) => {
  render(<ValidationPanel event={event("validation_completed", payload)} />);
  expect(screen.getByRole("heading", { name: "Validation output" }).parentElement).toHaveTextContent("not passed");
});

it("shows missing exit evidence as failed in the timeline too", () => {
  render(<ExecutionTimeline events={[event("validation_completed", { passed: true, results: [{ stdout: "12 passed" }] })]} />);
  expect(screen.getByText("Validation failed")).toBeInTheDocument();
});

it("requires complete test evidence for the approval control", () => {
  const incomplete = event("validation_completed", { passed: true, results: [] });
  render(<ApprovalGate busy={false} validationReady={hasSuccessfulValidation(incomplete)} onDecision={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Approve validated patch" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Reject patch" })).toBeEnabled();
  expect(screen.getByText(/Complete passing test results are missing/)).toBeInTheDocument();
});

it("shows passing commands, explicit file scope and saved fingerprints without overclaiming", () => {
  const validation = event("validation_completed", { passed: true, staged_files_unchanged: true, patch_sha256: "a".repeat(64), results: [{ command: ["uv", "run", "pytest"], exit_code: 0, timed_out: false, duration_seconds: 1, stdout: "2 passed" }] });
  expect(hasSuccessfulValidation(validation)).toBe(true);
  render(<ReviewCheckpoints events={[event("repository_inspected", { head: "b".repeat(40), dirty: false }), event("upgrade_staged", { changed_files: ["pyproject.toml", "uv.lock"] }), validation]} />);
  expect(screen.getByText("1 successful command")).toBeInTheDocument();
  expect(screen.getByText("pyproject.toml")).toBeInTheDocument();
  expect(screen.getByText("Tracked files unchanged during validation")).toBeInTheDocument();
  expect(screen.getByText(/not a signed security attestation/)).toBeInTheDocument();
});

it("does not clear unselected dependencies", () => {
  render(<RiskQueue dependencies={[{ name: "a", resolved_version: "1" }, { name: "b", resolved_version: "1" }]} candidate={{ package: "a", current_version: "1", target_version: "2", advisory_identifier: "test", rationale: "test" }} />);
  expect(screen.getByText("not selected · not cleared")).toBeInTheDocument();
  expect(screen.queryByText("no action")).not.toBeInTheDocument();
});
