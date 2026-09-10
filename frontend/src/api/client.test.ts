import { afterEach, expect, it, vi } from "vitest";
import { createRun, downloadReview } from "./client";

afterEach(() => vi.unstubAllGlobals());

it("retains a supplied idempotency key across retry attempts", async () => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}")));
  vi.stubGlobal("fetch", fetcher);
  await createRun("/trusted/project", "stable-key");
  await createRun("/trusted/project", "stable-key");
  expect(fetcher.mock.calls.map(call => call[1].headers["Idempotency-Key"])).toEqual(["stable-key", "stable-key"]);
});

it("turns non-JSON gateway failure into actionable recovery", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("upstream unavailable", { status: 502 })));
  await expect(createRun("/trusted/project")).rejects.toThrow("unreadable response (502)");
});

it("requires the authoritative export response and preserves its failure message", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: { code: "review_not_exportable", message: "Saved review has changed. Start a new review." },
  }), { status: 409, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetcher);
  await expect(downloadReview("run/encoded", "receipt")).rejects.toThrow("Start a new review");
  expect(fetcher).toHaveBeenCalledWith("/api/runs/run%2Fencoded/exports/receipt", { cache: "no-store" });
});

it("does not turn a gateway HTML page into a patch download", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>gateway</html>", {
    headers: { "Content-Type": "text/html" },
  })));
  await expect(downloadReview("run-test", "patch")).rejects.toThrow("unexpected download");
});

it("explains how to retry an offline export without changing the review", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));
  await expect(downloadReview("run-test", "patch")).rejects.toThrow("Reconnect and retry the download");
});
