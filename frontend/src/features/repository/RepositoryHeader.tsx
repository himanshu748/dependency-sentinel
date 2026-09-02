import { BranchIcon, CommitIcon, PlayIcon, RepositoryIcon, ThemeIcon } from "../../ui/Icons";

interface Props {
  repository: string;
  onRepositoryChange: (value: string) => void;
  onScan: () => void;
  isScanning: boolean;
  retry: boolean;
  branch?: string;
  head?: string;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export function RepositoryHeader({
  repository,
  onRepositoryChange,
  onScan,
  isScanning,
  retry,
  branch = "main",
  head = "pending",
  theme,
  onToggleTheme,
}: Props) {
  return (
    <header className="repository-header">
      <h1>Dependency Sentinel</h1>
      <form
        className="repository-form"
        onSubmit={(event) => {
          event.preventDefault();
          onScan();
        }}
        aria-busy={isScanning}
      >
        <label className="repository-field" htmlFor="repository-path">
          <span>Repository path</span>
          <span className="repository-input">
            <RepositoryIcon />
            <input
              id="repository-path"
              type="text"
              autoComplete="off"
              spellCheck={false}
              required
              value={repository}
              onChange={(event) => onRepositoryChange(event.target.value)}
            />
          </span>
        </label>
        <div className="repository-meta" aria-label="Repository revision">
          <span><BranchIcon />{branch}</span>
          <span><CommitIcon />{head.slice(0, 7)}</span>
        </div>
        <button
          type="submit"
          className="primary-action"
          disabled={isScanning || !repository}
          aria-busy={isScanning}
        >
          <PlayIcon />
          {isScanning ? "Scanning repository…" : retry ? "Retry scan" : "Scan repository"}
        </button>
      </form>
      <button
        type="button"
        className="theme-action"
        onClick={onToggleTheme}
        aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
      >
        <ThemeIcon />
      </button>
    </header>
  );
}
