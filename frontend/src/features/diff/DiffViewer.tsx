export function DiffViewer({ diff }: { diff: string }) {
  const lines = diff.split("\n").filter(Boolean);
  return (
    <details className="diff-panel" open>
      <summary>Proposed changes <span>2 files</span></summary>
      <pre aria-label="Proposed dependency diff">
        {lines.map((line, index) => {
          const type = line.startsWith("+") && !line.startsWith("+++")
            ? "addition"
            : line.startsWith("-") && !line.startsWith("---")
              ? "removal"
              : line.startsWith("---") || line.startsWith("+++")
                ? "file"
                : "context";
          const content = type === "addition" || type === "removal" ? line.slice(1).trim() : line;
          const accessibleType = type === "addition" ? "added line" : type === "removal" ? "removed line" : type;
          return (
            <span key={`${index}-${line}`} className={`diff-line ${type}`} aria-label={`${accessibleType}: ${content}`}>
              <i aria-hidden="true">{type === "addition" ? "+" : type === "removal" ? "−" : " "}</i>
              {content}
            </span>
          );
        })}
      </pre>
    </details>
  );
}
