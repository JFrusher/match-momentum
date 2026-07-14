// Hand-rolled validation — the schema is shallow enough that a JSON-schema
// dependency isn't worth it. Throws with a path-prefixed message on the first
// shape mismatch so a broken config fails loudly at module load, not mid-match.
import type {
  DerivedInputSpec,
  EventKind,
  EventTypeEntry,
  FollowUpSpec,
  ModifierTag,
  SportConfig,
} from "./types";

const EVENT_KINDS: EventKind[] = ["flat", "derived", "markerOnly"];
const MAX_EVENT_ITEMS = 9; // positional hotkeys 1-9
const MAX_GROUP_SIZE = 10; // positional hotkeys Q..P

function fail(path: string, message: string): never {
  throw new Error(`Invalid sport config at ${path}: ${message}`);
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function requireString(v: unknown, path: string): string {
  if (typeof v !== "string" || v.length === 0) fail(path, "expected a non-empty string");
  return v;
}

function requireNumber(v: unknown, path: string): number {
  if (typeof v !== "number" || !Number.isFinite(v)) fail(path, "expected a finite number");
  return v;
}

function optionalNumber(v: unknown, path: string): number | undefined {
  if (v === undefined) return undefined;
  return requireNumber(v, path);
}

function validateDerivedInput(raw: unknown, path: string): DerivedInputSpec {
  if (!isRecord(raw)) fail(path, "expected an object");
  return {
    field: requireString(raw.field, `${path}.field`),
    label: requireString(raw.label, `${path}.label`),
    min: optionalNumber(raw.min, `${path}.min`),
    max: optionalNumber(raw.max, `${path}.max`),
    step: optionalNumber(raw.step, `${path}.step`),
    default: optionalNumber(raw.default, `${path}.default`),
  };
}

function validateFollowUp(raw: unknown, path: string): FollowUpSpec {
  if (!isRecord(raw)) fail(path, "expected an object");
  if (!Array.isArray(raw.options) || raw.options.length === 0) {
    fail(`${path}.options`, "expected a non-empty array");
  }
  if (raw.options.length > MAX_EVENT_ITEMS) {
    fail(`${path}.options`, `max ${MAX_EVENT_ITEMS} options (hotkeys 1-9)`);
  }
  return {
    question: requireString(raw.question, `${path}.question`),
    options: raw.options.map((opt, i) => {
      const optPath = `${path}.options[${i}]`;
      if (!isRecord(opt)) fail(optPath, "expected an object");
      return {
        label: requireString(opt.label, `${optPath}.label`),
        logEvent: opt.logEvent === undefined ? undefined : requireString(opt.logEvent, `${optPath}.logEvent`),
        pointsDelta: optionalNumber(opt.pointsDelta, `${optPath}.pointsDelta`),
        modifier: opt.modifier === undefined ? undefined : requireString(opt.modifier, `${optPath}.modifier`),
      };
    }),
  };
}

function validateEventEntry(raw: unknown, path: string, groupIds: Set<string>): EventTypeEntry {
  if (!isRecord(raw)) fail(path, "expected an object");
  const kind = requireString(raw.kind, `${path}.kind`) as EventKind;
  if (!EVENT_KINDS.includes(kind)) fail(`${path}.kind`, `expected one of ${EVENT_KINDS.join(", ")}`);

  const modifierGroupId =
    raw.modifierGroupId === undefined
      ? undefined
      : requireString(raw.modifierGroupId, `${path}.modifierGroupId`);
  if (modifierGroupId !== undefined && !groupIds.has(modifierGroupId)) {
    fail(`${path}.modifierGroupId`, `unknown modifier group "${modifierGroupId}"`);
  }

  let derivedInputs: DerivedInputSpec[] | undefined;
  if (kind === "derived") {
    if (!Array.isArray(raw.derivedInputs) || raw.derivedInputs.length === 0) {
      fail(`${path}.derivedInputs`, 'kind "derived" requires a non-empty derivedInputs array');
    }
    derivedInputs = raw.derivedInputs.map((d, i) => validateDerivedInput(d, `${path}.derivedInputs[${i}]`));
  } else if (raw.derivedInputs !== undefined) {
    fail(`${path}.derivedInputs`, `only kind "derived" may declare derivedInputs (got "${kind}")`);
  }

  return {
    key: requireString(raw.key, `${path}.key`),
    label: requireString(raw.label, `${path}.label`),
    points: requireNumber(raw.points, `${path}.points`),
    kind,
    modifierGroupId,
    derivedInputs,
    triggersFollowUp:
      raw.triggersFollowUp === undefined
        ? undefined
        : validateFollowUp(raw.triggersFollowUp, `${path}.triggersFollowUp`),
  };
}

export function validateSportConfig(raw: unknown): SportConfig {
  if (!isRecord(raw)) fail("$", "expected an object");

  if (!isRecord(raw.teamColumn)) fail("$.teamColumn", "expected an object");
  if (typeof raw.teamColumn.includeNeutral !== "boolean") {
    fail("$.teamColumn.includeNeutral", "expected a boolean");
  }

  if (!isRecord(raw.modifierGroups)) fail("$.modifierGroups", "expected an object");
  const modifierGroups: Record<string, ModifierTag[]> = {};
  for (const [groupId, tags] of Object.entries(raw.modifierGroups)) {
    const groupPath = `$.modifierGroups.${groupId}`;
    if (!Array.isArray(tags) || tags.length === 0) fail(groupPath, "expected a non-empty array");
    if (tags.length > MAX_GROUP_SIZE) fail(groupPath, `max ${MAX_GROUP_SIZE} tags (hotkeys Q-P)`);
    modifierGroups[groupId] = tags.map((tag, i) => {
      const tagPath = `${groupPath}[${i}]`;
      if (!isRecord(tag)) fail(tagPath, "expected an object");
      return {
        id: requireString(tag.id, `${tagPath}.id`),
        label: requireString(tag.label, `${tagPath}.label`),
      };
    });
  }

  if (!isRecord(raw.eventColumn)) fail("$.eventColumn", "expected an object");
  if (!Array.isArray(raw.eventColumn.items) || raw.eventColumn.items.length === 0) {
    fail("$.eventColumn.items", "expected a non-empty array");
  }
  if (raw.eventColumn.items.length > MAX_EVENT_ITEMS) {
    fail("$.eventColumn.items", `max ${MAX_EVENT_ITEMS} items (hotkeys 1-9)`);
  }
  const groupIds = new Set(Object.keys(modifierGroups));
  const items = raw.eventColumn.items.map((item, i) =>
    validateEventEntry(item, `$.eventColumn.items[${i}]`, groupIds),
  );
  const seenKeys = new Set<string>();
  for (const item of items) {
    if (seenKeys.has(item.key)) fail("$.eventColumn.items", `duplicate event key "${item.key}"`);
    seenKeys.add(item.key);
  }

  const maxSaneMinute = requireNumber(raw.maxSaneMinute, "$.maxSaneMinute");
  if (maxSaneMinute <= 0) fail("$.maxSaneMinute", "expected a positive number");

  return {
    sportKey: requireString(raw.sportKey, "$.sportKey"),
    displayName: requireString(raw.displayName, "$.displayName"),
    teamColumn: {
      includeNeutral: raw.teamColumn.includeNeutral,
      neutralLabel: requireString(raw.teamColumn.neutralLabel, "$.teamColumn.neutralLabel"),
    },
    eventColumn: { items },
    modifierGroups,
    maxSaneMinute,
  };
}
