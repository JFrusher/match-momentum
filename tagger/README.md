# Tagger

A fast, keyboard-only sports event logger. Log an event in one or two keystrokes (Team → Event → Modifier), then export JSON that plugs directly into `../momentum.py`.

This is Phase 1 of the build: a static skeleton proving the hotkey loop and clock work, with rugby event data hardcoded inline (`src/data/rugbyInline.ts`). No config-driven sport rules, follow-up prompts, timeline editing, persistence, or export yet — see the phased plan for what's next.

## Setup

```bash
cd tagger
npm install
npm run dev
```

Open the printed local URL. Requires Node.js (LTS) — install via [nodejs.org](https://nodejs.org) or your package manager if you don't have it.

## Hotkeys

| Key | Action |
|---|---|
| `Z` / `X` / `C` | Stage Team A / Team B / Neutral (sticky — stays selected across events) |
| `1`–`9` | Select the event type in that on-screen position. If it has no modifiers, it logs immediately. |
| `Q W E R T Y U I O P` | Select the modifier in that on-screen position (always logs immediately) |
| `Enter` | Submit now (skips the modifier step) |
| `Backspace` | Clear the last staged field (modifier, then event type — team is never cleared this way) |
| `Space` | Start/pause the clock |
| `Shift+Space` | Arm a clock reset — press `Enter` to confirm, any other key cancels |

The clock's scrub slider is mouse-only (enabled while paused).

## Manual QA loop against the Python pipeline

Once export lands (Phase 4), the way to prove the JSON contract actually holds is to round-trip through the real pipeline:

```bash
# from the repo root, after using Export in the Tagger:
python momentum.py <exported-file>.json out.png --sport rugby
```

If the chart renders without a `KeyError` or `ValueError`, the export is contract-compliant.
