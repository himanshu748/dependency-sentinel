import { BranchIcon, CheckIcon, PlayIcon, ShieldIcon, WarningIcon } from "../../ui/Icons";

const PIPELINE = [
  {
    id: "01",
    title: "Inspect the checkout",
    body: "Read-only discovery over a canonicalized path constrained to an allowed root. Symlink escapes and out-of-root paths are rejected before anything is read.",
  },
  {
    id: "02",
    title: "Select one candidate",
    body: "A Strands agent picks a single upgrade using typed read-only tools. It cannot write files, run commands or reach the approval gate.",
  },
  {
    id: "03",
    title: "Verify the evidence",
    body: "Deterministic code confirms the advisory and the smallest fixed release, and records the source of each claim alongside the result.",
  },
  {
    id: "04",
    title: "Stage in a disposable worktree",
    body: "The manifest and lockfile change is applied to a throwaway Git worktree. Your source checkout is never written to.",
  },
  {
    id: "05",
    title: "Validate under an allowlist",
    body: "A fixed executable allowlist runs the test command with a bounded timeout. Stored output is redacted for common secret formats.",
  },
  {
    id: "06",
    title: "Halt for a human",
    body: "The run pauses at a persisted approval gate. Approval records the reviewed result; it does not modify the source checkout or publish anything.",
  },
];

const INVARIANTS = [
  "Repository paths are canonicalized and constrained to an allowed root.",
  "The model receives read-only discovery tools only.",
  "Source edits happen in a disposable Git worktree, never in your checkout.",
  "Validation uses a fixed executable allowlist and a bounded runtime.",
  "Stored command output is redacted for common secret formats.",
  "Approval IDs, choices, run transitions and events are persisted.",
  "Replayed run requests and approvals are idempotent.",
];

