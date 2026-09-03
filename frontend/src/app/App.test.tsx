import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const pausedRun = {
  run: {
    id: "run-test",
    task_type: "dependency_upgrade",
    input_summary: "/tmp/vulnerable-python-project",
    status: "waiting_for_approval",
    created_at: "2026-09-02T10:21:14Z",
    updated_at: "2026-09-02T10:21:28Z",
  },
  candidate: {
    package: "jinja2",
    current_version: "3.1.4",
    target_version: "3.1.5",
    advisory_identifier: "CVE-2024-56326",
    rationale: "The locked version is affected and 3.1.5 contains the fix.",
  },
  approval_id: "apply-upgrade",
};

const events = [
  {
    id: "1",
    run_id: "run-test",
    sequence: 1,
    kind: "repository_inspected",
    summary: "Inspected vulnerable-python-project at f2a4c19",
    payload: { branch: "main", head: "f2a4c19f00", dirty: false },
    idempotency_key: "1",
    created_at: "2026-09-02T10:21:14Z",
  },
  {
    id: "2",
    run_id: "run-test",
    sequence: 2,
    kind: "manifest_scanned",
    summary: "Found 2 locked dependencies",
    payload: {
      dependencies: [
        { name: "click", resolved_version: "8.1.8" },
        { name: "jinja2", resolved_version: "3.1.4" },
      ],
    },
    idempotency_key: "2",
    created_at: "2026-09-02T10:21:16Z",
  },
  {
    id: "3",
    run_id: "run-test",
    sequence: 3,
    kind: "candidate_selected",
    summary: "Selected jinja2 3.1.4 → 3.1.5",
    payload: pausedRun.candidate,
    idempotency_key: "3",
    created_at: "2026-09-02T10:21:18Z",
  },
  {
    id: "4",
    run_id: "run-test",
    sequence: 4,
    kind: "evidence_collected",
    summary: "Verified CVE-2024-56326 and the fixed release",
    payload: {
      advisory_ids: ["CVE-2024-56326"],
      advisories: [
        {
          identifier: "CVE-2024-56326",
          summary: "An oversight in Jinja's sandboxed environment requires a fixed release.",
          source: { publisher: "OSV / NVD", url: "https://nvd.nist.gov/vuln/detail/CVE-2024-56326" },
        },
      ],
      release: {
        version: "3.1.5",
        summary: "Jinja2 maintenance release",
        source: { publisher: "PyPI", url: "https://pypi.org/project/Jinja2/3.1.5/" },
      },
    },
    idempotency_key: "4",
    created_at: "2026-09-02T10:21:21Z",
  },
  {
    id: "5",
    run_id: "run-test",
    sequence: 5,
    kind: "upgrade_staged",
    summary: "Staged the candidate in a disposable worktree",
    payload: {
      diff: '--- a/pyproject.toml\n+++ b/pyproject.toml\n-  "jinja2==3.1.4"\n+  "jinja2==3.1.5"\n--- a/uv.lock\n+++ b/uv.lock\n-version = "3.1.4"\n+version = "3.1.5"\n',
    },
    idempotency_key: "5",
    created_at: "2026-09-02T10:21:24Z",
  },
  {
    id: "6",
    run_id: "run-test",
    sequence: 6,
    kind: "validation_completed",
    summary: "Validation passed",
    payload: { passed: true, results: [{ stdout: "2 passed in 1.42s" }] },
    idempotency_key: "6",
    created_at: "2026-09-02T10:21:28Z",
  },
  {
    id: "7",
    run_id: "run-test",
    sequence: 7,
    kind: "approval_required",
    summary: "Human approval is required before accepting the validated patch",
    payload: { approval_id: "apply-upgrade" },
    idempotency_key: "7",
    created_at: "2026-09-02T10:21:28Z",
  },
];

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.removeItem("dependency-sentinel-theme");
  delete document.documentElement.dataset.theme;
});

describe("Dependency Sentinel", () => {
  it("renders a useful empty state and repository scan action", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Dependency Sentinel" })).toBeInTheDocument();
    expect(screen.getByLabelText("Repository path")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scan repository" })).toBeEnabled();
    expect(screen.getByText("No maintenance run yet")).toBeInTheDocument();
  });

  it("supports an explicit accessible dark theme toggle", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light theme" })).toBeEnabled();
  });

  it("renders evidence, diff and approval only after a successful run", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(pausedRun), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(events), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Scan repository" }));

    expect(await screen.findByText("Approval required")).toBeInTheDocument();
    expect(screen.getByText("CVE-2024-56326")).toBeInTheDocument();
    expect(screen.getByText(/jinja2==3\.1\.5/)).toBeInTheDocument();
    expect(screen.getByText("2 passed")).toBeInTheDocument();
    expect(screen.getByText("Source checkout unchanged")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve validated patch" })).toBeEnabled();
    expect(document.activeElement).toHaveAttribute("aria-labelledby", "approval-title");
    expect(screen.getByText("Evidence").parentElement).toHaveTextContent("3");
    const queueItems = screen.getByRole("complementary", { name: "Risk queue" }).querySelectorAll("li");
    expect(queueItems[0]).toHaveTextContent("jinja2");
  });

  it("submits the exact approval gate and shows completion", async () => {
    const completedRun = { ...pausedRun.run, status: "completed" };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(pausedRun), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(events), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(completedRun), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Scan repository" }));
    await screen.findByText("Approval required");

    fireEvent.click(screen.getByRole("button", { name: "Approve validated patch" }));

    expect(await screen.findByText("Approved report complete")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/runs/run-test/approvals",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ approval_id: "apply-upgrade", choice: "approved" }),
      }),
    );
  });

  it("shows an actionable API error and keeps retry available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: { code: "repository_invalid", message: "Path is outside the allowed root" } }),
          { status: 400, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Scan repository" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Path is outside the allowed root",
    );
    expect(screen.getByRole("button", { name: "Retry scan" })).toBeEnabled();
  });
});
