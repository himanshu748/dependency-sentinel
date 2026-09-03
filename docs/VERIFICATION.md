# Verification record

Dependency Sentinel is verified at three levels:

- `pytest -q` exercises the deterministic backend workflow, approval boundary, path safety, idempotency, and API behavior.
- `npm test` exercises the React empty, loading, evidence, approval, rejection, error, and theme states.
- `npm run test:e2e` runs the real Vite application in desktop Chromium and a Pixel 7 viewport, including persisted theme behavior.

The committed captures in `docs/screenshots/` were produced from the running application. They show the approval gate, evidence, proposed diff, validation output, and mobile timeline. All values visible in these captures come from the seeded local fixture; no live advisory or package registry is contacted during the demo.
