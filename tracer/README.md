# tracer/ — Live Trace

Trace a rugby possession chain as **one continuous mouse drag** on a pitch;
the software segments the line into carries/passes/kicks from its geometry,
keyboard taps layer on annotations, and the result exports as the same JSON
`momentum.py` already consumes. Replaces the old keyboard-only `tagger/`
(archived in `legacy/`).

## Run

```
pip install -e .[dev]          # once, from repo root
python -m tracer.app           # browser tab; native window if pywebview installed
```

## The mechanic

1. Press and **hold** the mouse button when a possession starts; follow the
   ball. Keep the button down through the whole chain — pass, run, pass,
   tackle are one unbroken line.
2. Tap **`A` or `Space`** when the play dies (tackle/ruck/whistle). That —
   not releasing the button — is the authoritative end; release is only a
   defensive fallback.
3. The raw white line redraws color-coded by inferred action:
   amber carry · blue pass · red kick (dashed = intercepted).

**Assumption**: you trace in rough real-time sync with the play (live or
real-time-paced replay). Kick-vs-carry classification reads tracing speed;
leisurely after-the-fact reconstruction breaks that signal.

## Keys (tap any time during the trace; timing correlates them)

| Key | Meaning |
|---|---|
| `A` / `Space` | End the current play chain |
| `K` / `P` / `R` | Override a segment as Kick / Pass / Run(carry) |
| `L` | Linebreak flag on the current carry |
| `Shift` (hold) | Pass under it was intercepted (splits possession) |
| digits | Player number at the nearest action boundary (quick `1`,`0` = 10) |
| `Z` / `X` | Possession to home / away |
| `T` `N` `G` `V` `B` | Try · Penalty kick · Drop goal · Turnover won · Sin bin |
| `C` / `M` | Conversion made / missed (within 90s of a `T`) |

Kicks and interceptions flip possession automatically. Clock start/pause and
halftime direction flip are buttons, not keys. **Review** opens a
non-blocking timeline editor for corrections during stoppages.

## Autosave

Every committed chain (and every 5s) writes `tracer/sessions/session.json`
atomically; relaunching offers to resume, clock paused. A crash loses at
most the one in-progress trace.

## Tuning

All segmentation thresholds live in `tracer/config.py` with comments. If
real-world traces misclassify, tune there and check against
`tracer/tests/test_segmentation.py`, which encodes the expected behavior on
synthetic paths with known ground truth.

## Manual test recipe (browser half; the pure logic is pytest-covered)

1. `python -m tracer.app`, start a match, start the clock.
2. **Capture spike check**: hold the mouse down and drag while tapping
   letters and holding Shift — the white line must follow the cursor and no
   key must interrupt the drag (this is the Phase-2 assumption; if taps drop
   or the drag aborts, file it before trusting anything else).
3. Trace a carry (slow drift forward), a pass (quick backward-lateral
   flick), a carry, then a kick (fast long sweep); tap `A`. Expect
   amber–blue–amber–red redraw.
4. Tap `T` then `C` after a scoring trace; open Review and confirm the
   events; export and run
   `python momentum.py examples/tracer-sample.json out.png --sport rugby`.
5. Kill the process mid-match, relaunch, choose Resume: events and clock
   (paused) must survive.

## Known MVP gaps (deliberate)

- A team kicking to itself (chip-and-chase regather) isn't representable.
- Sin bin assumes the **defending** side was binned; flip the team in Review
  when it wasn't.
- No squad-number rosters; digit typos are corrected in Review.
- No live momentum chart; chart generation stays the manual `momentum.py` step.
