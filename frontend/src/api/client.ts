import type { AgentRun, RunEnvelope, RunEvent } from "./types";

interface ApiErrorBody {
  detail?: { message?: string } | string;
}

async function readJson<T>(response: Response): Promise<T> {
  let body: T & ApiErrorBody;
  try { body = (await response.json()) as T & ApiErrorBody; }
  catch { throw new Error(`The local service returned an unreadable response (${response.status}). Retry the request.`); }
  if (!response.ok) {
    const detail = body.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return body;
}

export async function createRun(repository: string, idempotencyKey: string = crypto.randomUUID()): Promise<RunEnvelope> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({ repository }),
  });
  return readJson<RunEnvelope>(response);
}

export async function getRun(runId: string): Promise<AgentRun> {
  return readJson<AgentRun>(await fetch(`/api/runs/${encodeURIComponent(runId)}`));
}

export async function listRuns(): Promise<AgentRun[]> {
  return readJson<AgentRun[]>(await fetch("/api/runs"));
}

export async function getEvents(runId: string): Promise<RunEvent[]> {
  return readJson<RunEvent[]>(await fetch(`/api/runs/${runId}/events`));
}

export async function decideApproval(
  runId: string,
  approvalId: string,
  choice: "approved" | "rejected",
): Promise<AgentRun> {
  const response = await fetch(`/api/runs/${runId}/approvals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approval_id: approvalId, choice }),
  });
  return readJson<AgentRun>(response);
}

export type ReviewExport = "patch" | "receipt";

export async function downloadReview(runId: string, kind: ReviewExport): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/runs/${encodeURIComponent(runId)}/exports/${kind}`, { cache: "no-store" });
  } catch {
    throw new Error("The review download could not reach the local service. Reconnect and retry the download.");
  }
  if (!response.ok) await readJson(response);
  const expectedType = kind === "receipt" ? "application/json" : "text/plain";
  if (!response.headers.get("content-type")?.includes(expectedType)) {
    throw new Error("The service returned an unexpected download. Retry the download after checking the local service.");
  }
  const blob = await response.blob();
  if (!blob.size) throw new Error("The service returned an empty download. Start a new review to recreate the record.");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${runId.replace(/[^A-Za-z0-9_-]/g, "_")}.${kind === "receipt" ? "review.json" : "patch"}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
