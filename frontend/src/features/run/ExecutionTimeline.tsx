import type { RunEvent, RunStatus } from "../../api/types";
import { hasSuccessfulValidation } from "./validation";

const steps = [
  ["repository_inspected", "Repository inspected", "Files, manifests and lockfiles analyzed"],
  ["manifest_scanned", "Manifest scanned", "pyproject.toml and uv.lock read"],
  ["candidate_selected", "Candidate selected", "One evidence-backed upgrade chosen"],
  ["evidence_collected", "Evidence collected", "Advisory and release data verified"],
  ["upgrade_staged", "Upgrade staged", "Disposable worktree"],
  ["validation_completed", "Validation", "Repository tests executed in isolation"],
  ["approval_required", "Approval required", "Human review and approval required"],
] as const;

function time(value?: string) {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function ExecutionTimeline({ events, status }: { events: RunEvent[]; status?: RunStatus }) {
  return (
    <ol className="execution-timeline">
      {steps.map(([kind, label, description], index) => {
        const approved = kind === "approval_required" && status === "completed";
        const rejected = kind === "approval_required" && status === "cancelled";
        const event = events.find((item) => item.kind === (approved ? "approval_recorded" : rejected ? "approval_rejected" : kind));
        const reached = Boolean(event) || approved || rejected;
        const decision = kind === "approval_required" && reached;
        const paused = decision && (!status || status === "waiting_for_approval");
        const failed = kind === "validation_completed" && Boolean(event) && !hasSuccessfulValidation(event);
        return (
          <li key={kind} className={failed || rejected ? "failed" : reached && !paused ? "complete" : paused ? "paused" : "pending"}>
            <span className="step-number">{index + 1}</span>
            <span className="step-copy">
              <strong>{kind === "validation_completed" && event ? failed ? "Validation failed" : "Validation passed" : decision && status === "completed" ? "Patch approved" : rejected ? "Patch rejected" : label}</strong>
              <small>{approved || rejected ? "Human decision saved" : description}</small>
            </span>
            <span className="step-status">
              <strong>{failed ? "Failed" : rejected ? "Rejected" : paused ? "Paused" : reached ? "Complete" : "Not reached"}</strong>
              <small>{paused ? "waiting for approval" : (approved || rejected) && !event ? "Time unavailable" : time(event?.created_at)}</small>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
