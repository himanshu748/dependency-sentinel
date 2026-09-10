import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { HostedNotice } from "./features/connection/HostedNotice";
import { ErrorBoundary } from "./app/ErrorBoundary";
import "./styles/tokens.css";
import "./styles/app.css";
import "./features/landing/preview.css";
import "./features/landing/interaction.css";
import "./styles/product.css";

import "./styles/distinct.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <HostedNotice /><App />
    </ErrorBoundary>
  </StrictMode>,
);
