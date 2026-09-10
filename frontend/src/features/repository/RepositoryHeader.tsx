import { BranchIcon, CommitIcon, PlayIcon, RepositoryIcon, ThemeIcon } from "../../ui/Icons";

interface Props {
  onBack: () => void;
  repository: string;
  onRepositoryChange: (value: string) => void;
  onScan: () => void;
  isScanning: boolean;
  retry: boolean;
  trusted: boolean;
  onTrustedChange: (value: boolean) => void;
  branch?: string;
  head?: string;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export function RepositoryHeader({
  onBack,
  repository,
  onRepositoryChange,
  onScan,
  isScanning,
  retry,
  trusted,
  onTrustedChange,
  branch = "not inspected",
  head = "pending",
  theme,
  onToggleTheme,
}: Props) {
  return (
    <header className="repository-header">
      <h1>Dependency Sentinel</h1>
      <div className="repository-header-actions">
        <button type="button" className="nav-action subtle" onClick={onBack}>Back to overview</button>
        <button
          type="button"
          className="theme-action"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
        >
          <ThemeIcon />
        </button>
      </div>
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
              disabled={isScanning}
              placeholder="/absolute/path/to/your-python-repository"
              value={repository}
              onChange={(event) => onRepositoryChange(event.target.value)}
            />
          </span>
        </label>
        <div className="repository-meta" aria-label="Repository revision">
          <span><BranchIcon />{branch}</span>
          <span><CommitIcon />{head.slice(0, 7)}</span>
        </div>
        <div className="trust-contract">
          <label><input type="checkbox" checked={trusted} disabled={isScanning} onChange={(event) => onTrustedChange(event.target.checked)} aria-describedby="repository-trust-note" /> I own or trust this repository and authorize running its tests locally.</label>
          <p id="repository-trust-note">A worktree protects your source files, not your machine. Do not run untrusted code.</p>
        </div>
        <button
          type="submit"
          className="primary-action"
          disabled={isScanning || !repository.trim()}
          aria-busy={isScanning}
        >
          <PlayIcon />
          {isScanning ? "Scanning repository…" : retry ? "Retry scan" : "Scan repository"}
        </button>
      </form>
    </header>
  );
}
