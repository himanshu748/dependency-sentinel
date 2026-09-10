import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { DiffViewer } from "./DiffViewer";


it("labels additions and removals without relying on color alone", () => {
  render(
    <DiffViewer
      diff={'--- a/pyproject.toml\n+++ b/pyproject.toml\n-"jinja2==3.1.4"\n+"jinja2==3.1.5"\n'}
    />,
  );

  expect(screen.getByText('"jinja2==3.1.4"')).toHaveAccessibleName(/removed/i);
  expect(screen.getByText('"jinja2==3.1.5"')).toHaveAccessibleName(/added/i);
});

it("bounds a long lockfile diff and exposes an accessible full-diff toggle", () => {
  const diff = Array.from({ length: 120 }, (_, index) => `+dependency-line-${index}`).join("\n");
  render(<DiffViewer diff={diff} />);
  expect(screen.getByLabelText("Proposed dependency diff").children).toHaveLength(36);
  fireEvent.click(screen.getByRole("button", { name: "Show full diff" }));
  expect(screen.getByLabelText("Proposed dependency diff").children).toHaveLength(120);
  expect(screen.getByRole("button", { name: "Show compact diff" })).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(screen.getByRole("button", { name: "Show compact diff" }));
  expect(screen.getByLabelText("Proposed dependency diff").children).toHaveLength(36);
});
