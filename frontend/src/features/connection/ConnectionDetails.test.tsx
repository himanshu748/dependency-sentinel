import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ConnectionDetails } from "./ConnectionDetails";
vi.unmock("./health");

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });
const payload = (body: unknown) => new Response(JSON.stringify(body));
async function show(body: unknown) {
  const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(payload(body));
  render(<ConnectionDetails />);
  expect(request).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Connection details" }));
  await waitFor(() => expect(screen.getByRole("region", { name: "Runtime configuration" })).toHaveAttribute("aria-busy", "false"));
  expect(request).toHaveBeenCalledTimes(1);
  expect(request.mock.calls[0][0]).toBe("/api/health");
}
it("distinguishes scripted execution without calling a provider", async () => {
  await show({ fixture_mode: true, runtime_mode: "local", evidence_mode: "fixture" });
  expect(screen.getByText("Scripted responses · no model inference")).toBeInTheDocument();
  expect(screen.getByText(/Fixture advisory data/)).toBeInTheDocument();
});
it("shows configured AI without opening the details panel", async () => {
  const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(payload({ fixture_mode: false, runtime_mode: "openai-compatible", model_configured: true }));
  render(<ConnectionDetails />);
  expect(await screen.findByText("AI configured")).toBeInTheDocument();
  expect(screen.queryByRole("region")).not.toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(1);
  expect(request.mock.calls[0][0]).toBe("/api/health");
});
it("does not label missing model configuration as AI configured", async () => {
  await show({ fixture_mode: false, runtime_mode: "openai-compatible", model_configured: false });
  expect(screen.getByText("AI not configured")).toBeInTheDocument();
  expect(screen.queryByText("AI configured")).not.toBeInTheDocument();
});
it("cleans up its passive configuration request on unmount", () => {
  let signal: AbortSignal | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
    signal = init?.signal as AbortSignal;
    return new Promise(() => {});
  });
  const view = render(<ConnectionDetails />);
  view.unmount();
  expect(signal?.aborted).toBe(true);
});
it.each([["openai-compatible", "External model"], ["bedrock", "Bedrock"], ["agentcore", "AgentCore"]])("does not mistake configured %s for working inference", async (mode, label) => {
  await show({ fixture_mode: false, runtime_mode: mode, model_configured: true, evidence_mode: "live" });
  expect(screen.getByText(`${label} configured · inference not verified`)).toBeInTheDocument();
  expect(screen.getByText(/does not call the model/)).toBeInTheDocument();
  expect(screen.getByText("AI configured")).toBeInTheDocument();
});
it.each([null, { fixture_mode: true, runtime_mode: "bedrock" }, { runtime_mode: "unknown", debug_detail: "private-test-value" }])("fails closed on unknown configuration %j", async value => {
  await show(value);
  expect(screen.getByText("Execution mode unavailable")).toBeInTheDocument();
  expect(document.body).not.toHaveTextContent("private-test-value");
});
it("allows a failed local health check to be retried without displaying raw errors", async () => {
  const request = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("private-test-value")).mockResolvedValueOnce(payload({ runtime_mode: "local", fixture_mode: true }));
  render(<ConnectionDetails />);
  fireEvent.click(screen.getByRole("button", { name: "Connection details" }));
  fireEvent.click(await screen.findByRole("button", { name: "Retry connection check" }));
  expect(await screen.findByText("Scripted responses · no model inference")).toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(2);
  expect(document.body).not.toHaveTextContent("private-test-value");
});
it("cancels a pending check when its panel closes", async () => {
  let signal: AbortSignal | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
    signal = init?.signal as AbortSignal;
    return new Promise(() => {});
  });
  render(<ConnectionDetails />);
  const toggle = screen.getByRole("button", { name: "Connection details" });
  fireEvent.click(toggle); fireEvent.click(toggle);
  expect(signal?.aborted).toBe(true);
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("region")).not.toBeInTheDocument();
});
