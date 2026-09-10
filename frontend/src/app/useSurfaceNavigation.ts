import { useEffect, useState } from "react";

type Surface = "landing" | "demo";
const fromHash = (): Surface => window.location.hash && window.location.hash !== "#main" ? "landing" : "demo";

/** Keep the overview, workspace, URL and browser history in agreement. */
export function useSurfaceNavigation() {
  const [surface, setSurface] = useState<Surface>(fromHash);
  const [navigation, setNavigation] = useState(0);

  useEffect(() => {
    const sync = () => { setSurface(fromHash()); setNavigation(n => n + 1); };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  useEffect(() => {
    if (!navigation) return;
    const frame = requestAnimationFrame(() => {
      const hash = window.location.hash.slice(1);
      if (hash && hash !== "main" && hash !== "overview") {
        document.getElementById(hash)?.scrollIntoView();
        return;
      }
      window.scrollTo({ top: 0, behavior: "instant" });
      const main = document.querySelector("main");
      if (main) { main.setAttribute("tabindex", "-1"); main.focus({ preventScroll: true }); }
    });
    return () => cancelAnimationFrame(frame);
  }, [surface, navigation]);

  function openSurface(next: Surface) {
    const hash = next === "landing" ? "#overview" : "#main";
    if (window.location.hash !== hash) window.history.pushState(null, "", hash);
    setSurface(next);
    setNavigation(n => n + 1);
  }

  return { surface, openSurface };
}
