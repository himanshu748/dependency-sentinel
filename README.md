# Dependency Sentinel

Dependency Sentinel is an evidence-first maintenance agent for the Professional Agents track of the Agents for Humans Hackathon. It finds one vulnerable Python dependency, verifies the smallest fixed release, stages the upgrade in a disposable Git worktree, runs validation and pauses for a human decision.

It never edits the selected source checkout.

![Dependency Sentinel public landing page](docs/screenshots/landing-desktop.png)

## Why this project

Routine dependency upgrades combine security research, release verification, source changes and test execution. Automating all of that directly in a maintainer's checkout creates unnecessary risk. Dependency Sentinel separates reasoning from execution and makes the boundary visible:

1. A Strands agent selects one candidate using typed read-only tools.
2. Deterministic application code verifies advisory and release evidence.
3. A disposable worktree receives the proposed manifest and lockfile changes.
4. A fixed command allowlist runs validation with a timeout and secret redaction.
5. The run pauses at a persisted approval gate.
6. Approval records the reviewed result. It does not silently modify the source checkout or publish anything.

## One-command judging demo

Prerequisites: Python 3.11+, uv, Node.js 20.19+ (22.12+ recommended), npm, Git and Bash.

```bash
python3 scripts/demo.py
```

Open `http://127.0.0.1:8000`. This installs locked dependencies, builds the frontend, and serves the UI and API from one local process. It forces scripted fixture mode even if your environment enables AWS, uses temporary demo data, and removes that data when stopped with Ctrl+C. First-time dependency installation needs internet access; the demo itself does not call a model. Use `--port 8201` to avoid a port conflict. After installation, `--skip-install` reuses dependencies.

This is a local judging build, not a public hosted service. Live Bedrock inference and AgentCore deployment remain unverified.

## Architecture

```mermaid
flowchart LR
    UI[React operations console] --> API[FastAPI run API]
    API --> Agent[Strands candidate agent]
    Agent --> Tools[Typed read-only tools]
    Tools --> Sources[Repository, OSV and PyPI]
    API --> Worktree[Disposable Git worktree]
    Worktree --> Validator[Allowlisted validation]
    Validator --> Gate[Persisted human approval]
    API --> Store[(SQLite run ledger)]
```

The default fixture mode is deterministic and requires no AWS account. Live mode uses the same workflow with a Strands `Agent`, an Amazon Bedrock model, OSV advisory data and PyPI release data.

## Reproducible local demo

Prerequisites: Git, Python 3.11+, [uv](https://docs.astral.sh/uv/) and Node.js 20+.

Create the standalone vulnerable fixture repository:

```bash
./scripts/create_demo_repository.sh
cp .env.example .env
```

The script prints the absolute repository path. The default `.env.example` allows repositories under `demo-repositories/` and keeps temporary worktrees under `backend/data/workspaces/`.

Start the API:

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload
```

In another terminal, start the interface and pass the path printed by the setup script:

```bash
cd frontend
npm ci
VITE_DEMO_REPOSITORY=/absolute/path/to/demo-repositories/vulnerable-python-project npm run dev
```

Open `http://127.0.0.1:5173`, scan the fixture and review the evidence, diff, validation output and exact approval gate.

## Live Bedrock mode

Set these values in the repository root `.env`:

```dotenv
AWS_PROFILE=your-profile
BEDROCK_MODEL_ID=your-supported-model-id
DEPENDENCY_SENTINEL_AWS_REGION=us-east-1
DEPENDENCY_SENTINEL_FIXTURE_MODE=false
```

`amazon.nova-micro-v1:0` is an on-demand text-model example listed in `us-east-1`; verify access in your own account before enabling live mode. The Bedrock client explicitly caps each response at 512 tokens to bound quota reservation and cost.

Live mode can use paid AWS services and public advisory APIs. Confirm your AWS budget and model access before enabling it. The current repository demonstrates Strands Agents SDK orchestration locally. It does not claim an Amazon Bedrock AgentCore deployment.

## API surface

- `POST /api/runs` starts an idempotent maintenance run
- `GET /api/runs/{run_id}` returns the persisted run
- `GET /api/runs/{run_id}/events` returns the ordered event ledger
- `GET /api/runs/{run_id}/events/stream` streams run events with SSE
- `POST /api/runs/{run_id}/approvals` records the exact approval or rejection
- `GET /api/health` reports fixture and model configuration

## Verification

Backend:

```bash
cd backend
uv run pytest -q
uv run ruff check .
```

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```

End-to-end:

```bash
cd frontend
npm run test:e2e
```

The checked-in fixture test asserts that validation runs against the staged Jinja2 3.1.5 manifest and lockfile. Nine frontend interaction tests pass. Four Playwright checks verify the real Vite application in desktop Chromium and a Pixel 7 viewport, including landing-to-demo navigation, persisted theme behavior, and no horizontal overflow at 390, 768, and 1440 pixel widths. See [the verification record](docs/VERIFICATION.md).

| Landing | Mobile landing | Approval console | Mobile evidence |
| --- | --- | --- | --- |
| [Desktop](docs/screenshots/landing-desktop.png) | [Mobile](docs/screenshots/landing-mobile.png) | [Desktop](docs/screenshots/desktop-approval.png) | [Timeline](docs/screenshots/mobile-timeline.png) and [approval](docs/screenshots/mobile-approval.png) |

## Hackathon technology and outstanding requirements

The free demo now executes a real Strands Agent using a scripted model provider, including tool dispatch and structured output. Live mode uses Amazon Bedrock directly or the optional AgentCore advisory service, which accepts a locked dependency snapshot and returns a candidate for independent local verification. See [AgentCore setup](docs/AGENTCORE.md).

The backend suite now passes 59 tests. The [qualification record](docs/QUALIFICATION.md) documents remaining publication and account requirements. The [architecture PNG](docs/architecture.png), [Builder Center article draft](docs/BUILDER_POST.md) and [demo video outline](docs/DEMO_SCRIPT.md) are prepared. An article draft does not earn bonus points until it is publicly published on Builder Center.

## Safety properties

- Repository paths are canonicalized and constrained to an allowed root
- Symlink escapes and non-root paths are rejected
- The model receives read-only discovery tools only
- Source edits happen in a disposable Git worktree
- Validation uses a fixed executable allowlist and bounded runtime
- Stored command output is redacted for common secret formats
- Approval IDs, choices, run transitions and events are persisted
- Replayed run requests and approvals are idempotent

## Development disclosure

Himanshu Kumar is the solo entrant. Codex assisted implementation, testing and documentation; Claude Desktop assisted the landing-page implementation. Product decisions and submission responsibility remain with the entrant.

## License

Apache-2.0
