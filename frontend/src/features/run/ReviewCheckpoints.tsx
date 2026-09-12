import type { RunEvent } from "../../api/types";
import { hasSuccessfulValidation, validationResults } from "./validation";
import "./checkpoints.css";

export function ReviewCheckpoints({ events }: { events: RunEvent[] }) {
  const snapshot = events.find(event => event.kind === "repository_inspected")?.payload;
  const staged = events.find(event => event.kind === "upgrade_staged")?.payload;
  const validation = events.find(event => event.kind === "validation_completed");
  const revision = typeof snapshot?.head === "string" ? snapshot.head : "";
  const files = Array.isArray(staged?.changed_files) ? staged.changed_files.filter((file): file is string => typeof file === "string") : [];
  const complete = hasSuccessfulValidation(validation);
  const unchanged = validation?.payload.staged_files_unchanged === true;
  const patchHash = typeof validation?.payload.patch_sha256 === "string" ? validation.payload.patch_sha256 : "";
  return <section className="review-checkpoints" aria-labelledby="checkpoints-title">
    <h2 id="checkpoints-title">What this review covers</h2>
    <dl>
      <div><dt>Captured source</dt><dd>{revision ? <code title={revision}>{revision.slice(0, 12)}</code> : "Not recorded"}</dd><small>{snapshot?.dirty === false ? "Clean at capture · later edits are outside this review" : "Clean source state not confirmed"}</small></div>
      <div><dt>Proposed files</dt><dd>{files.length ? files.map(file => <code key={file}>{file}</code>) : "File scope not recorded"}</dd><small>{unchanged ? "Tracked files unchanged during validation" : "Validation stability not confirmed"}</small></div>
      <div><dt>Recorded validation</dt><dd>{complete ? `${validationResults(validation).length} successful command${validationResults(validation).length === 1 ? "" : "s"}` : "Incomplete or not passed"}</dd><a href="#validation-output">Read command output</a></div>
    </dl>
    {patchHash && <details><summary>Recorded patch fingerprint</summary><code>{patchHash}</code><p>The server checks this saved patch against the approval record. This is a consistency check, not a signed security attestation.</p></details>}
  </section>;
}
