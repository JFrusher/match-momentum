import { create } from "zustand";
import type { TaggedEvent, TeamRole } from "./types";
import { DEFAULT_SPORT_KEY, SPORT_CONFIGS } from "../sport-config";
import type { EventTypeEntry, FollowUpSpec } from "../sport-config";

interface ClockState {
  running: boolean;
  baseMs: number;
  startedAt: number | null;
}

export type InteractionMode = "normal" | "followUp" | "derivedInput";

interface FollowUpState {
  spec: FollowUpSpec;
  team: TeamRole;
  primaryEventId: string;
}

interface DerivedDraft {
  entry: EventTypeEntry;
  // Values live in the store (not panel-local state) so the global hotkey
  // handler can submit with current values when focus isn't in an input.
  values: Record<string, number>;
}

interface MatchState {
  sportKey: string;
  teamNames: { home: string; away: string };
  clock: ClockState;
  mode: InteractionMode;
  stagedTeam: TeamRole | null;
  stagedType: string | null;
  stagedModifier: string | null;
  followUp: FollowUpState | null;
  derivedDraft: DerivedDraft | null;
  resetPending: boolean;
  events: TaggedEvent[];

  setSportKey: (key: string) => void;
  setStagedTeam: (team: TeamRole) => void;
  stageEventType: (entryKey: string) => void;
  stageModifier: (modifier: string) => void;
  submitStaged: () => void;
  clearLastStaged: () => void;

  resolveFollowUp: (optionIndex: number) => void;
  dismissFollowUp: () => void;

  setDerivedValue: (field: string, value: number) => void;
  submitDerived: () => void;
  cancelDerived: () => void;

  startClock: () => void;
  pauseClock: () => void;
  toggleClock: () => void;
  armReset: () => void;
  cancelReset: () => void;
  confirmReset: () => void;
  scrubClockTo: (ms: number) => void;

  getElapsedMs: () => number;
}

function findEntry(sportKey: string, entryKey: string | null): EventTypeEntry | undefined {
  if (!entryKey) return undefined;
  return SPORT_CONFIGS[sportKey]?.eventColumn.items.find((i) => i.key === entryKey);
}

