# Verification record

Dependency Sentinel is verified at three levels:

- `pytest -q` exercises the deterministic backend workflow, approval boundary, path safety, idempotency, and API behavior.
- `npm test` passes 9 React interaction tests covering the landing path plus empty, loading, evidence, approval, rejection, error, and theme states.
- `npm run test:e2e` passes 4 checks in desktop Chromium and a Pixel 7 viewport, including landing-to-demo navigation, persisted theme behavior, and responsive overflow checks at 390, 768, and 1440 pixels.
- `npm run build` produces the production frontend bundle successfully.

The committed captures in `docs/screenshots/` were produced from the running application. The landing page captures have one page-level heading, no browser console errors, and no horizontal overflow. The workflow captures show the approval gate, evidence, proposed diff, validation output, and mobile timeline. All demo values come from the seeded local fixture; no live advisory or package registry is contacted.
