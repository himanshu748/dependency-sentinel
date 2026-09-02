export type RunStatus =
  | "queued"
  | "running"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "cancelled";

export interface AgentRun {
  id: string;
  task_type: string;
  input_summary: string;
  status: RunStatus;
  created_at: string;
  updated_at: string;
}

export interface CandidateSelection {
  package: string;
  current_version: string;
  target_version: string;
  advisory_identifier: string;
  rationale: string;
}

export interface RunEnvelope {
  run: AgentRun;
  candidate: CandidateSelection;
  approval_id: string | null;
}

export interface RunEvent {
  id: string;
  run_id: string;
  sequence: number;
  kind: string;
  summary: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
  created_at: string;
}
