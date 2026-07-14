// Phase 1 skeleton: sport rules hardcoded inline to prove the tagging loop
// works end-to-end before the config-driven JSON layer (sport-config/) lands
// in Phase 2. Do not extend this file — extend sport-config/rugby.json instead.
import type { EventTypeItem, ModifierTag } from "../store/types";

export const teamNames = { home: "Team A", away: "Team B" };

// Column 2 — positional, hotkeys 1-9 in this order.
export const eventItems: EventTypeItem[] = [
  { key: "pass", label: "Pass", modifierGroupId: "pass_outcome" },
  { key: "kick", label: "Kick", modifierGroupId: "kick_outcome" },
  { key: "tackle", label: "Tackle", modifierGroupId: "tackle_outcome" },
  { key: "turnover_won", label: "Turnover Won" },
  { key: "penalty_kick", label: "Penalty Kick" },
  { key: "drop_goal", label: "Drop Goal" },
  { key: "try", label: "Try" },
  { key: "linebreak", label: "Linebreak" },
  { key: "sin_bin", label: "Sin Bin", modifierGroupId: "card_colour" },
];

// Column 3 — positional, hotkeys Q W E R T Y U I O P in this order per group.
export const modifierGroups: Record<string, ModifierTag[]> = {
  pass_outcome: [
    { id: "successful", label: "Successful" },
    { id: "missed", label: "Missed" },
    { id: "intercepted", label: "Intercepted" },
  ],
  kick_outcome: [
    { id: "successful", label: "Successful" },
    { id: "missed", label: "Missed" },
    { id: "charged_down", label: "Charged Down" },
  ],
  tackle_outcome: [
    { id: "made", label: "Made" },
    { id: "missed", label: "Missed" },
    { id: "dominant", label: "Dominant" },
  ],
  card_colour: [
    { id: "yellow", label: "Yellow" },
    { id: "red", label: "Red" },
  ],
};
