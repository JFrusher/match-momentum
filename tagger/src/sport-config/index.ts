// Bundled sport configs, validated once at module load. Runtime config upload
// is out of scope — add a sport by adding a JSON file here and registering it.
import rugbyRaw from "./rugby.json";
import footballRaw from "./football.json";
import { validateSportConfig } from "./validate";
import type { SportConfig } from "./types";

export const SPORT_CONFIGS: Record<string, SportConfig> = {
  rugby: validateSportConfig(rugbyRaw),
  football: validateSportConfig(footballRaw),
};

export const DEFAULT_SPORT_KEY = "rugby";

export type { SportConfig, EventTypeEntry, FollowUpSpec, FollowUpOption, DerivedInputSpec, ModifierTag } from "./types";

// Timeline label for any vocabulary member — including types with no Column-2
// button (e.g. conversion/conversion_missed, reachable only via a follow-up),
// which fall back to a humanized key.
export function eventLabel(config: SportConfig, typeKey: string): string {
  const entry = config.eventColumn.items.find((i) => i.key === typeKey);
  if (entry) return entry.label;
  const humanized = typeKey.replace(/_/g, " ");
  return humanized.charAt(0).toUpperCase() + humanized.slice(1);
}
