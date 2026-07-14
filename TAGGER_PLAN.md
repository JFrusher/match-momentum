# Tagger — Build Plan & Progress

Real-time sport event logging web app in [tagger/](tagger/), exporting JSON compatible with this repo's `momentum.py` pipeline. Full architecture background, rationale, and locked decisions are below; progress/status is at the top so you can pick this up cold.

**Where this stands:** Phases 1 and 2 are done and verified on a Node machine (`npm run build` green: vocab-parity tests → `tsc -b` → `vite build`; all hotkey flows driven end-to-end in a headless browser, including the follow-up modal and derived-input panel).

---

## Status

- [x] **Phase 1 — Static skeleton** (verified: type-checks, builds, hotkey loop driven in-browser)
- [x] **Phase 2 — Config-driven sport rules + follow-up/derived flows**
- [ ] **Phase 3 — Timeline editing + persistence**
- [ ] **Phase 4 — Export + validation**

### What's actually in the repo right now (post-Phase 2)

```
tagger/
  package.json  tsconfig.json  tsconfig.node.json  vite.config.ts  index.html  README.md
  src/
    main.tsx  App.tsx  App.css
    store/
      types.ts        # TeamRole, TaggedEvent (+derivedInputs?, followUpOf?)
      matchStore.ts    # Zustand store: staging state machine + clock + mode (normal|followUp|derivedInput) + sportKey + teamNames
    sport-config/
      types.ts         # SportConfig schema (EventKind, DerivedInputSpec, FollowUpSpec, ...)
      validate.ts      # hand-rolled validateSportConfig, throws path-prefixed errors at load
      rugby.json  football.json
      index.ts         # SPORT_CONFIGS (validated at module load), eventLabel() helper
    hooks/
      useHotkeys.ts    # global keydown listener, all hotkey zones, mode routing
      useSportConfig.ts # active config from store.sportKey
      useClock.ts      # ticking display hook, isolated re-renders
    components/
      TeamColumn.tsx  EventColumn.tsx  ModifierColumn.tsx  SubmitBar.tsx
      ClockController.tsx  SportSelect.tsx
      FollowUpModal.tsx      # Try -> Conversion? — hotkeys 1-9 pick, Escape skips
      DerivedInputPanel.tsx  # phase_sequence numeric fields — Enter submits, Escape cancels whole event
      TimelineLog/TimelineLog.tsx   # read-only, newest-first (createdAt tiebreak within a rounded minute)
    utils/
      time.ts          # formatClock(ms) -> "mm:ss"
  tests/
    vocab-parity.test.ts  # config <-> translators/<sport>_weights.json contract; runs as prebuild + npm run check:vocab
```

