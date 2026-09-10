import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("retries a failed history request without creating a record", async () => {
  window.location.hash = "";
  const fetcher = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response("{}", { status: 503 }))
    .mockResolvedValueOnce(new Response("[]", { status: 200 }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Saved runs" }));
  fireEvent.click(await screen.findByRole("button", { name: "Retry request" }));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(fetcher.mock.calls.map(call => [call[0], call[1]?.method || "GET"]))
    .toEqual([["/api/runs", "GET"], ["/api/runs", "GET"]]);
  await waitFor(() => expect(screen.queryByRole("button", { name: "Retry request" })).not.toBeInTheDocument());
});

it("recovers lost event output without submitting the repository twice", async () => {
  window.location.hash = "";
  const envelope = { run: { id: "recover-run", task_type: "dependency_upgrade", input_summary: "/trusted/project", status: "failed", created_at: "2026-09-08T00:00:00Z", updated_at: "2026-09-08T00:00:00Z" }, candidate: null, approval_id: null };
  const fetcher = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(envelope), { status: 201 }))
    .mockRejectedValueOnce(new Error("Lost connection"))
    .mockResolvedValueOnce(new Response("[]", { status: 200 }));
  render(<App />);
  fireEvent.change(screen.getByLabelText("Repository path"), { target: { value: "/trusted/project" } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Scan repository" }));
  fireEvent.click(await screen.findByRole("button", { name: "Try scan again" }));
  await screen.findByText("Run did not produce a patch");
  expect(fetcher.mock.calls.filter(call => call[1]?.method === "POST")).toHaveLength(1);
  expect(fetcher.mock.calls.filter(call => String(call[0]).endsWith("/events"))).toHaveLength(2);
});

it("does not invent a branch before repository inspection", () => {
  window.location.hash = "";
  render(<App />);
  expect(screen.getByText("not inspected")).toBeInTheDocument();
  expect(screen.queryByText("main")).not.toBeInTheDocument();
});
