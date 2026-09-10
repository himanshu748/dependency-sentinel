# Judging evidence for Dependency Sentinel

Checked September 10, 2026 using the live Devpost criteria and rules. The five criteria are equally weighted on a 1–5 scale. This is our evidence map, not a prediction of the judges' score. [Official rules](https://agentsforhumans.devpost.com/rules)

## Audience and job

Maintainers reviewing dependency upgrades in their own trusted Python repositories.

An advisory alone leaves a maintainer to choose a release, inspect compatibility, run tests and preserve the evidence behind the decision.

The intended workflow: Read a clean owned checkout, select one evidence-backed upgrade, stage and validate it separately, review evidence and test results, then approve export of the patch and receipt.

## Evidence by criterion

| Criterion | Evidence to show | Remaining proof |
| --- | --- | --- |
| Technological Implementation | Strands can read manifest, advisory and release evidence. Deterministic checks validate the candidate and bind the exported patch to the reviewed source and test results. | Fresh real-model execution and free working judge access. AgentCore and a live URL can strengthen this score but are optional. |
| Design | Trust confirmation, progress, evidence, diff, failed-run boundaries, saved runs and approved downloads are part of the same review. | Record intake through final artifact, including an error or uncertain state. |
| Potential Impact | Demonstrate the reviewer receiving an exact patch plus test and evidence provenance while the original checkout stays unchanged. No vulnerability coverage or measured time-saving claim is made. | User feedback or observed task timings would strengthen the claim; neither has been measured here. |
| Creativity & Originality | The product returns an approval-bound review receipt as well as a patch. It makes the reviewed source revision, validation and export relationship inspectable. | Explain the domain tradeoff with a concrete difficult example. |
| Presentation | A timed script in DEMO_SCRIPT.md connects audience, problem, decisions and output. | Public YouTube/Vimeo video no longer than five minutes. |

Track: **Professional Agents**. Python projects with supported manifests and lockfiles; one upgrade per review. Recorded fixture advisories are not a current security audit. No automatic merge.

## Difficult case and useful output

Show a failing validation or missing evidence record and the blocked export. A worktree is not a security sandbox; use only a trusted synthetic repository.

Download the patch and JSON receipt. Check the original Git HEAD and clean status before and after approval.

## Current verification

- Automated checks: 171 backend + 54 frontend tests, with the frontend production build passing.
- The workspace's Connection details panel makes only a local health request. It distinguishes scripted responses from configured external/Bedrock/AgentCore inference; it never claims that configuration proves access.
- Unknown runtime configurations and failed health requests are labeled, not interpreted as success.
- Real Qwen evidence is dated September 9 in QWEN-VERIFICATION.md. The owner subsequently stopped the endpoint. No new inference is established by offline tests.
- RELEASE-CHECKLIST.md tracks architecture, public repository, video, Builder ID, eligibility, judge access and final submission separately.

## Bonus plan and release boundary

Optional public builder.aws posts can add 0.2 points each, up to 0.6. Drafts are not bonus proof. Describe the actual Strands implementation and provider boundary; do not claim AWS hosting or AgentCore deployment.

Before submission, provide the public video and free working access through judging, confirm the entrant's Builder ID and eligibility, review the official rules, and verify the Devpost receipt. Do not replace those steps with a test count.
