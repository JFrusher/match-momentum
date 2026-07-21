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
python -m tracer.app 8123      # optional port (default 8080)
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

Trace at whatever pace suits you — live, real-time replay, or a quick
after-the-fact sketch. The line is read from its **geometry** (shape,
distances, turns), not its drawing speed, so the same trace classifies
identically however fast you draw it.

## Keys (tap any time during the trace; timing correlates them)

| Key | Meaning |
|---|---|
| `A` / `Space` | End the current play chain |
| `S` | Scrum — ends the play and marks a scrum (knock-on, injury restart, …) |
| `F` | Penalty — ends the play, awards against the side carrying |
| `Ctrl`+`Z` | Undo the last committed chain |
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

## How the next possession starts, and fixing it

Every possession is recorded with the reason it began — `kickoff`, `restart`,
`scrum`, `lineout`, `penalty`, `turnover_open`, `interception`, `kick_return` —
and that reason scales its momentum weight (`origin_factor` in
`translators/rugby_weights.json`). Most of it is read off the trace itself: a
kick finishing at a touchline is a lineout, a score is a restart, an
intercepted pass is an interception. Only the two things a line cannot show —
a scrum and a penalty — are tapped.

The result appears as a **chip** on the pitch, above its mark, and the chip is
the correction UI:

- **Click the team name** to swap it. There are two teams, so a wrong guess is
  always one click from right.
- **Click `swap_horiz`** on a lineout to move the mark. A kick to touch from
  outside your own 22 is assumed to have gone out on the full, so the mark
  goes back to the kick; click to say it bounced first.
- The **type is never editable** — it was either certain or you typed it. A
  lineout does not become a scrum.
- A penalty chip also offers *to touch · at goal · tap · scrum*, pre-selected
  on the guess. Ignoring it accepts that guess; nothing blocks. Choosing
  *to touch* arms the next stroke, so the lineout that follows correctly keeps
  the throw with the kicking team.

**Click any drawn segment** to cycle its action (carry → pass → kick); the
chain re-commits with the consequences that follow.

## Autosave

Every committed chain (and every 5s) writes `tracer/sessions/session.json`
atomically; relaunching offers to resume, clock paused. A crash loses at
most the one in-progress trace.

## Dev mode (segment introspection, replay, trace capture)

```
python -m tracer.app 8080 dev      # or open http://localhost:8080/?dev=1
```

A right drawer logs one report per chain — **including rejected ones** (the
"why did my trace disappear" case): path stats (points, duration, Hz, net
px), the boundary baselines plus every candidate's evidence score (and the
top near-miss rejects — what a missed turn actually scored), a per-segment
score table (each feature's value, weight, and contribution per class, final
probabilities, confidence margin, `CARRY->KICK (hint)` when a tap relabelled
it), and every tap-correlation decision. The canvas draws a white dot at
each picked boundary.

- **Replay** injects any `tracer/fixtures.py` scenario (or a saved trace)
  through the real pipeline — same canvas redraw, same report. Start the
  clock first or minute stamps read ~0.
- **Save last trace** snapshots the last chain's raw inputs to
  `tracer/dev_traces/` (gitignored). Replaying the file must reproduce the
  identical report — the pipeline is deterministic on identical points.
- **Promote a trace to a regression**: move the file to
  `tracer/tests/traces/`, add an `"expect"` key (vocabulary in
  `fixtures.check`), and `tracer/tests/test_corpus.py` picks it up as
  `trace:<name>` automatically.

## Tuning

Full workflow with a symptom→parameter diagnosis table: **[TUNING.md](TUNING.md)**.

Both recognizer layers are evidence-scored: boundary detection scores
heading/speed changes against the path's own baselines; classification is a
per-class weighted feature sum (softmax, CARRY the default reference class).
Every weight, scale, and threshold is a flat constant in `tracer/config.py`.

The loop: save the misbehaving trace in dev mode → promote it with the
expected truth → `python -m tracer.sweep` grid-sweeps any constants over the
whole corpus (39 synthetic scenarios + promoted real traces), and
`python -m tracer.fit` proposes classification weights by softmax regression
over the same corpus. Neither ever writes `config.py` — read the output,
decide, edit by hand.

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

## Calibration status

Thresholds in `config.py` are tuned against the 39 synthetic scenarios in
`fixtures.py` plus the pace-invariance fence — **not against a real match**.
Nobody has yet traced live footage end to end, so the numbers most likely to
move are the boundary accept level, the ~27m geometric kick threshold, and the
`origin_factor` weights in `translators/rugby_weights.json`, which are
judgement calls with no reference data behind them.

The loop for fixing that is already here: dev mode → Save last trace → promote
with an `"expect"` key → `python -m tracer.sweep`.

## Known MVP gaps (deliberate)

- A team kicking to itself (chip-and-chase regather) isn't representable.
- Sin bin assumes the **defending** side was binned; flip the team in Review
  when it wasn't.
- No squad-number rosters; digit typos are corrected in Review.
- No live momentum chart; chart generation stays the manual `momentum.py` step.
- No advantage, no free kicks (trace as a scrum and flip the team if needed),
  no full-time or period model beyond the halftime flip.
- The match clock is a stopwatch you start and pause to stay roughly with
  play. Trace pace and real match time are structurally unlinkable given the
  input model, so **event minutes are approximate** — and minute is the
  chart's x-axis.
- `confidence` on a segment is a diagnostic, not a certainty; see TUNING.md
  for why it ranks clean carries below ambiguous kicks.
