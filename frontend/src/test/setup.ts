import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// Workflow tests isolate passive health reads from their ordered mutation mocks.
// ConnectionDetails.test.tsx restores the real reader and tests the HTTP boundary.
vi.mock("../features/connection/health", () => ({
  readRuntimeConfiguration: vi.fn(async () => ({ fixture_mode: true, runtime_mode: "local" })),
}));

// jsdom has no viewport scrolling; rendered scrolling is covered in browser QA.
beforeEach(() => vi.stubGlobal("scrollTo", vi.fn()));

afterEach(() => cleanup());
