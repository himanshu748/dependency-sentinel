# Release QA, September 10, 2026

## Judging follow-up

The judging-focused revision passed 499 tests: StudyPilot 101 backend/37 frontend,
Dependency Sentinel 171/54, and ScamShield 104/32. All three frontend production
builds passed. The earlier 472-test record below describes the previous release.

The new Connection details panel was checked in Chromium at 1440×1000 and 390×1000.
Keyboard Enter opened and closed it; the real local health response displayed
scripted mode without claiming model access. The three fixture approval workflows
were repeated successfully. Page identity, nonempty rendering, no error overlay,
console health and tested landing/panel horizontal overflow checks passed.

Unit tests cover configured external/Bedrock/AgentCore modes, unknown metadata,
failed checks and cancellation. These do not prove provider availability. No model
endpoint was resumed. Browser plugin was unavailable, so bundled Playwright was
used. Screenshots and the browser harness remain outside the repository.

JUDGING.md maps each criterion to evidence and remaining proof. The revised
DEMO_SCRIPT.md includes a difficult case and final artifact. Submission-copy and
Builder Center article drafts are local and ignored; no publication is claimed.

## Earlier release record

All checks below used the local September 10 release candidate. The Modal endpoint
remained stopped. Real Qwen evidence is dated September 9 and recorded separately
in QWEN-VERIFICATION.md.

## Checks

| Project | Backend tests | Frontend tests | Frontend build |
| --- | ---: | ---: | --- |
| StudyPilot | 101 passed | 28 passed | Passed |
| Dependency Sentinel | 171 passed | 45 passed | Passed |
| ScamShield | 104 passed | 23 passed | Passed |

Total: 472 automated tests passed. Starlette emitted deprecation warnings; these
were not runtime failures.

The same 472 tests passed again from clean exports of the staged source, without
private environment files or local databases. Frontend dependencies were installed
from their lockfiles with `npm ci --ignore-scripts`, then tested and built in each
export. Backend tests used the existing pinned virtual environments with the
exported source on `PYTHONPATH`; this was not a fresh Python dependency installation.

All three rendered apps passed at 1440×1000 and 390×1000: correct page title,
nonempty content, no framework overlay, no console/page errors, no horizontal
overflow on the tested landing pages, and working primary controls. Browser plugin
was unavailable; the bundled Playwright 1.62.1 runtime was used without installing
new browser dependencies.

## Browser workflow evidence

- StudyPilot: overview → Open planner → fictional coursework → Build this week →
  approve exact sessions → calendar-events-added confirmation.
- Dependency Sentinel: overview → Open workspace → owned generated sample repository →
  explicit local-test authorization → scan → approve validated patch →
  Download reviewed patch available.
- ScamShield: overview → Check a message → labeled fictional message → analyze →
  Generate local report → Local report ready.

These were real UI/API/database interactions with scripted model responses.
They do not establish new live inference or current OSV/PyPI evidence. Temporary
demo databases and the generated repository were separate from user data.

## Changes validated

Provider failures now distinguish denied access, usage/capacity limits and a stopped
or warming endpoint without returning credentials or raw provider responses.
Dependency Sentinel's test configuration uses explicit fixture paths and evidence,
so running the suite from the repository root no longer depends on a developer's
private environment file.

The current architecture attachment was rendered from architecture-current.svg in
Chromium. The old architecture files remain historical artifacts; use the current
PNG for the submission.

## Release boundaries

No judge video, public hosting, Builder ID, bonus publication or Devpost submission
receipt is established by these checks. See RELEASE-CHECKLIST.md. Model inference
requires deliberate resumption of the stopped service or another funded provider.

Screenshots and the temporary Playwright harness were captured outside source.
The staged-text credential-pattern scan found no matches; it omitted the generated
architecture PNG, which was visually reviewed and generated from the scanned SVG.
The scan did not inspect Git history or unknown secret formats.
