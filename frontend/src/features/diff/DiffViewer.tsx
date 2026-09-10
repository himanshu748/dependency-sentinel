import { useState } from "react";

export function DiffViewer({ diff }: { diff: string }) {
  const [expanded, setExpanded] = useState(false);
  const lines = diff.split("\n").filter(Boolean);
  const visibleLines = expanded ? lines : lines.slice(0, 36);
  const gitHeaders = lines.filter((line) => line.startsWith("diff --git ")).length;
  const changedFiles = gitHeaders || new Set(lines.filter((line) => line.startsWith("+++ b/")).map((line) => line.slice(6))).size;
  return (
    <details className="diff-panel" open>
      <summary><span className="disclosure-heading"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m5 3 5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>Proposed changes</span><span>{changedFiles} {changedFiles === 1 ? "file" : "files"}</span></summary>
      <pre aria-label="Proposed dependency diff">
        {visibleLines.map((line, index) => {
          const type = line.startsWith("+") && !line.startsWith("+++")
            ? "addition"
            : line.startsWith("-") && !line.startsWith("---")
              ? "removal"
              : line.startsWith("---") || line.startsWith("+++")
                ? "file"
                : "context";
          const content = type === "addition" || type === "removal" ? line.slice(1) : line;
          const accessibleType = type === "addition" ? "added line" : type === "removal" ? "removed line" : type;
          return (
            <span key={`${index}-${line}`} className={`diff-line ${type}`} aria-label={`${accessibleType}: ${content}`}>
              <i aria-hidden="true">{type === "addition" ? "+" : type === "removal" ? "−" : " "}</i>
              {content}
            </span>
          );
        })}
      </pre>
      {lines.length > 36 && <div className="diff-controls"><p>{expanded ? `Showing all ${lines.length} lines.` : `Showing 36 of ${lines.length} lines. The reviewed download always includes the full patch.`}</p><button type="button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Show compact diff" : "Show full diff"}</button></div>}
    </details>
  );
}
