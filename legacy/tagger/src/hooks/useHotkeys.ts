import { useEffect } from "react";
import { useMatchStore } from "../store/matchStore";
import { SPORT_CONFIGS } from "../sport-config";
import type { TeamRole } from "../store/types";

const TEAM_KEYS: Record<string, TeamRole> = { z: "home", x: "away", c: "neutral" };
const EVENT_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];
const MODIFIER_KEYS = ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"];

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

export function useHotkeys() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (isEditableTarget(e.target)) return;

      const store = useMatchStore.getState();
      const config = SPORT_CONFIGS[store.sportKey];
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

      // Follow-up modal: 1-9 pick an option, Escape dismisses without logging
      // the secondary event. Everything else is swallowed — it's a modal.
      if (store.mode === "followUp") {
        e.preventDefault();
        if (key === "Escape") {
          store.dismissFollowUp();
          return;
        }
        const optIndex = EVENT_KEYS.indexOf(key);
        if (optIndex !== -1 && optIndex < (store.followUp?.spec.options.length ?? 0)) {
          store.resolveFollowUp(optIndex);
        }
        return;
      }

      // Derived-input panel: its inputs handle their own keys (the editable
      // guard above bails). This branch only fires when focus is elsewhere —
      // Enter submits current values, Escape cancels the whole event.
      if (store.mode === "derivedInput") {
        if (key === "Enter") {
          e.preventDefault();
          store.submitDerived();
        } else if (key === "Escape") {
          e.preventDefault();
          store.cancelDerived();
        }
        return;
      }

      // Undo — checked before the single-key zones so Ctrl+Z never stages a team.
      if ((e.ctrlKey || e.metaKey) && lower === "z") {
        e.preventDefault();
        store.undo();
        return;
      }

      // Any other chord is a browser shortcut (Ctrl+R, Ctrl+C...) — pass through.
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      // Score override — [ / Shift+[ home −/+, ] / Shift+] away −/+ (a visible
      // delta on top of the computed points total, never overwriting it).
      if (key === "[" || key === "{") {
        e.preventDefault();
        store.adjustScoreOverride("home", key === "[" ? -1 : 1);
        return;
      }
      if (key === "]" || key === "}") {
        e.preventDefault();
        store.adjustScoreOverride("away", key === "]" ? -1 : 1);
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
        const team = TEAM_KEYS[lower];
        if (team === "neutral" && !config.teamColumn.includeNeutral) return;
        e.preventDefault();
        store.setStagedTeam(team);
        return;
      }

      // Event type column — positional, binds to config array order.
      // stageEventType routes by kind (derived opens the panel, no-modifier
      // entries auto-submit, modifier entries stage and wait).
      const eventIndex = EVENT_KEYS.indexOf(key);
      if (eventIndex !== -1 && eventIndex < config.eventColumn.items.length) {
        e.preventDefault();
        store.stageEventType(config.eventColumn.items[eventIndex].key);
        return;
      }

      // Modifier column — positional, only live once a type with a
      // modifier group is staged; always auto-submits
      const stagedItem = config.eventColumn.items.find((i) => i.key === store.stagedType);
      if (stagedItem?.modifierGroupId) {
        const group = config.modifierGroups[stagedItem.modifierGroupId] ?? [];
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