Phase 1 behavior (all verified in-browser):
- Sticky team (Z/X/C), positional event keys (1-9), positional modifier keys (Q W E R T Y U I O P), auto-submit rules exactly as designed (see "Interaction state machine" below).
- `Enter` submits/skips modifier, `Backspace` clears last staged field (modifier then type, never team).
- `Space` start/pause, `Shift+Space` arms a reset that `Enter` confirms and any other key cancels.
- Clock stored as `{running, baseMs, startedAt}` in Zustand; `getElapsedMs()` computed on demand so only `ClockController` re-renders every tick (via `useClock`'s own 250ms interval), not the whole tree.
- Mouse-operable scrub slider on the clock (disabled while running).
- Global hotkey listener bails out if focus is in an input/textarea/select/contenteditable.

Phase 2 behavior (all verified in-browser):
- Both sports load from validated JSON configs; header dropdown switches (switching clears staged type/modifier, keeps logged events).
- Try auto-submits then opens the follow-up modal (1/2 answer, Escape skips — primary event unaffected). Neutral-team events never trigger a follow-up.
- Phase Sequence opens the derived panel (defaults prefilled, first field autofocused, Enter submits, Escape cancels the whole event; no staged team → warning + Enter no-ops).
- Sin Bin behaves as a normal modifier-group event (`markerOnly` needs no special UI).

Deviations from the plan as written (all deliberate):
- `translators/rugby_weights.json` gained `"conversion_missed": 0.0` — the plan's follow-up logs it, but the weights table lacked it, so the translator's `_default` would have given a **missed** conversion 0.4 momentum (more than a made conversion's 0.3). 0.0 = no momentum credit; revisit if a miss should count as attacking pressure.
- `rugby.json` includes a flat `linebreak` entry the plan's example omitted — the weights table has it, and the parity test's reachability rule (correctly) demanded it.
- `TaggedEvent` gained `derivedInputs?`/`followUpOf?` in Phase 2, not Phase 4 — the modal flows have to record that data when they log; `points`/`editedAt` still deferred as planned.
- Timeline sorts newest-first with a `createdAt` tiebreak — rapid events share a rounded minute and ties otherwise displayed oldest-first (found by driving the app).

Not yet done, deliberately deferred:
- No inline timeline editing/delete, no undo stack.
- No autosave/persistence — refreshing the browser loses all state.
- No export/download, no export validation.
- No score tracking UI (config `points` values are recorded but unused until Phase 3's ScoreboardPanel).

---

## Ground truth: match-momentum's actual input contract

(Verified by reading the code — not assumed. Re-check if `translators/` changes before relying on this.)

- `CustomJSONSource.parse()` requires top-level `teams: {home, away}` (exact strings, no ID system, no third "neutral" slot) and `events: [...]`, each needing `minute` (float, continuous match-clock, sort key). Optional: `colors`, `title`, `footer`. Unknown fields anywhere are silently ignored.
- Per-event, each translator (`translators/football.py`, `translators/rugby.py`) requires `type` (string) and `team` (must exactly equal `teams.home`/`teams.away`), and looks up `weight` from a static table (`translators/{football,rugby}_weights.json`) unless the event carries an explicit `weight` override.
- `translators/__init__.py`'s `SPORTS` registry keys are `"football"` and `"rugby"` (rugby's class attribute `name="rugby_union"` is a red herring — the registry/CLI/filename key is `"rugby"`).
- Rugby has two vocabulary members **not** in `rugby_weights.json`, handled in code: `phase_sequence` (weight derived from flat top-level fields `metres_gained`, `end_metres_from_line`, `linebreaks` — **exact key names, not nested**) and `sin_bin` (forced weight `0.0`, card/marker-only).
- `weight` is "momentum threat energy" — unrelated to real match score. match-momentum has no concept of actual points; the Tagger owns scoring entirely itself.
- Zero schema validation exists in match-momentum (plain `KeyError`s on bad input) — the Tagger is effectively the first validation layer in this whole pipeline.

## Locked Decisions

| Area | Decision |
|---|---|
| Packaging | Standalone app in `tagger/` folder, same repo, no Python coupling |
| Stack | React + TypeScript + Vite |
| Hotkeys | Positional for Columns 2/3 (bind by config array order); fixed keys for Column 1 (only ever 2-3 items) |
| Video | No embedded/synced player — independent clock only |
| `weight` field | Omitted from export; match-momentum's static tables resolve it (no second source of truth) |
| Follow-ups (Try→Conversion) | Modal overlay, still fully hotkey-driven |
| Clock | Single continuous clock; manual pause/adjust at halftime; manual scrub slider |
| Undo/edit | Full inline timeline editing (click any logged event to edit/delete) + quick undo-last |
| Persistence | Autosave to browser storage (IndexedDB), single active match per session, explicit Export action |
| Neutral events | Stay in the on-screen timeline/log; **excluded** from the momentum JSON export (schema has no 3rd team slot) |
| Sport config format | **Plain JSON files** (`rugby.json`, `football.json`), validated against a TS type at load time |
| Modifiers (Column 3) | Single-select per event |

## Interaction state machine (makes "<1s, no mouse" real)

- `stagedTeam` is **sticky** — persists across submits.
- `stagedType`/`stagedModifier` reset after every submit.
- Team keys never submit, only stage.
- Event type key: if `kind: "derived"` → opens `DerivedInputPanel` (gates submission, Phase 2). If no modifier group → **auto-submits immediately** with the sticky team. If it has a modifier group → stages, waits for modifier.
- Modifier key → always auto-submits.
- `Enter` = manual submit/skip modifier. `Backspace` = clear last staged field (modifier, then type — never team).

## Hotkey zones

| Zone | Keys | Binds to |
|---|---|---|
| Team | `Z X C` | Fixed — Team A / Team B / Neutral |
| Event type | `1`–`9` | Positional, config array order (max 9) |
| Modifier | `Q W E R T Y U I O P` | Positional, active modifier group (max 10) |
| Submit/clear | `Enter` / `Backspace` | Manual submit / clear staged |
| Undo (Phase 3) | `Ctrl+Z` | Pop shallow undo stack (~10 entries) |
| Clock | `Space` start/pause, `Shift+Space` reset (Enter/any-key confirm) | |
| Score override (Phase 3) | `[`/`Shift+[` Team A −/+, `]`/`Shift+]` Team B −/+ | Adjusts a visible delta on top of computed points total |

Guard rule (already implemented): if `document.activeElement` is an editable field, the global listener does nothing.

---

## Phase 2 — Config-driven sport rules + follow-up/derived flows

Goal: replace `data/rugbyInline.ts` with the real JSON config layer, and add the two modal interaction flows.

1. **`sport-config/types.ts`** — the `SportConfig` schema:
   ```ts
   type EventKind = "flat" | "derived" | "markerOnly";

   interface DerivedInputSpec { field: string; label: string; min?: number; max?: number; step?: number; default?: number; }
   interface FollowUpOption { label: string; logEvent?: string; pointsDelta?: number; modifier?: string; }
   interface FollowUpSpec { question: string; options: FollowUpOption[]; }  // array — order = hotkey order

   interface EventTypeEntry {
     key: string;    // must equal a translators/<sportKey>_weights.json key, or be an allowlisted code-special type
     label: string; points: number; kind: EventKind;
     modifierGroupId?: string; derivedInputs?: DerivedInputSpec[]; triggersFollowUp?: FollowUpSpec;
   }

   interface SportConfig {
     sportKey: string;   // must equal translators/__init__.py SPORTS registry key ("football" | "rugby")
     displayName: string;
     teamColumn: { includeNeutral: boolean; neutralLabel: string };
     eventColumn: { items: EventTypeEntry[] };      // max 9
     modifierGroups: Record<string, {id: string; label: string}[]>;  // each group max 10
     maxSaneMinute: number;
   }
   ```
2. **`sport-config/rugby.json`** and **`sport-config/football.json`** — plain data files. Rugby example (all three `kind`s):
   ```json
   {
     "sportKey": "rugby",
     "displayName": "Rugby Union",
     "teamColumn": { "includeNeutral": true, "neutralLabel": "Neutral / Stoppage" },
     "eventColumn": { "items": [
       { "key": "try", "label": "Try", "points": 5, "kind": "flat",
         "triggersFollowUp": { "question": "Was the conversion successful?",
           "options": [
             { "label": "Yes", "logEvent": "conversion", "pointsDelta": 2 },
             { "label": "No", "logEvent": "conversion_missed", "pointsDelta": 0 }
           ] } },
       { "key": "penalty_kick", "label": "Penalty Kick", "points": 3, "kind": "flat" },
       { "key": "drop_goal", "label": "Drop Goal", "points": 3, "kind": "flat" },
       { "key": "turnover_won", "label": "Turnover Won", "points": 0, "kind": "flat" },
       { "key": "phase_sequence", "label": "Phase Sequence", "points": 0, "kind": "derived",
         "derivedInputs": [
           { "field": "metres_gained", "label": "Metres gained", "default": 0, "min": 0, "max": 100, "step": 5 },
           { "field": "end_metres_from_line", "label": "End metres from line", "default": 50, "min": 0, "max": 100, "step": 5 },
           { "field": "linebreaks", "label": "Linebreaks", "default": 0, "min": 0, "max": 5, "step": 1 }
         ] },
       { "key": "sin_bin", "label": "Sin Bin", "points": 0, "kind": "markerOnly", "modifierGroupId": "card_colour" }
     ] },
     "modifierGroups": { "card_colour": [{ "id": "yellow", "label": "Yellow" }, { "id": "red", "label": "Red" }] },
     "maxSaneMinute": 130
   }
   ```
   Note: `conversion`/`conversion_missed` have no dedicated Column-2 button — only reachable via the `try` follow-up — but are still real vocabulary members.
3. **`sport-config/validate.ts`** — hand-rolled `validateSportConfig(raw: unknown): SportConfig`, throws clear errors on shape mismatches. No new dependency (schema is shallow).
4. **`sport-config/index.ts`** — imports the JSON (Vite supports native JSON imports), validates once at load, exposes typed configs.
5. **`useSportConfig` hook** — v1: a small dropdown between the two bundled configs. Replace all `data/rugbyInline.ts` imports across components/hooks with this.
6. **`FollowUpModal.tsx`** — question + `options[]` rendered in array order = hotkey order (`1`-`9` rebind to modal options via a `mode` field in the store: `normal | followUp | derivedInput`). `Escape` dismisses without logging the secondary event (primary event, already logged, unaffected).
7. **`DerivedInputPanel.tsx`** — numeric fields for `kind: "derived"` entries, pre-filled with `default`. `Enter` submits current/default values immediately. `Escape` cancels the *whole* event (no partial form makes sense for a derived event).
8. **`markerOnly`** entries (`sin_bin`) — same as `flat` in the UI (pick from Column 2, optionally a modifier), just doesn't map to a `_SCORE_TYPES` marker on the Python side. No special UI handling needed beyond respecting `points: 0`.
9. **Vocabulary-parity test** — `tests/vocab-parity.test.ts`, reads `translators/<sportKey>_weights.json` directly via `sportConfig.sportKey` and asserts:
   - Every `kind: "flat"` entry's `key` (and every `triggersFollowUp.options[].logEvent`) exists in the weights JSON.
   - Every weights-JSON key (excluding `_default`) is reachable from *some* config entry.
   - `kind: "derived" | "markerOnly"` entries are in an explicit allowlist in the test file (`{ rugby: ["phase_sequence", "sin_bin"] }`) and must **not** appear in the weights JSON.
   - Wire as `npm run check:vocab`, run as a `prebuild` step.

## Phase 3 — Timeline editing + persistence

1. `TimelineRow.tsx` — click-to-expand inline edit (team/type/modifier/minute) and delete, in `TimelineLog`.
2. Shallow undo stack (~10 entries: `{type: add|edit|delete, event, previous?}`) + `Ctrl+Z` binding in `useHotkeys`.
3. `useAutosave` hook — `idb-keyval` dependency (already in `package.json`), debounced (~500ms) writes via `subscribeWithSelector`, silent rehydrate on mount (single-match scope, nothing to prompt).
4. `NewMatchDialog.tsx` — mouse-only confirm-to-clear.
5. `ScoreboardPanel.tsx` — `Σ(points of team's events) + manualOverrideDelta`; `[`/`]` (and Shift variants) adjust the delta without overwriting the computed total.

## Phase 4 — Export + validation

1. **Internal `TaggedEvent`** (already defined in `store/types.ts`) gains: `points`, `derivedInputs?: Record<string, number>`, `followUpOf?: string`, `editedAt?`.
2. **`export/toMomentumJson.ts`** — filters `team === "neutral"` out entirely; resolves `"home"/"away"` roles to actual configured team name strings; flattens `derivedInputs` to top-level keys with the **exact** names `rugby.py` reads (`metres_gained`, `end_metres_from_line`, `linebreaks` — not nested); omits `weight` entirely; keeps `points`/`modifier` as harmless extra per-event fields; sorts by `minute` ascending before serializing.
3. **`export/validate.ts`** — `validateForExport(state) -> {errors, warnings, info}`:
   - Errors (block download): `teams.home`/`teams.away` non-empty and distinct; every mapped event's `team` matches one of them; every `minute` finite and `>= 0`; every `type` in the active sport's known vocabulary (defensive against stale IndexedDB state after a config change).
   - Warnings: no non-neutral events; `minute` exceeds `maxSaneMinute`.
   - Info only: neutral-event count excluded from export.
4. **`ExportPanel.tsx`** — runs validation, shows errors/warnings/info, enables download only once `errors.length === 0`.
5. **`export/download.ts`** — triggers a browser file download of the JSON.
6. **Close the loop** — tag a short synthetic match, Export, drop the file into `examples/`, run:
   ```bash
   python momentum.py <exported-file>.json out.png --sport rugby
   ```
   from the repo root. If the chart renders without a `KeyError`/`ValueError`, the contract holds.

Out of scope for the whole plan: multi-match library, embedded/synced video, multi-select modifiers, runtime config upload (JSON configs are bundled at build time, not uploaded live).

## Verification checklist per phase

- **Phase 1**: tag a burst of events, confirm sub-1-second no-mouse logging and correct clock behavior. *(Done — driven headless via Playwright, see `.claude/skills/verify/SKILL.md` for the recipe.)*
- **Phase 2**: `npm run check:vocab` passes for both sports; Try triggers the follow-up modal, fully hotkey-navigable; `phase_sequence` triggers the derived-input panel correctly. *(Done — all three verified in-browser, plus Escape/no-team/neutral-team/out-of-range-key probes.)*
- **Phase 3**: refresh mid-match, confirm autosave rehydrates; edit/delete timeline entries; confirm undo restores the last action.
- **Phase 4 (end-to-end)**: the `python momentum.py ... --sport rugby` round-trip above — this is the real proof the schema contract holds.

### Reference files (match-momentum side, read-only — the contract this all targets)

- `translators/rugby.py`, `translators/football.py`
- `translators/rugby_weights.json`, `translators/football_weights.json`
- `translators/__init__.py` (SPORTS registry)
- `sources/custom_json.py`, `core/schema.py`
