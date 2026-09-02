import type { AgentRun, RunEnvelope, RunEvent } from "./types";

interface ApiErrorBody {
  detail?: { message?: string } | string;
}

async function readJson<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T & ApiErrorBody;
  if (!response.ok) {
    const detail = body.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return body;
}

export async function createRun(repository: string): Promise<RunEnvelope> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify({ repository }),
  });
  return readJson<RunEnvelope>(response);
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
