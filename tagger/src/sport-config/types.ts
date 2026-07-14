// The SportConfig schema — the shape rugby.json / football.json must satisfy.
// `sportKey` and every event `key` are contract-bound to the Python side:
// see TAGGER_PLAN.md "Ground truth" and tests/vocab-parity.test.ts.

export type EventKind = "flat" | "derived" | "markerOnly";

export interface DerivedInputSpec {
  field: string; // exact top-level key the Python translator reads (not nested)
  label: string;
  min?: number;
  max?: number;
  step?: number;
  default?: number;
}

export interface FollowUpOption {
  label: string;
  logEvent?: string; // omitted = answer logs nothing
  pointsDelta?: number;
  modifier?: string;
}

export interface FollowUpSpec {
  question: string;
  options: FollowUpOption[]; // array order = hotkey order (1-9)
}

export interface EventTypeEntry {
  key: string; // must equal a translators/<sportKey>_weights.json key, or be an allowlisted code-special type
  label: string;
  points: number;
  kind: EventKind;
  modifierGroupId?: string;
  derivedInputs?: DerivedInputSpec[];
  triggersFollowUp?: FollowUpSpec;
}

export interface ModifierTag {
  id: string;
  label: string;
}

export interface SportConfig {
  sportKey: string; // must equal a translators/__init__.py SPORTS registry key
  displayName: string;
  teamColumn: { includeNeutral: boolean; neutralLabel: string };
  eventColumn: { items: EventTypeEntry[] }; // max 9 (positional hotkeys 1-9)
  modifierGroups: Record<string, ModifierTag[]>; // each group max 10 (Q..P)
  maxSaneMinute: number;
}