export function Landing({ onStart }: { onStart: () => void }) {
  return (
    <main id="main" className="console-landing">
      <section className="console-hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <p className="console-eyebrow">
            <span className="status-led" aria-hidden="true" />
            Professional Agents · Agents for Humans
          </p>
          <h2 id="hero-title">One upgrade. Full evidence. Nothing touched without you.</h2>
          <p className="hero-lede">
            A dependency bump is four jobs wearing one hat: security research, release verification,
            a source edit and a test run. Automating all four inside a maintainer's checkout is how
            trust gets lost. Dependency Sentinel separates the reasoning from the execution and shows
            you the seam.
          </p>
          <div className="hero-actions">
            <button type="button" className="primary-action" onClick={onStart}>
              <PlayIcon />Try the demo
            </button>
            <a className="ghost-action" href="#pipeline-title">Inspect the pipeline</a>
          </div>
          <p className="hero-note">
            <ShieldIcon />
            <span>
              Fixture mode is the default. The full workflow runs locally with no AWS account, no
              model spend and no calls to any advisory or package registry.
            </span>
          </p>
        </div>
        <div className="hero-readout" aria-hidden="true">
          <div className="readout-head"><BranchIcon /><span>run/ledger</span></div>
          <dl>
            <div><dt>source checkout</dt><dd className="ok">unchanged</dd></div>
            <div><dt>staged in</dt><dd>disposable worktree</dd></div>
            <div><dt>validation</dt><dd className="ok">allowlisted</dd></div>
            <div><dt>network (fixture)</dt><dd className="ok">none</dd></div>
            <div><dt>gate</dt><dd className="hold">waiting for approval</dd></div>
          </dl>
        </div>
      </section>

      <section className="console-problem" aria-labelledby="problem-title">
        <h2 id="problem-title" className="console-heading"><span aria-hidden="true">//</span>The risk in routine maintenance</h2>
        <div className="problem-grid">
          <article>
            <WarningIcon />
            <h3>Advisories are read, not verified</h3>
            <p>
              A version number copied from a summary is a guess. The fixed release has to be checked
              against the registry that publishes it.
            </p>
          </article>
          <article>
            <WarningIcon />
            <h3>Agents write where they reason</h3>
            <p>
              An agent with file access and shell access in your working tree can leave behind
              changes you did not review and cannot cleanly undo.
            </p>
          </article>
          <article>
            <WarningIcon />
            <h3>Green tests prove nothing you can see</h3>
            <p>
              A passing run that you cannot read, tied to a diff you were not shown, is a claim
              rather than evidence.
            </p>
          </article>
        </div>
      </section>

      <section className="console-pipeline" aria-labelledby="pipeline-title">
        <h2 id="pipeline-title" className="console-heading"><span aria-hidden="true">//</span>How the agent works</h2>
        <p className="console-lede">
          Six ordered stages. The model participates in exactly one of them, and every stage writes
          an entry to a persisted event ledger you can read in the demo.
        </p>
        <ol className="pipeline-list">
          {PIPELINE.map((stage) => (
            <li key={stage.id}>
              <span className="stage-id" aria-hidden="true">{stage.id}</span>
              <div>
                <h3>{stage.title}</h3>
                <p>{stage.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="console-architecture" aria-labelledby="architecture-title">
        <h2 id="architecture-title" className="console-heading"><span aria-hidden="true">//</span>What it is built on</h2>
        <div className="architecture-split">
          <div className="architecture-prose">
            <p>
              A FastAPI service, a SQLite run ledger and a React operations console. The candidate
              agent is built with the open-source <strong>Strands Agents SDK</strong> and is given
              typed, read-only tools.
            </p>
            <p>
              Live mode is opt-in and configured in your own AWS account: an <strong>Amazon
              Bedrock</strong> model provider, plus OSV advisory data and PyPI release data. Each
              model response is capped at 512 tokens to bound quota reservation and cost.
            </p>
            <p className="architecture-caveat">
              <WarningIcon />
              <span>
                This repository demonstrates Strands orchestration locally. It does not claim an
                Amazon Bedrock AgentCore deployment, and in fixture mode it contacts nothing.
              </span>
            </p>
          </div>
          <div className="architecture-diagram" aria-label="Component path">
            <ol>
              <li><code>React console</code><span>risk queue · timeline · evidence</span></li>
              <li><code>FastAPI run API</code><span>idempotent run lifecycle</span></li>
              <li><code>Strands agent</code><span>typed read-only tools</span></li>
              <li><code>Evidence verifier</code><span>advisory + release checks</span></li>
              <li><code>Git worktree</code><span>disposable staging</span></li>
              <li><code>Validator</code><span>allowlist · timeout · redaction</span></li>
              <li><code>Approval gate</code><span>persisted decision</span></li>
              <li><code>SQLite ledger</code><span>ordered event record</span></li>
            </ol>
          </div>
        </div>
      </section>

      <section className="console-invariants" aria-labelledby="invariants-title">
        <h2 id="invariants-title" className="console-heading"><span aria-hidden="true">//</span>Safety invariants</h2>
        <ul className="invariant-list">
          {INVARIANTS.map((item) => (
            <li key={item}><CheckIcon /><span>{item}</span></li>
          ))}
        </ul>
      </section>

      <section className="console-close" aria-labelledby="close-title">
        <h2 id="close-title">Run it against the seeded vulnerable fixture.</h2>
        <p>
          Scan, read the advisory and release evidence, review the proposed diff and the validation
          output, then approve or reject the exact patch.
        </p>
        <button type="button" className="primary-action" onClick={onStart}>
          <PlayIcon />Try the demo
        </button>
      </section>

      <footer className="console-footer">
        <p className="footer-mark"><ShieldIcon /><span>Dependency Sentinel</span></p>
        <p className="footer-meta">
          Built for the Professional Agents track of the Agents for Humans hackathon. Apache-2.0
          licensed. The demo runs against a checked-in vulnerable fixture repository.
        </p>
      </footer>
    </main>
  );
}
