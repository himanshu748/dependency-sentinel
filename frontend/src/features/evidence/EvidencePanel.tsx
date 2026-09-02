import type { RunEvent } from "../../api/types";
import { ExternalIcon, ShieldIcon } from "../../ui/Icons";

interface Source {
  publisher?: string;
  url?: string;
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
  return (
    <details className="evidence-panel" open>
      <summary>
        Evidence <span>{advisories.length * 2 + (release ? 1 : 0)}</span>
      </summary>
      <div className="evidence-list">
        {advisories.map((advisory) => (
          <a key={advisory.identifier} href={advisory.source?.url} target="_blank" rel="noreferrer">
            <ShieldIcon />
            <span><strong>{advisory.identifier}</strong><small>{advisory.summary}</small></span>
            <ExternalIcon />
          </a>
        ))}
        {advisories[0]?.source && (
          <a href={advisories[0].source.url} target="_blank" rel="noreferrer">
            <span className="source-mark" aria-hidden="true">◎</span>
            <span><strong>{advisories[0].source.publisher}</strong><small>Published advisory evidence</small></span>
            <ExternalIcon />
          </a>
        )}
        {release && (
          <a href={release.source?.url} target="_blank" rel="noreferrer">
            <span className="source-mark cube" aria-hidden="true">◇</span>
            <span><strong>PyPI {release.version}</strong><small>{release.summary}</small></span>
            <ExternalIcon />
          </a>
        )}
      </div>
    </details>
  );
}