export const useMatchStore = create<MatchState>((set, get) => {
  function currentMinute(): number {
    return Math.round((get().getElapsedMs() / 60000) * 100) / 100;
  }

  function makeEvent(fields: Omit<TaggedEvent, "id" | "createdAt">): TaggedEvent {
    return { id: crypto.randomUUID(), createdAt: Date.now(), ...fields };
  }

  return {
    sportKey: DEFAULT_SPORT_KEY,
    teamNames: { home: "Team A", away: "Team B" },
    clock: { running: false, baseMs: 0, startedAt: null },
    mode: "normal",
    stagedTeam: null,
    stagedType: null,
    stagedModifier: null,
    followUp: null,
    derivedDraft: null,
    resetPending: false,
    events: [],

    // Staged type/modifier belong to the old sport's vocabulary; already-logged
    // events are kept (Phase 4 export validation flags any stale types).
    setSportKey: (key) => {
      if (!(key in SPORT_CONFIGS)) return;
      set({
        sportKey: key,
        stagedType: null,
        stagedModifier: null,
        mode: "normal",
        followUp: null,
        derivedDraft: null,
      });
    },

    setStagedTeam: (team) => set({ stagedTeam: team }),

    // Single entry point for Column 2 (hotkey or click) — routes by kind:
    // derived opens the input panel; flat/markerOnly without a modifier group
    // auto-submits; with a group, stages and waits for the modifier.
    stageEventType: (entryKey) => {
      const { sportKey, mode } = get();
      if (mode !== "normal") return;
      const entry = findEntry(sportKey, entryKey);
      if (!entry) return;
      if (entry.kind === "derived") {
        const values: Record<string, number> = {};
        for (const input of entry.derivedInputs ?? []) values[input.field] = input.default ?? 0;
        set({ stagedType: entry.key, stagedModifier: null, mode: "derivedInput", derivedDraft: { entry, values } });
        return;
      }
      set({ stagedType: entry.key, stagedModifier: null });
      if (!entry.modifierGroupId) get().submitStaged();
    },

    stageModifier: (modifier) => set({ stagedModifier: modifier }),

    submitStaged: () => {
      const { sportKey, stagedTeam, stagedType, stagedModifier, events, mode } = get();
      if (mode !== "normal" || !stagedTeam || !stagedType) return;
      const event = makeEvent({
        minute: currentMinute(),
        team: stagedTeam,
        type: stagedType,
        modifier: stagedModifier ?? undefined,
      });
      set({ events: [...events, event], stagedType: null, stagedModifier: null });

      // Neutral events are excluded from export, so a follow-up (conversion
      // after a neutral "try") would be meaningless — only home/away trigger it.
      const entry = findEntry(sportKey, stagedType);
      if (entry?.triggersFollowUp && stagedTeam !== "neutral") {
        set({
          mode: "followUp",
          followUp: { spec: entry.triggersFollowUp, team: stagedTeam, primaryEventId: event.id },
        });
      }
    },

    clearLastStaged: () => {
      const { stagedModifier, stagedType } = get();
      if (stagedModifier) {
        set({ stagedModifier: null });
      } else if (stagedType) {
        set({ stagedType: null });
      }
    },

    resolveFollowUp: (optionIndex) => {
      const { followUp, events } = get();
      if (!followUp) return;
      const option = followUp.spec.options[optionIndex];
      if (!option) return;
      if (option.logEvent) {
        const event = makeEvent({
          minute: currentMinute(),
          team: followUp.team,
          type: option.logEvent,
          modifier: option.modifier,
          followUpOf: followUp.primaryEventId,
        });
        set({ events: [...events, event] });
      }
      set({ mode: "normal", followUp: null });
    },

    // Escape path — the primary event (already logged) is unaffected.
    dismissFollowUp: () => set({ mode: "normal", followUp: null }),

    setDerivedValue: (field, value) => {
      const { derivedDraft } = get();
      if (!derivedDraft) return;
      set({ derivedDraft: { ...derivedDraft, values: { ...derivedDraft.values, [field]: value } } });
    },

    submitDerived: () => {
      const { stagedTeam, derivedDraft, events } = get();
      // No team staged -> keep the panel open; the panel shows a hint.
      if (!derivedDraft || !stagedTeam) return;
      const event = makeEvent({
        minute: currentMinute(),
        team: stagedTeam,
        type: derivedDraft.entry.key,
        derivedInputs: { ...derivedDraft.values },
      });
      set({
        events: [...events, event],
        mode: "normal",
        derivedDraft: null,
        stagedType: null,
        stagedModifier: null,
      });
    },

    // Cancels the whole event — no partial form makes sense for a derived event.
    cancelDerived: () =>
      set({ mode: "normal", derivedDraft: null, stagedType: null, stagedModifier: null }),

    startClock: () => {
      const { clock } = get();
      if (clock.running) return;
      set({ clock: { ...clock, running: true, startedAt: Date.now() } });
    },

    pauseClock: () => {
      const { clock } = get();
      if (!clock.running) return;
      const elapsed = clock.baseMs + (clock.startedAt ? Date.now() - clock.startedAt : 0);
      set({ clock: { running: false, baseMs: elapsed, startedAt: null } });
    },

    toggleClock: () => {
      const { clock } = get();
      if (clock.running) get().pauseClock();
      else get().startClock();
    },

    armReset: () => set({ resetPending: true }),
    cancelReset: () => set({ resetPending: false }),
    confirmReset: () =>
      set({ clock: { running: false, baseMs: 0, startedAt: null }, resetPending: false }),

    scrubClockTo: (ms) => {
      const { clock } = get();
      const baseMs = Math.max(0, ms);
      set({ clock: { ...clock, baseMs, startedAt: clock.running ? Date.now() : null } });
    },

    getElapsedMs: () => {
      const { clock } = get();
      return clock.baseMs + (clock.running && clock.startedAt ? Date.now() - clock.startedAt : 0);
    },
  };
});
