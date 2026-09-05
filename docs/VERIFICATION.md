# Verification record

Dependency Sentinel is verified at three levels:

- `pytest -q` exercises the deterministic backend workflow, approval boundary, path safety, idempotency, and API behavior.
- `npm test` passes 9 React interaction tests covering the landing path plus empty, loading, evidence, approval, rejection, error, and theme states.
- `npm run test:e2e` passes 4 checks in desktop Chromium and a Pixel 7 viewport, including landing-to-demo navigation, persisted theme behavior, and responsive overflow checks at 390, 768, and 1440 pixels.
- `npm run build` produces the production frontend bundle successfully.

On 2026-09-05 the backend suite passed 59 tests, including real Strands fixture tool dispatch, the AgentCore HTTP contract, session cleanup on failure, local-only demo serving, and an offline cloud-advisory fixture. ARM64 direct-code packaging succeeded. Deployment was attempted but AWS rejected S3 with `NotSignedUp`; the Nova access check hit a daily-token limit. No successful cloud deployment or inference is claimed. See [qualification record](QUALIFICATION.md).

The one-command demo was checked in the browser on 2026-09-05 at localhost:8202. It created an isolated fixture repository, showed two dependencies, staged the Jinja2 upgrade, displayed two passing validation tests and paused for approval. Approval completed the evidence record while the source checkout stayed unchanged. The launcher forces scripted fixture mode even when the checkout is renamed.

The committed captures in `docs/screenshots/` were produced from the running application. The landing page captures have one page-level heading, no browser console errors, and no horizontal overflow. The workflow captures show the approval gate, evidence, proposed diff, validation output, and mobile timeline. All demo values come from the seeded local fixture; no live advisory or package registry is contacted.
