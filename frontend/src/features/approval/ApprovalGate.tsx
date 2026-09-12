import { useEffect, useRef } from "react";

import { LockIcon } from "../../ui/Icons";

interface Props {
  busy: boolean;
  validationReady: boolean;
  onDecision: (choice: "approved" | "rejected") => void;
}

export function ApprovalGate({ busy, validationReady, onDecision }: Props) {
  const gateRef = useRef<HTMLElement>(null);
  useEffect(() => gateRef.current?.focus(), []);
  return (
    <section className="approval-gate" aria-labelledby="approval-title" ref={gateRef} tabIndex={-1}>
      <LockIcon />
      <div>
        <h3 id="approval-title">Approval gate</h3>
        <p>{validationReady ? "Recorded tests passed. Review their scope and the patch before approving. Approval makes the patch downloadable; it does not merge it or modify your checkout." : "Complete passing test results are missing. Approval is unavailable. Start a new review; the server also checks the saved evidence before accepting any approval."}</p>
      </div>
      <div className="approval-actions">
        <button className="reject-action" disabled={busy} onClick={() => onDecision("rejected")}>
          Reject patch
        </button>
        <button className="primary-action" disabled={busy || !validationReady} onClick={() => onDecision("approved")}>
          {busy ? "Recording decision…" : "Approve validated patch"}
        </button>
      </div>
    </section>
  );
}
