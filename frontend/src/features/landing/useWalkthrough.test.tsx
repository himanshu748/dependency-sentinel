import { useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWalkthrough } from "./useWalkthrough";
function Harness() {
  const [step, setStep] = useState(0);
  const tour = useWalkthrough(setStep);
  return <aside ref={tour.preview}><p>Step {step}</p><button onClick={tour.play}>{tour.playing ? "Pause" : "Play"}</button><button onClick={() => { tour.stop(); setStep(1); }}>Choose diff</button></aside>;
}
beforeEach(() => { vi.useFakeTimers(); vi.stubGlobal("matchMedia", () => ({ matches: false })); });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
describe("bounded walkthrough", () => {
  it("plays one sequence and stops", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Play"));
    act(() => vi.advanceTimersByTime(1400));
    expect(screen.getByText("Step 1")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(2800));
    expect(screen.getByText("Step 2")).toBeInTheDocument();
    expect(screen.getByText("Play")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(12000));
    expect(screen.getByText("Step 2")).toBeInTheDocument();
  });
  it("cancels pending steps when paused or directly selected", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Play"));
    fireEvent.click(screen.getByText("Choose diff"));
    act(() => vi.advanceTimersByTime(10000));
    expect(screen.getByText("Step 1")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Play"));
    fireEvent.click(screen.getByText("Pause"));
    act(() => vi.advanceTimersByTime(10000));
    expect(screen.getByText("Step 0")).toBeInTheDocument();
  });
  it("keeps manual steps working with reduced motion", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    render(<Harness />);
    fireEvent.click(screen.getByText("Play"));
    expect(screen.queryByText("Pause")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Choose diff"));
    expect(screen.getByText("Step 1")).toBeInTheDocument();
  });
  it("clears timers on unmount", () => {
    const { unmount } = render(<Harness />);
    fireEvent.click(screen.getByText("Play"));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
