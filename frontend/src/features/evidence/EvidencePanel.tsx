import type { RunEvent } from "../../api/types";
import { ExternalIcon, RepositoryIcon, ShieldIcon } from "../../ui/Icons";

interface Source {
  publisher?: string;
  url?: string;
  retrieved_at?: string;
}

function sourceUrl(value?: string) {
  if (!value) return undefined;
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : undefined; } catch { return undefined; }
}

interface Advisory {
  identifier?: string;
  summary?: string;
  source?: Source;
}

interface Release {
  version?: string;
  summary?: string;
  source?: Source;
}

export function EvidencePanel({ event }: { event?: RunEvent }) {
  const advisories = (event?.payload.advisories as Advisory[] | undefined) || [];
  const release = event?.payload.release as Release | undefined;
  const evidenceCount = advisories.length + Number(Boolean(advisories[0]?.source)) + Number(Boolean(release));
  return (
    <details className="evidence-panel" open>
      <summary>
        <span className="disclosure-heading"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m5 3 5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>Evidence</span> <span>{evidenceCount}</span>
      </summary>
      <div className="evidence-list">
        {advisories.map((advisory) => (
          <a key={advisory.identifier} href={sourceUrl(advisory.source?.url)} target="_blank" rel="noreferrer">
            <ShieldIcon />
            <span><strong>{advisory.identifier}</strong><small>{advisory.summary}</small></span>
            <ExternalIcon />
          </a>
        ))}
        {advisories[0]?.source && (
          <a href={sourceUrl(advisories[0].source.url)} target="_blank" rel="noreferrer">
            <RepositoryIcon />
            <span><strong>{advisories[0].source.publisher}</strong><small>Published advisory evidence</small></span>
            <ExternalIcon />
          </a>
        )}
        {release && (
          <a href={sourceUrl(release.source?.url)} target="_blank" rel="noreferrer">
            <RepositoryIcon />
            <span><strong>PyPI {release.version}</strong><small>{release.summary}</small></span>
            <ExternalIcon />
          </a>
        )}
        {!advisories.length && !release && <p className="panel-empty">No advisory or release evidence was recorded. This run is not ready for approval.</p>}
        {event && <p className="evidence-caption">Recorded <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>. Source links open externally; a saved review does not refresh their contents.</p>}
      </div>
    </details>
  );
}
