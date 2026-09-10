import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSurfaceNavigation } from "./useSurfaceNavigation";

function Harness() {
  const { surface, openSurface } = useSurfaceNavigation();
  return <><button onClick={() => openSurface("landing")}>Overview</button><button onClick={() => openSurface("demo")}>Workspace</button><main>{surface}</main></>;
}
beforeEach(() => {
  window.history.replaceState(null, "", "#overview");
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => { callback(0); return 1; });
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  vi.stubGlobal("scrollTo", vi.fn());
});
afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState(null, "", "/"); });
describe("surface navigation", () => {
  it("changes screen and URL, then focuses the destination", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Workspace"));
    expect(window.location.hash).toBe("#main");
    expect(screen.getByRole("main")).toHaveTextContent("demo");
    expect(screen.getByRole("main")).toHaveFocus();
    fireEvent.click(screen.getByText("Overview"));
    expect(window.location.hash).toBe("#overview");
    expect(screen.getByRole("main")).toHaveTextContent("landing");
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "instant" });
  });
  it("does not create duplicate history entries on repeated home clicks", () => {
    const push = vi.spyOn(window.history, "pushState");
    render(<Harness />);
    fireEvent.click(screen.getByText("Overview"));
    expect(push).not.toHaveBeenCalled();
    push.mockRestore();
  });
  it("honors browser back/forward navigation", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Workspace"));
    act(() => { window.history.replaceState(null, "", "#overview"); window.dispatchEvent(new PopStateEvent("popstate")); });
    expect(screen.getByRole("main")).toHaveTextContent("landing");
  });
  it("opens landing section deep links on the landing surface", () => {
    window.history.replaceState(null, "", "#how-it-works");
    render(<Harness />);
    expect(screen.getByRole("main")).toHaveTextContent("landing");
  });
});
