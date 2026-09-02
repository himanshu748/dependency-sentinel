import type { CandidateSelection } from "../../api/types";
import { CheckIcon, WarningIcon } from "../../ui/Icons";

interface Dependency {
  name: string;
  resolved_version?: string;
}

interface Props {
  dependencies: Dependency[];
  candidate: CandidateSelection;
}

export function RiskQueue({ dependencies, candidate }: Props) {
  const ordered = [...dependencies].sort((item) => (item.name === candidate.package ? -1 : 1));
  return (
    <aside className="risk-queue" aria-label="Risk queue">
      <h2>Risk queue <span>({ordered.length})</span></h2>
      <ol>
        {ordered.map((dependency) => {
          const selected = dependency.name === candidate.package;
          return (
            <li key={dependency.name} className={selected ? "selected" : "clear"}>
              <span className="risk-symbol" aria-hidden="true">
                {selected ? <WarningIcon /> : <CheckIcon />}
              </span>
              <span>
                <strong>{dependency.name} <code>{dependency.resolved_version}</code></strong>
                <small>{selected ? "advisory found" : "no action"}</small>
              </span>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
