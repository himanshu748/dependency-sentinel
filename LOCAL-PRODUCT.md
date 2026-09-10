# Local product workflow

Verified 2026-09-07. This increment accepts your own inputs; sample scenarios remain optional. It is local-only, not a public multi-user release or a verified live AgentCore deployment.

## Start

Use the existing repository setup instructions to install dependencies. From the repository root, start the API in one terminal:

```sh
cd backend
DEPENDENCY_SENTINEL_FIXTURE_MODE=true \
DEPENDENCY_SENTINEL_EVIDENCE_MODE=live \
DEPENDENCY_SENTINEL_REPOSITORY_ROOT=/absolute/path/to/trusted-repositories \
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

In a second terminal:

```sh
cd frontend
npm run dev -- --config vite.config.ts --host 127.0.0.1 --port 5179 --strictPort
```

Open http://127.0.0.1:5179/. The frontend proxies /api to port 8001. The overview is available through Back to overview or /#overview.

## What works and what is limited

Enter an absolute path to a trusted local Python Git repository under the configured root. It needs pyproject.toml, uv.lock and runnable tests. Confirm that you trust its code, then scan, review the evidence/diff/test results and approve or reject. Approval records acceptance; it does not edit the source checkout. Download the reviewed patch and apply it yourself after review.

OSV and PyPI are real public network sources in this mode; candidate selection remains local and deterministic. The runner resolves the upgraded lockfile with uv and tests in that environment. A worktree is not a security sandbox: tests and package builds execute on your machine. Do not use an untrusted repository or expose this API publicly. Optional VITE_DEMO_REPOSITORY enables the sample-path button only when you provide a path.

Verified against an isolated owned test repository: Jinja2 3.1.2 to 3.1.6, OSV advisory GHSA-cpwx-vrp4-4pq7, real regenerated uv.lock and 1 passing repository test. Browser approval and patch download succeeded; git apply --check passed; source git status stayed clean. This is a small integration test, not broad repository compatibility proof. Backend: 64 tests; frontend: 14 tests; production build passed.

## Cost and data boundary

The commands above force local scripted model behavior. No AWS inference or deployment was started for these checks. The authorized ceiling is $50 in covered AWS credits and $0 from the bank; credit eligibility and billing safeguards have not been verified here. Do not switch off fixture mode or deploy based on this local validation.

Desktop light and mobile dark input screens were captured under .impeccable/review/. Browser downloads are under output/playwright/. No changes from this increment have been pushed to GitHub.
