import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { HostedNotice } from "./HostedNotice";

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it("keeps privacy details collapsed and specific to this product", async () => {
  vi.stubEnv("VITE_HOSTED", "true");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ hosted: true }) }));
  render(<HostedNotice />);
  const summary = screen.getByText("Privacy & usage");
  const details = summary.closest("details");
  expect(details).not.toHaveAttribute("open");
  expect(screen.getByText("No sign-up needed")).toBeInTheDocument();
  fireEvent.click(summary);
  expect(details).toHaveAttribute("open");
  expect(screen.getByText(/Your reviews are saved on the server/)).toBeInTheDocument();
  expect(screen.getByText(/included sample repository/)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText(/AI provider: Groq/)).toBeInTheDocument());
  fireEvent.click(summary);
  expect(details).not.toHaveAttribute("open");
});

it("does not add hosting copy or requests to the local build", () => {
  vi.stubEnv("VITE_HOSTED", "false");
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const { container } = render(<HostedNotice />);
  expect(container).toBeEmptyDOMElement();
  expect(fetcher).not.toHaveBeenCalled();
});
