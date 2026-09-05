# Agents for Humans: building Dependency Sentinel with Strands and verifiable upgrade evidence

A dependency upgrade looks like a one-line change until someone has to verify the advisory, find an appropriate fixed release, edit the lockfile, run validation, and decide whether the result is acceptable. For a solo maintainer, that repeated work is the problem Dependency Sentinel addresses.

The application takes one locked Python dependency through that process and presents an evidence report. It keeps the selected source checkout unchanged throughout the demonstration.

## Give Strands a constrained job

The project uses the Strands Agents SDK to choose one dependency candidate using read-only discovery tools. The local Bedrock path can inspect a repository, scan its manifest, query advisory evidence and check a release. Its result is a typed CandidateSelection containing the package, current version, target version, advisory identifier and rationale.

The execution code verifies that selection against the locked manifest and fetched advisory. The package and current version must exist in the snapshot. The target must be newer and must be listed as fixed in the cited advisory. Release evidence must agree with the proposed package and version.

This check prevents the rest of the workflow from treating fluent model output as proof.

## Make every consequential step visible

After evidence verification, the application applies the manifest and lockfile changes in a disposable Git worktree. A command allowlist and timeout constrain validation. The resulting diff, command output, evidence and run events appear in the interface.

The approval action records the user's review of the validated patch report. It does not merge a pull request or modify the original checkout. That limitation is deliberate and documented; a later integration could add a separately approved publishing operation.

A SQLite run ledger persists the ordered events and decisions. Idempotency checks protect the workflow from replayed run requests and approval messages.

## Reproducible orchestration without paid inference

The default demo uses checked-in advisory and release fixtures. Its scripted model provider drives a real Strands Agent through tool dispatch and structured output. The fixture is not a simulated success screen: the application scans a real seeded Git repository, stages a change, runs the configured validation command and reaches an approval gate.

The model responses are deterministic in this mode. This makes the demo and tests reproducible without describing them as live model inference.

## Adding an AgentCore advisory service

A cloud process cannot inspect an arbitrary path on a maintainer's laptop. The AgentCore design therefore accepts a bounded manifest snapshot rather than a local filesystem path.

Inside the optional Amazon Bedrock AgentCore Runtime, a Strands agent reads that snapshot and uses read-only OSV and PyPI tools. It returns a candidate to the local application. Independent verification, worktree changes, validation and approval stay local.

The service uses Nova Micro with a 512-token response cap and an eight-call request budget. The AWS SDK client invokes the runtime with IAM authentication and stops the session afterward. Direct-code packaging targets Linux ARM64 and uses locked dependencies.

The implementation is ready for cloud verification, but the attempted deployment did not succeed: AWS returned NotSignedUp for S3 in the available account. The public documentation records that blocker instead of showing an unverified deployment badge.

## What the project demonstrates

The aim is to reduce routine maintenance work while preserving the evidence a maintainer needs to make a decision. The project does not claim to eliminate dependency risk or prove every upgrade safe. It shows one candidate, one verified advisory path, one staged change and one explicit human decision.

Codex and Claude assisted implementation, UI work and review. The repository includes setup instructions, tests, an architecture attachment and the verification record.

Source: https://github.com/himanshu748/dependency-sentinel
