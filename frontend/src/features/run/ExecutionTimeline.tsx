import type { RunEvent } from "../../api/types";

const steps = [
  ["repository_inspected", "Repository inspected", "Files, manifests and lockfiles analyzed"],
  ["manifest_scanned", "Manifest scanned", "pyproject.toml and uv.lock read"],
  ["candidate_selected", "Candidate selected", "One evidence-backed upgrade chosen"],
  ["evidence_collected", "Evidence collected", "Advisory and release data verified"],
  ["upgrade_staged", "Upgrade staged", "Disposable worktree"],
  ["validation_completed", "Validation passed", "Tests and policy checks executed"],
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

export function ExecutionTimeline({ events }: { events: RunEvent[] }) {
  return (
    <ol className="execution-timeline">
      {steps.map(([kind, label, description], index) => {
        const event = events.find((item) => item.kind === kind);
        const paused = kind === "approval_required" && Boolean(event);
        return (
          <li key={kind} className={event && !paused ? "complete" : paused ? "paused" : "pending"}>
            <span className="step-number">{index + 1}</span>
            <span className="step-copy">
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
            <span className="step-status">
              <strong>{paused ? "Paused" : event ? "Complete" : "Locked"}</strong>
              <small>{paused ? "waiting for approval" : time(event?.created_at)}</small>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
