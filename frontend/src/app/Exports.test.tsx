import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "./App";

const candidate = { package: "sample", current_version: "1.0", target_version: "1.1", advisory_identifier: "controlled", rationale: "Controlled fixture review" };
const completed = { id: "saved-approved", task_type: "dependency_upgrade", input_summary: "/controlled/repo", status: "completed", created_at: "2026-09-08T00:00:00Z", updated_at: "2026-09-08T00:00:00Z" };
const events = [
  { id: "candidate", run_id: completed.id, kind: "candidate_selected", sequence: 1, payload: candidate, summary: "Selected controlled fixture", created_at: completed.created_at },
  { id: "patch", run_id: completed.id, kind: "upgrade_staged", sequence: 2, payload: { diff: "display-only-client-diff" }, summary: "Staged fixture", created_at: completed.created_at },
];

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function blobText(blob: Blob): Promise<string> {
  // Fetch responses use Node's Blob; jsdom's FileReader only accepts its own Blob.
  if (typeof blob.text === "function") return blob.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

async function openSaved(exportResponse: () => Promise<Response>, status = "completed") {
  window.location.hash = "#main";
  const run = { ...completed, status };
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/exports/")) return exportResponse();
    if (url.endsWith("/events")) return new Response(JSON.stringify(events));
    if (url === "/api/runs") return new Response(JSON.stringify([run]));
    return new Response(JSON.stringify(run));
  });
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Saved runs" }));
  fireEvent.click(await screen.findByRole("button", { name: "repo /controlled/repo" }));
  await screen.findByText("Controlled fixture review");
  return fetcher;
}

it("downloads the server patch bytes and receipt using the reopened run identity", async () => {
  const blobs: Blob[] = [];
  const revoke = vi.fn();
  vi.stubGlobal("URL", class extends URL {
    static createObjectURL(blob: Blob) { blobs.push(blob); return "blob:controlled"; }
    static revokeObjectURL(url: string) { revoke(url); }
  });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  const response = vi.fn()
    .mockResolvedValueOnce(new Response("server-approved-patch", { headers: { "Content-Type": "text/plain" } }))
    .mockResolvedValueOnce(new Response('{"artifact":"approved-review"}', { headers: { "Content-Type": "application/json" } }));
  const fetcher = await openSaved(response);
  fireEvent.click(screen.getByRole("button", { name: "Download reviewed patch" }));
  await screen.findByText(/Reviewed patch download started/);
  expect(await blobText(blobs[0])).toBe("server-approved-patch");
  fireEvent.click(screen.getByRole("button", { name: "Download review receipt" }));
  await screen.findByText(/Review receipt download started/);
  expect(await blobText(blobs[1])).toBe('{"artifact":"approved-review"}');
  expect(click).toHaveBeenCalledTimes(2);
  expect(fetcher.mock.calls.filter(call => String(call[0]).includes("/exports/")).map(call => call[0])).toEqual([
    "/api/runs/saved-approved/exports/patch", "/api/runs/saved-approved/exports/receipt",
  ]);
  await waitFor(() => expect(revoke).toHaveBeenCalledTimes(2), { timeout: 5000 });
});

it("shows a legacy or altered record failure and retries export without rerunning or reapproving", async () => {
  const response = vi.fn().mockImplementation(async () => new Response(JSON.stringify({
    detail: { message: "This saved run lacks verified source provenance. Start a new review." },
  }), { status: 409, headers: { "Content-Type": "application/json" } }));
  const fetcher = await openSaved(response);
  fireEvent.click(screen.getByRole("button", { name: "Download review receipt" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Start a new review");
  expect(screen.getByText("Approved report complete")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry download" }));
  await waitFor(() => expect(response).toHaveBeenCalledTimes(2));
  expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1]?.method === "GET")).toBe(true);
});

it("does not show export actions for a failed saved record", async () => {
  await openSaved(vi.fn(), "failed");
  expect(screen.getByText("Review incomplete")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Download reviewed patch" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Download review receipt" })).not.toBeInTheDocument();
});
