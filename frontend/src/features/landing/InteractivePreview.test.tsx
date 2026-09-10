import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InteractivePreview } from "./InteractivePreview";

describe("Interactive dependency preview", () => {
  it("shows the evidence and diff through labeled controls", () => {
    render(<InteractivePreview />);
    expect(screen.getByLabelText("Illustrative version change")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Evidence" }));
    expect(screen.getByText("One claim. A traceable source.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Illustrative version change")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Diff" }));
    expect(screen.getByLabelText("Illustrative version change")).toBeInTheDocument();
  });
  it("keeps example decisions reversible and clearly unsaved", () => {
    render(<InteractivePreview />);
    fireEvent.click(screen.getByRole("button", { name: "Decision" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve example" }));
    expect(screen.getByRole("status")).toHaveTextContent("Example approved");
    expect(screen.getByText(/No files, approvals or pull requests were saved/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reject example" }));
    expect(screen.getByRole("status")).toHaveTextContent("Example rejected");
    fireEvent.click(screen.getByRole("button", { name: "Reset example" }));
    expect(screen.getByRole("status")).toHaveTextContent("Waiting for your decision");
  });
});
