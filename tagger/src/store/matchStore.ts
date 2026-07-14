import { create } from "zustand";
import type { TaggedEvent, TeamRole } from "./types";

interface ClockState {
  running: boolean;
  baseMs: number;
  startedAt: number | null;
}

interface MatchState {
  clock: ClockState;
  stagedTeam: TeamRole | null;
  stagedType: string | null;
  stagedModifier: string | null;
  resetPending: boolean;
  events: TaggedEvent[];

  setStagedTeam: (team: TeamRole) => void;
  stageType: (type: string) => void;
  stageModifier: (modifier: string) => void;
  submitStaged: () => void;
  clearLastStaged: () => void;

  startClock: () => void;
  pauseClock: () => void;
  toggleClock: () => void;
  armReset: () => void;
  cancelReset: () => void;
  confirmReset: () => void;
  scrubClockTo: (ms: number) => void;

  getElapsedMs: () => number;
}

export const useMatchStore = create<MatchState>((set, get) => ({
  clock: { running: false, baseMs: 0, startedAt: null },
  stagedTeam: null,
  stagedType: null,
  stagedModifier: null,
  resetPending: false,
  events: [],

  setStagedTeam: (team) => set({ stagedTeam: team }),

  stageType: (type) => set({ stagedType: type, stagedModifier: null }),

  stageModifier: (modifier) => set({ stagedModifier: modifier }),

  submitStaged: () => {
    const { stagedTeam, stagedType, stagedModifier, events, getElapsedMs } = get();
    if (!stagedTeam || !stagedType) return;
    const minute = getElapsedMs() / 60000;
    const event: TaggedEvent = {
      id: crypto.randomUUID(),
      minute: Math.round(minute * 100) / 100,
      team: stagedTeam,
      type: stagedType,
      modifier: stagedModifier ?? undefined,
      createdAt: Date.now(),
    };
    set({ events: [...events, event], stagedType: null, stagedModifier: null });
  },

  clearLastStaged: () => {
    const { stagedModifier, stagedType } = get();
    if (stagedModifier) {
      set({ stagedModifier: null });
    } else if (stagedType) {
      set({ stagedType: null });
    }
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

  getElapsedMs: () => {
    const { clock } = get();
    return clock.baseMs + (clock.running && clock.startedAt ? Date.now() - clock.startedAt : 0);
  },
}));
