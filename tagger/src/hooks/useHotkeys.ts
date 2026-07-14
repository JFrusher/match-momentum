import { useEffect } from "react";
import { useMatchStore } from "../store/matchStore";
import { eventItems, modifierGroups } from "../data/rugbyInline";
import type { TeamRole } from "../store/types";

const TEAM_KEYS: Record<string, TeamRole> = { z: "home", x: "away", c: "neutral" };
const EVENT_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];
const MODIFIER_KEYS = ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"];

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
}

export function useHotkeys() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (isEditableTarget(e.target)) return;

      const store = useMatchStore.getState();
      const key = e.key;
      const lower = key.toLowerCase();

      // A pending reset confirmation swallows every key until resolved:
      // Enter confirms, anything else (including Escape) cancels.
      if (store.resetPending) {
        e.preventDefault();
        if (key === "Enter") store.confirmReset();
        else store.cancelReset();
        return;
      }

      // Clock controls
      if (key === " ") {
        e.preventDefault();
        if (e.shiftKey) store.armReset();
        else store.toggleClock();
        return;
      }

      // Team column — fixed keys (only ever 2-3 items)
      if (lower in TEAM_KEYS) {
        e.preventDefault();
        store.setStagedTeam(TEAM_KEYS[lower]);
        return;
      }

      // Event type column — positional, binds to config array order
      const eventIndex = EVENT_KEYS.indexOf(key);
      if (eventIndex !== -1 && eventIndex < eventItems.length) {
        e.preventDefault();
        const item = eventItems[eventIndex];
        store.stageType(item.key);
        if (!item.modifierGroupId) store.submitStaged();
        return;
      }

      // Modifier column — positional, only live once a type with a
      // modifier group is staged; always auto-submits
      const stagedItem = eventItems.find((i) => i.key === store.stagedType);
      if (stagedItem?.modifierGroupId) {
        const group = modifierGroups[stagedItem.modifierGroupId] ?? [];
        const modIndex = MODIFIER_KEYS.indexOf(lower);
        if (modIndex !== -1 && modIndex < group.length) {
          e.preventDefault();
          store.stageModifier(group[modIndex].id);
          store.submitStaged();
          return;
        }
      }

      if (key === "Enter") {
        e.preventDefault();
        store.submitStaged();
        return;
      }

      if (key === "Backspace") {
        e.preventDefault();
        store.clearLastStaged();
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
