import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { MatchSnapshot, TaggedEvent, TeamRole } from "./types";
import { DEFAULT_SPORT_KEY, SPORT_CONFIGS, vocabPoints } from "../sport-config";
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

// Shallow undo stack entries — each records how to reverse one mutation.
type UndoAction =
  | { kind: "add"; eventId: string }
  | { kind: "edit"; previous: TaggedEvent }
  | { kind: "delete"; event: TaggedEvent };

const UNDO_DEPTH = 10;

export interface EventPatch {
  team: TeamRole;
  type: string;
  modifier?: string;
  minute: number;
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
  scoreOverride: { home: number; away: number };
  undoStack: UndoAction[];
  hydrated: boolean;

  setSportKey: (key: string) => void;
  setTeamName: (role: "home" | "away", name: string) => void;
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

  editEvent: (id: string, patch: EventPatch) => void;
  deleteEvent: (id: string) => void;
  undo: () => void;

  adjustScoreOverride: (team: "home" | "away", delta: number) => void;

  startClock: () => void;
  pauseClock: () => void;
  toggleClock: () => void;
  armReset: () => void;
  cancelReset: () => void;
  confirmReset: () => void;
  scrubClockTo: (ms: number) => void;

  resetMatch: () => void;
  hydrate: (snapshot: MatchSnapshot) => void;

  getElapsedMs: () => number;
}

function findEntry(sportKey: string, entryKey: string | null): EventTypeEntry | undefined {
  if (!entryKey) return undefined;
  return SPORT_CONFIGS[sportKey]?.eventColumn.items.find((i) => i.key === entryKey);
}

function pointsFor(sportKey: string, typeKey: string): number {
  return vocabPoints(SPORT_CONFIGS[sportKey])[typeKey] ?? 0;
}

export const useMatchStore = create<MatchState>()(
  subscribeWithSelector((set, get) => {
    function currentMinute(): number {
      return Math.round((get().getElapsedMs() / 60000) * 100) / 100;
    }

    function makeEvent(fields: Omit<TaggedEvent, "id" | "createdAt">): TaggedEvent {
      return { id: crypto.randomUUID(), createdAt: Date.now(), ...fields };
    }

    function pushUndo(stack: UndoAction[], action: UndoAction): UndoAction[] {
      return [...stack.slice(-(UNDO_DEPTH - 1)), action];
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
      scoreOverride: { home: 0, away: 0 },
      undoStack: [],
      hydrated: false,

      // Staged type/modifier belong to the old sport's vocabulary; already-logged
      // events are kept (export validation flags any stale types).
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

      setTeamName: (role, name) =>
        set({ teamNames: { ...get().teamNames, [role]: name } }),

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
        const { sportKey, stagedTeam, stagedType, stagedModifier, events, mode, undoStack } = get();
        if (mode !== "normal" || !stagedTeam || !stagedType) return;
        const entry = findEntry(sportKey, stagedType);
        const event = makeEvent({
          minute: currentMinute(),
          team: stagedTeam,
          type: stagedType,
          modifier: stagedModifier ?? undefined,
          points: entry?.points ?? 0,
        });
        set({
          events: [...events, event],
          stagedType: null,
          stagedModifier: null,
          undoStack: pushUndo(undoStack, { kind: "add", eventId: event.id }),
        });

        // Neutral events are excluded from export, so a follow-up (conversion
        // after a neutral "try") would be meaningless — only home/away trigger it.
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
        const { followUp, events, undoStack } = get();
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
            points: option.pointsDelta ?? 0,
          });
          set({
            events: [...events, event],
            undoStack: pushUndo(undoStack, { kind: "add", eventId: event.id }),
          });
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
        const { stagedTeam, derivedDraft, events, undoStack } = get();
        // No team staged -> keep the panel open; the panel shows a hint.
        if (!derivedDraft || !stagedTeam) return;
        const event = makeEvent({
          minute: currentMinute(),
          team: stagedTeam,
          type: derivedDraft.entry.key,
          derivedInputs: { ...derivedDraft.values },
          points: derivedDraft.entry.points,
        });
        set({
          events: [...events, event],
          mode: "normal",
          derivedDraft: null,
          stagedType: null,
          stagedModifier: null,
          undoStack: pushUndo(undoStack, { kind: "add", eventId: event.id }),
        });
      },

      // Cancels the whole event — no partial form makes sense for a derived event.
      cancelDerived: () =>
        set({ mode: "normal", derivedDraft: null, stagedType: null, stagedModifier: null }),

      editEvent: (id, patch) => {
        const { sportKey, events, undoStack } = get();
        const existing = events.find((e) => e.id === id);
        if (!existing) return;
        const edited: TaggedEvent = {
          ...existing,
          team: patch.team,
          type: patch.type,
          modifier: patch.modifier,
          minute: patch.minute,
          // Type may have changed — points follow the type, not the old event.
          points: pointsFor(sportKey, patch.type),
          editedAt: Date.now(),
        };
        set({
          events: events.map((e) => (e.id === id ? edited : e)),
          undoStack: pushUndo(undoStack, { kind: "edit", previous: existing }),
        });
      },

      deleteEvent: (id) => {
        const { events, undoStack } = get();
        const existing = events.find((e) => e.id === id);
        if (!existing) return;
        set({
          events: events.filter((e) => e.id !== id),
          undoStack: pushUndo(undoStack, { kind: "delete", event: existing }),
        });
      },

      undo: () => {
        const { undoStack, events, mode } = get();
        if (mode !== "normal") return;
        const action = undoStack[undoStack.length - 1];
        if (!action) return;
        const rest = undoStack.slice(0, -1);
        if (action.kind === "add") {
          set({ events: events.filter((e) => e.id !== action.eventId), undoStack: rest });
        } else if (action.kind === "edit") {
          set({
            events: events.map((e) => (e.id === action.previous.id ? action.previous : e)),
            undoStack: rest,
          });
        } else {
          set({ events: [...events, action.event], undoStack: rest });
        }
      },

      adjustScoreOverride: (team, delta) => {
        const { scoreOverride } = get();
        set({ scoreOverride: { ...scoreOverride, [team]: scoreOverride[team] + delta } });
      },

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

      // New match: clears the match, keeps sport + team names (likely reused).
      resetMatch: () =>
        set({
          clock: { running: false, baseMs: 0, startedAt: null },
          mode: "normal",
          stagedTeam: null,
          stagedType: null,
          stagedModifier: null,
          followUp: null,
          derivedDraft: null,
          resetPending: false,
          events: [],
          scoreOverride: { home: 0, away: 0 },
          undoStack: [],
        }),

      hydrate: (snapshot) => {
        const sportKey = snapshot.sportKey in SPORT_CONFIGS ? snapshot.sportKey : DEFAULT_SPORT_KEY;
        set({
          sportKey,
          teamNames: snapshot.teamNames,
          events: snapshot.events,
          scoreOverride: snapshot.scoreOverride,
          clock: { running: false, baseMs: snapshot.clockMs, startedAt: null },
          hydrated: true,
        });
      },

      getElapsedMs: () => {
        const { clock } = get();
        return clock.baseMs + (clock.running && clock.startedAt ? Date.now() - clock.startedAt : 0);
      },
    };
  }),
);
