import { useEffect, useRef } from "react";

import { LockIcon } from "../../ui/Icons";

interface Props {
  busy: boolean;
  onDecision: (choice: "approved" | "rejected") => void;
}

export function ApprovalGate({ busy, onDecision }: Props) {
  const gateRef = useRef<HTMLElement>(null);
  useEffect(() => gateRef.current?.focus(), []);
  return (
    <section className="approval-gate" aria-labelledby="approval-title" ref={gateRef} tabIndex={-1}>
      <LockIcon />
      <div>
        <h3 id="approval-title">Approval gate</h3>
        <p>All automated checks are complete. Review the evidence and approve or reject the validated patch.</p>
      </div>
      <div className="approval-actions">
        <button className="reject-action" disabled={busy} onClick={() => onDecision("rejected")}>
          Reject patch
        </button>
        <button className="primary-action" disabled={busy} onClick={() => onDecision("approved")}>
          {busy ? "Recording decision…" : "Approve validated patch"}
        </button>
      </div>
    </section>
  );
}
