---
name: Dependency Sentinel
description: Local Python repository review interface
colors:
  accent: "#0f62f6"
  accent-strong: "#084cca"
  canvas: "#f7f6f2"
  surface: "#fff"
  surface-subtle: "#f4f6f8"
  graphite: "#171c22"
  graphite-2: "#252c34"
  ink: "#17202b"
  muted: "#596474"
  rule: "#d8dde3"
  rule-strong: "#b9c1cb"
  success: "#168845"
  warning: "#a96800"
  error: "#c62323"
  header-ink: "#f8fafc"
  button-ink: "#ffffff"
typography:
  body:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
rounded:
  control: "4px"
  input: "6px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
  input:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.input}"
---

# Design System: Dependency Sentinel

## Overview

A graphite repository header sits above bordered review panels. Blue identifies actions and selected work; green, amber and red distinguish execution states. Monospace labels, evidence identifiers and diffs retain the console identity.

Captured from frontend/src/styles/tokens.css, app.css and product.css on 2026-09-07. This records the existing interface; it does not assert accessibility conformance or production readiness. BUILD-BRIEF.md and LOCAL-PRODUCT.md retain workflow scope.

## Colors

The frontmatter records selected reused light-theme primitives. Dark theme overrides live in `frontend/src/styles/tokens.css` under `:root[data-theme="dark"]`; retain these variable bindings when extending components. Blue carries actions, while success, warning and error tokens identify review states. Neutral tokens separate the canvas, working surfaces, text and rules.

## Typography

Inter/system sans is used throughout the interface; SFMono-Regular/Consolas/Liberation Mono serves evidence identifiers, metadata and diffs. The repository title is 20px with -0.03em tracking. The empty-state heading uses clamp(26px, 3vw, 38px). Diff and validation content use 12px monospace with line-height 1.55.

## Layout

The repository header uses a grid with the path form, overview action and theme control. At 1100px, evidence moves below the main work area; at 760px, the header form and review workspace stack. Compact review adjustments exist at 400px. Local workspace controls and saved runs use 16px padding at 650px.

## Elevation & Depth

Depth comes mainly from graphite/surface contrast, panel borders and status fills. Keyboard focus uses a three-pixel blue shadow; the path field applies it to its surrounding input container. The status light has a small green ring.

## Shapes

Primary and header controls use the control radius. Added saved-run and workspace buttons use 6px corners. Review panels and diffs are square; execution step markers are circular.

## Components

Primary actions use blue, 44px minimum height, 18px horizontal padding and weight 700. The repository input is transparent with light text inside the graphite header; its container receives focus. Rejection actions use an outlined surface with error-colored text. Evidence count labels use compact monospace text and a 3px radius. Diff additions and removals have separate text and background colors.

The sidecar provides five source-derived HTML/CSS previews. They illustrate appearance and CSS states; they do not execute application workflows. Tokens inherit from the application root.

## Do's and Don'ts

- Do preserve the existing theme variables, typography roles and responsive stacking.
- Do retain explicit field labels and text for status states.
- Don't replace the approved visual identity or introduce a new brand metaphor.
- Don't infer product capabilities or conformance from these visual records.
