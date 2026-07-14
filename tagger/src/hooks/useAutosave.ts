import { useEffect } from "react";
import { get as idbGet, set as idbSet } from "idb-keyval";
import { useMatchStore } from "../store/matchStore";
import type { MatchSnapshot } from "../store/types";

export const AUTOSAVE_KEY = "tagger-active-match";
const DEBOUNCE_MS = 500;

function takeSnapshot(): MatchSnapshot {
  const s = useMatchStore.getState();
  return {
    v: 1,
    sportKey: s.sportKey,
    teamNames: s.teamNames,
    events: s.events,
    scoreOverride: s.scoreOverride,
    clockMs: s.getElapsedMs(),
    savedAt: Date.now(),
  };
}

// Silent rehydrate on mount (single-match scope — nothing to prompt), then
// debounced writes on every persisted-field change. Saving only starts once
// `hydrated` flips, so an empty first render can never clobber a saved match.
export function useAutosave() {
  useEffect(() => {
    let cancelled = false;

    idbGet(AUTOSAVE_KEY)
      .then((saved: MatchSnapshot | undefined) => {
        if (cancelled) return;
        if (saved && saved.v === 1) useMatchStore.getState().hydrate(saved);
        else useMatchStore.setState({ hydrated: true });
      })
      .catch(() => {
        // IndexedDB unavailable (private mode etc.) — run memory-only.
        if (!cancelled) useMatchStore.setState({ hydrated: true });
      });

    let timer: number | undefined;
    const unsubscribe = useMatchStore.subscribe(
      (s) => [s.events, s.sportKey, s.teamNames, s.scoreOverride, s.clock] as const,
      () => {
        if (!useMatchStore.getState().hydrated) return;
        window.clearTimeout(timer);
        timer = window.setTimeout(() => {
          idbSet(AUTOSAVE_KEY, takeSnapshot()).catch(() => {});
        }, DEBOUNCE_MS);
      },
      { equalityFn: (a, b) => a.every((v, i) => Object.is(v, b[i])) },
    );

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      unsubscribe();
    };
  }, []);
}
