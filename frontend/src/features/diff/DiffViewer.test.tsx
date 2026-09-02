import { render, screen } from "@testing-library/react";
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
