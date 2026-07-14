import type { TaggedEvent } from "../store/types";
import { SPORT_CONFIGS, knownVocab } from "../sport-config";

export interface ExportValidation {
  errors: string[];
  warnings: string[];
  info: string[];
}

export interface ValidateInput {
  sportKey: string;
  teamNames: { home: string; away: string };
  events: TaggedEvent[];
}

// match-momentum itself has zero schema validation (plain KeyErrors on bad
// input) — this is the first validation layer in the whole pipeline.
export function validateForExport({ sportKey, teamNames, events }: ValidateInput): ExportValidation {
  const errors: string[] = [];
  const warnings: string[] = [];
  const info: string[] = [];

  const config = SPORT_CONFIGS[sportKey];
  if (!config) {
    return { errors: [`Unknown sport "${sportKey}"`], warnings, info };
  }

  const home = teamNames.home.trim();
  const away = teamNames.away.trim();
  if (!home) errors.push("Home team name is empty");
  if (!away) errors.push("Away team name is empty");
  if (home && away && home === away) errors.push(`Team names must be distinct (both are "${home}")`);

  const vocab = knownVocab(config);
  const exportable = events.filter((ev) => ev.team !== "neutral");
  const neutralCount = events.length - exportable.length;

  for (const ev of exportable) {
    const at = `event at ${ev.minute.toFixed(2)}' (${ev.type})`;
    if (ev.team !== "home" && ev.team !== "away") {
      // Defensive against stale IndexedDB state — TeamRole should prevent this.
      errors.push(`Unknown team "${String(ev.team)}" on ${at}`);
    }
    if (!Number.isFinite(ev.minute) || ev.minute < 0) {
      errors.push(`Invalid minute on ${at} — must be a finite number >= 0`);
    }
    if (!vocab.has(ev.type)) {
      errors.push(
        `"${ev.type}" is not in the ${config.displayName} vocabulary — logged under a different sport config?`,
      );
    }
  }

  if (exportable.length === 0) {
    warnings.push("No home/away events to export — the momentum chart would be empty");
  }
  const beyondSane = exportable.filter((ev) => ev.minute > config.maxSaneMinute);
  if (beyondSane.length > 0) {
    warnings.push(
      `${beyondSane.length} event${beyondSane.length === 1 ? "" : "s"} beyond minute ${config.maxSaneMinute} — clock left running?`,
    );
  }

  if (neutralCount > 0) {
    info.push(
      neutralCount === 1
        ? "1 neutral event stays in the timeline but is excluded from the export"
        : `${neutralCount} neutral events stay in the timeline but are excluded from the export`,
    );
  }

  return { errors, warnings, info };
}
