# Release checklist

Checked September 10, 2026 against the live Devpost rules, required fields, judging
criteria, dates, and organizer announcements for [Agents for Humans](https://agentsforhumans.devpost.com/rules).

This is a release checklist, not a claim that the entry has been submitted or qualifies for a prize.

## Required deliverables

| Item | Current evidence | Release gate |
| --- | --- | --- |
| Meaningful Strands implementation | Real Qwen tools and approval workflow verified September 9; offline regression suites | Repeat a fresh scenario when the endpoint is deliberately resumed |
| Public code and MIT/Apache license | Public himanshu748/dependency-sentinel; GitHub detects Apache-2.0 | Publish and verify the tested release commit, including assets and lockfiles |
| README and testing instructions | README, ACTIVATION.md, MODAL.md, QWEN-VERIFICATION.md | A stranger can follow setup without private account knowledge |
| Architecture diagram | architecture-current.png and editable SVG | Attach the current PNG to required Devpost field 27734 |
| Public video, at most five minutes | DEMO_SCRIPT.md | Record real execution, pitch the problem/audience/value, upload to YouTube or Vimeo, verify public playback |
| AWS Builder ID | Not verified in this pass | Confirm the actual Builder ID for required field 27735 |
| Entrant eligibility and ownership | Solo entrant with AI-assistant disclosure in README | Entrant confirms eligibility, original contest-period work, reuse disclosure and rules |
| Free working-project access for judges | Scripted demo can run locally; real-model endpoint is stopped | Arrange free real-model testing through the judging period; do not substitute a paid BYO key or scripted behavior for the advertised product |
| Completed Devpost entry | No matching entry in the connected account's project list on September 10 | Create the entry, attach required materials, explicitly approve submission, verify receipt |

## Track and product story

Dependency Sentinel targets **Professional Agents**. The demonstrated loop is:
Owned, trusted Git repository → Read manifest and release evidence → Stage worktree and run tests → Review evidence, diff and tests → Approved patch and review receipt.

A worktree is not a security sandbox. Use only owned, trusted repositories. Recorded fixture advisory checks are distinct from fresh live OSV/PyPI evidence. Passing fixture tests does not establish full application compatibility.

## Optional scoring opportunities

The organizer's September 9 update confirms: “No — use whatever model you want. It won't affect your eligibility.”

AgentCore deployment and a live demo can strengthen technical implementation, but
are optional. Builder Center posts are optional bonus evidence: 0.2 points each,
up to 0.6. Relevant posts must be public before the deadline. The current article
drafts are not published proof. Do not invent AWS deployments or impact numbers to
make an article sound stronger.

## Ordered release work

1. Complete and record the real product loop with a fresh, non-sensitive example.
2. Review desktop/mobile controls, failed requests, keyboard use and exports.
3. Verify the public repository commit and current architecture attachment.
4. Publish one honest end-to-end video per entry and verify playback.
5. Resolve free judge access, Builder ID, entrant facts and any reuse disclosure.
6. Publish only evidence-backed bonus posts; add their verified public URLs.
7. Review the completed Devpost form and submit only after explicit approval.

The submission cutoff is September 15 at 05:30 IST. Judge access must remain
available through October 9 at 05:30 IST. The official website prevails if its
rules change or differ from this dated checklist.

## Cost and runtime state

The shared Qwen app was stopped on September 9 at the owner's request. Offline
checks do not restart it. The approved Modal workspace usage limit is $25 across
all its apps; that is separate from AWS budgets. Cached model storage remains.
Credits and budgets are not a promise that every future charge is impossible.
