import { useEffect, useRef, useState } from "react";

/** A single, user-started sequence. Never loops or keeps running off-screen. */
export function useWalkthrough(setStep: (step: number) => void) {
  const [playing, setPlaying] = useState(false);
  const preview = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!playing) return;
    const timers = [window.setTimeout(() => setStep(1), 1400), window.setTimeout(() => setStep(2), 2800), window.setTimeout(() => setPlaying(false), 4200)];
    const stop = () => { if (document.hidden) setPlaying(false); };
    const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    const reduce = () => { if (media?.matches) setPlaying(false); };
    document.addEventListener("visibilitychange", stop);
    media?.addEventListener?.("change", reduce);
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => { if (!entry.isIntersecting) setPlaying(false); });
    if (preview.current) observer?.observe(preview.current);
    return () => {
      timers.forEach(window.clearTimeout);
      document.removeEventListener("visibilitychange", stop);
      media?.removeEventListener?.("change", reduce);
      observer?.disconnect();
    };
  }, [playing, setStep]);
  function play() {
    if (playing) { setPlaying(false); return; }
    setStep(0);
    // All steps remain directly available when motion is reduced.
    if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) setPlaying(true);
  }
  return { preview, playing, play, stop: () => setPlaying(false) };
}
