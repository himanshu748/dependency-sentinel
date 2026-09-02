import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Dependency Sentinel interface failed", error, info);
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-state" role="alert">
          <strong>Dependency Sentinel could not render.</strong>
          <p>Reload the page to restore the operations console.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Reload console
          </button>
        </main>
      );
    }

    return this.props.children;
  }
}
