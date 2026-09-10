import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Landing } from "./Landing";

describe("Landing preview", () => {
  it("describes hosted storage and inference without claiming offline execution", () => {
    vi.stubEnv("VITE_HOSTED", "true");
    try {
      render(<Landing onStart={vi.fn()} />);
      expect(screen.getByText(/This hosted build uses Groq through AWS AgentCore/)).toBeInTheDocument();
      expect(screen.queryByText(/does not claim an Amazon Bedrock/)).not.toBeInTheDocument();
    } finally {
      vi.unstubAllEnvs();
    }
  });
  it("labels the preview as illustrative and makes its explanation expandable", () => {
    render(<Landing onStart={vi.fn()} />);
    const preview = screen.getByRole("complementary", { name: "Illustrative dependency review" });
    expect(within(preview).getByText(/Illustrative preview/)).toBeInTheDocument();
    const disclosure = within(preview).getByText("What does approval actually do?");
    const details = disclosure.closest("details");
    expect(details).not.toHaveAttribute("open");
    fireEvent.click(disclosure);
    expect(details).toHaveAttribute("open");
    fireEvent.click(disclosure);
    expect(details).not.toHaveAttribute("open");
  });

  it("keeps the demo call to action functional", () => {
    const onStart = vi.fn();
    render(<Landing onStart={onStart} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Open workspace" })[0]);
    expect(onStart).toHaveBeenCalledOnce();
  });
});
