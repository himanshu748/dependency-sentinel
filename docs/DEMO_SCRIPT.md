# Dependency Sentinel recording plan

Target length: about 4 minutes 15 seconds, below the five-minute limit. Public YouTube/Vimeo upload is still pending.

## Recording prerequisites

The Qwen endpoint is stopped at the owner's request. Resume only with explicit approval, warm it, run the real workflow smoke check, then record a fresh run. Do not start inference for rehearsal.

Use a fictional input and a temporary database. Hide private tabs, credentials and account information. Open Connection details to show configuration, but do not call that a successful model test. For a scripted rehearsal, keep "Scripted responses — no model inference" visible in the recording; do not present that clip as new live-model evidence.

## Pitch

Dependency Sentinel prepares one dependency upgrade for review, runs validation in a separate worktree, and keeps the original checkout unchanged. Approval unlocks the reviewed patch and its evidence receipt.

## Screen sequence

| Time | Screen/action | Narration cue |
| --- | --- | --- |
| 0:00–0:30 | Show the trusted synthetic repository and clean Git status. | A maintainer has to turn an advisory into a reviewable upgrade. State whether the advisory evidence is recorded or freshly fetched. |
| 0:30–1:20 | Confirm repository trust and start a review. | Explain that tests execute code from this owned repository. A Git worktree is isolation of changes, not a security sandbox. |
| 1:20–2:05 | Inspect selected release, source evidence, diff and commands. | Show the actual validation result. Do not equate a passing fixture test with current production compatibility. |
| 2:05–2:50 | Approve, download the patch and review receipt. | Open source SHA, commands, results and patch digest. Approval does not apply or merge the patch. |
| 2:50–3:30 | Show a recorded failed validation with export unavailable. | Label the recording if this failure is from a separate run. Explain what prevents a failed candidate from being accepted. |
| 3:30–4:15 | Recheck unchanged source and show Strands architecture. | Explain advisory/release tools, deterministic verification and the human decision. End on the concrete review artifacts. |

## Final checks

- Show a useful output and one difficult case, not only a landing page.
- Name Strands Agents SDK and the provider used in the captured run. Use architecture-current.png.
- Distinguish source evidence, model advice, deterministic validation and human approval.
- Python projects with supported manifests and lockfiles; one upgrade per review. Recorded fixture advisories are not a current security audit. No automatic merge.
- Disclose Codex as a development assistant; do not invent user adoption, results or deployments.
- Watch the entire uploaded video while signed out. Confirm public playback, readable text, intelligible audio and a duration under five minutes.
- Copy the verified public video URL into the submission. Recording a file alone does not complete this requirement.
