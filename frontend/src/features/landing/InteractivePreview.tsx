import { useState } from "react";
import { BranchIcon, CheckIcon, ShieldIcon } from "../../ui/Icons";

const STEPS = ["Evidence", "Diff", "Decision"] as const;

export function InteractivePreview() {
  const [stage, setStage] = useState(1);
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);
  return (
    <aside className="hero-readout interactive-preview" aria-label="Illustrative dependency review">
      <div className="readout-head"><BranchIcon /><span>Illustrative preview · fixture workflow</span></div>
      <div className="patch-preview-title"><h3>A patch you can inspect.</h3><span>Explore the review. Nothing runs or writes.</span></div>
      <div className="review-switcher" role="group" aria-label="Explore the example review">
        {STEPS.map((step, index) => <button key={step} type="button" aria-pressed={stage === index} aria-controls="review-preview-panel" onClick={() => setStage(index)}><span aria-hidden="true">0{index + 1}</span>{step}</button>)}
      </div>
      <div id="review-preview-panel" className="review-preview-panel">
        <div key={stage} className="review-panel-content">
          {stage === 0 && <div className="example-evidence">
            <p className="example-file">advisory / illustrative only</p>
            <h4>One claim. A traceable source.</h4>
            <dl><div><dt>package</dt><dd>demo-library</dd></div><div><dt>installed</dt><dd>1.0.0</dd></div><div><dt>candidate</dt><dd>1.0.1</dd></div></dl>
            <p>This fictional package shows the evidence layout. The full demo includes fixture advisories and release records.</p>
          </div>}
          {stage === 1 && <>
            <div className="patch-preview-diff" aria-label="Illustrative version change">
              <div>requirements.txt <span>example package</span></div>
              <p className="patch-removed"><span aria-hidden="true">−</span><span><span className="sr-only">Remove </span>demo-library==1.0.0</span></p>
              <p className="patch-added"><span aria-hidden="true">+</span><span><span className="sr-only">Add </span>demo-library==1.0.1</span></p>
            </div>
            <div className="example-worktrees"><span>Source checkout<strong>Unchanged</strong></span><BranchIcon /><span>Disposable worktree<strong>Patch staged</strong></span></div>
            <p className="example-caption">Sample diff only. No package installation or tests run in this preview.</p>
          </>}
          {stage === 2 && <div className="example-decision">
            <ShieldIcon /><h4>{decision ? "Your example decision is noted." : "This is where the agent stops."}</h4>
            <p>{decision ? "Only this preview changed. No files, approvals or pull requests were saved." : "You choose what happens next. Approval in the full demo records a reviewed result; it does not merge a patch."}</p>
            <div className="example-decision-actions">
              <button type="button" aria-pressed={decision === "approved"} onClick={() => setDecision("approved")}>Approve example</button>
              <button type="button" aria-pressed={decision === "rejected"} onClick={() => setDecision("rejected")}>Reject example</button>
            </div>
            <p className="example-decision-status" role="status">{decision ? `Example ${decision}. Source checkout untouched.` : "Waiting for your decision."}</p>
            {decision && <button className="preview-reset" type="button" onClick={() => setDecision(null)}>Reset example</button>}
          </div>}
        </div>
      </div>
      <details className="patch-review-details"><summary>What does approval actually do?</summary><p>It records your decision on the staged result. It does not merge the patch, publish a release or modify your source checkout. The diff above is illustrative, not a verified package recommendation.</p></details>
      <div className="patch-preview-footer"><CheckIcon /><span>Review first. Source checkout untouched.</span></div>
    </aside>
  );
}
