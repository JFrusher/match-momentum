// Guards the contract between the bundled sport configs and match-momentum's
// static weight tables (translators/<sportKey>_weights.json). Runs as
// `npm run check:vocab` and as a prebuild step.
import { describe, expect, it } from "vitest";
import { SPORT_CONFIGS } from "../src/sport-config";
import rugbyWeightsRaw from "../../translators/rugby_weights.json";
import footballWeightsRaw from "../../translators/football_weights.json";

// Static imports keyed by sportKey — asserts each config's sportKey actually
// matches a weights table on the Python side.
const WEIGHTS: Record<string, Record<string, number>> = {
  rugby: rugbyWeightsRaw,
  football: footballWeightsRaw,
};

// kind: "derived" | "markerOnly" entries are handled specially in translator
// code (phase_sequence derives its weight, sin_bin is forced to 0.0) — they
// must NOT appear in the weights table.
const CODE_SPECIAL_ALLOWLIST: Record<string, string[]> = {
  rugby: ["phase_sequence", "sin_bin"],
  football: [],
};

for (const [registryKey, config] of Object.entries(SPORT_CONFIGS)) {
  describe(`${registryKey} vocab parity`, () => {
    const weights = WEIGHTS[config.sportKey] ?? {};
    const weightKeys = Object.keys(weights).filter((k) => k !== "_default");
    const allowlist = CODE_SPECIAL_ALLOWLIST[config.sportKey] ?? [];

    const flatKeys = config.eventColumn.items
      .filter((i) => i.kind === "flat")
      .map((i) => i.key);
    const followUpEvents = config.eventColumn.items.flatMap(
      (i) =>
        i.triggersFollowUp?.options.flatMap((o) => (o.logEvent ? [o.logEvent] : [])) ?? [],
    );
    const specialKeys = config.eventColumn.items
      .filter((i) => i.kind !== "flat")
      .map((i) => i.key);

    it("sportKey resolves to a weights table", () => {
      expect(WEIGHTS[config.sportKey], `no weights table for sportKey "${config.sportKey}"`).toBeDefined();
    });

    it("every flat key and follow-up logEvent exists in the weights table", () => {
      for (const key of [...flatKeys, ...followUpEvents]) {
        expect(weightKeys, `"${key}" missing from ${config.sportKey}_weights.json`).toContain(key);
      }
    });

    it("every weights key is reachable from some config entry", () => {
      const reachable = new Set([...flatKeys, ...followUpEvents]);
      for (const key of weightKeys) {
        expect(reachable.has(key), `weights key "${key}" unreachable from ${registryKey} config`).toBe(true);
      }
    });

    it("derived/markerOnly keys are allowlisted and absent from the weights table", () => {
      for (const key of specialKeys) {
        expect(allowlist, `"${key}" (non-flat) missing from CODE_SPECIAL_ALLOWLIST`).toContain(key);
        expect(weightKeys, `"${key}" is code-special but appears in the weights table`).not.toContain(key);
      }
      for (const key of allowlist) {
        expect(specialKeys, `allowlisted "${key}" has no non-flat config entry`).toContain(key);
      }
    });
  });
}
