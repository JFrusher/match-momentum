# Match Momentum — rebuilding FIFA's World Cup 2026 broadcast chart

[![tests](https://github.com/Jfrusher/match-momentum/actions/workflows/tests.yml/badge.svg)](https://github.com/Jfrusher/match-momentum/actions/workflows/tests.yml)

Watching the 2026 World Cup, I kept noticing the **Match Momentum** graphic on the broadcast — a mirrored area chart showing which team is "on top" minute by minute. FIFA doesn't publish the methodology, so I rebuilt it from scratch.

![Match momentum chart](momentum_arg_egy.png)

## The match

Argentina 3–2 Egypt, Round of 16, July 7 2026 (Mercedes-Benz Stadium, Atlanta). Egypt led 2–0 in the 75th minute; Argentina became the first team in World Cup history to win a knockout match in regulation after trailing by two that late. Romero 79', Messi 84', Enzo Fernández 90+2'.

The momentum chart makes the story visible in one glance: Argentina on top for most of the match, two sharp Egyptian counter-spikes (both goals), then a blue wall at the end.

## The model

Each threat event (shot, chance, goal, sustained pressure) injects "momentum energy" for its team, which **decays exponentially** (half-life ≈ 3 min). The chart shows **net momentum** (home energy minus away energy), smoothed with a Gaussian kernel: at any moment only one team is on top, matching the visual grammar of FIFA's broadcast graphic and The Athletic's momentum charts. When one side has momentum, the other by definition doesn't.

```
momentum_team(t) = Σ over events e:  w_e · exp(-λ · (t - t_e))   for t ≥ t_e
```

## Validation

FIFA doesn't publish its momentum charts as data or standalone images, so validation uses two independent references: Flashscore's published Momentum graphics for the same matches, and a broadcast photo of FIFA's own graphic (AUS–TUR).

![Model vs reference](comparison_model_vs_reference.png)

Bars = Flashscore's graphic, traced by eye (their snapshots: ARG–EGY at 2–2, AUS–TUR at half-time). White curve = this decay model. Run `python compare.py` to regenerate.

What validation caught: my first ARG–EGY reconstruction assumed Egypt dominated momentum because they led 2–0. Flashscore's chart showed the opposite — Argentina controlled territory throughout while Egypt scored on counters. The event stream was corrected accordingly. Also notable: FIFA's broadcast chart and Flashscore's disagree with *each other* (e.g. Australia's early momentum), because "momentum" has no standard definition — every provider models it differently.

Limitations: two matches, references traced by eye, and event streams calibrated against the same graphics they're compared to — so this demonstrates the model can reproduce the reference shapes, not that it independently replicates any provider's algorithm. A rigorous test needs official event data (Opta/StatsBomb) as input.

## Data honesty

Goal and penalty minutes are real (per ESPN / Sky Sports match reports). The granular event stream (shots, pressure spells) is **reconstructed from match report narratives** to illustrate the model — official event-level data isn't public. Swap in a real event feed (Opta/StatsBomb) via a new `sources/` adapter and the decay/smoothing pipeline works unchanged.

## Architecture

The decay math and chart renderer don't know what sport they're drawing. Three independent pieces compose to produce a chart:

```
DataSource.parse()  ->  Sport.translate()  ->  MomentumEngine.compute()  ->  chart.render()
   (raw provider          (raw events ->           (decay + smoothing,        (figure, driven
    format in)              StandardEvent)           sport-agnostic)            by ChartProfile)
```

- **`core/`** — the sport-agnostic engine: `schema.py` (`StandardEvent`, the only shape the math ever sees), `engine.py` (`MomentumEngine`, the exponential-decay + Gaussian-smoothing math, unchanged since the original model), `chart.py` (the FIFA-style area-chart renderer, driven by a `ChartProfile` rather than hardcoded match structure).
- **`translators/`** — one module per sport (`football.py`, `rugby.py`), each a `BaseSport` implementing `translate(raw_events) -> list[StandardEvent]` plus match structure (duration, half-time marker, decay half-life, axis labels). Static event→weight tables live alongside as JSON (`football_weights.json`, `rugby_weights.json`); sports that need real computation — rugby's phase-play territory scoring has no discrete "shot" to key off, so its weight is derived from metres gained / field position / linebreaks — override `translate()` in code instead of a flat lookup.
- **`sources/`** — one module per data provider (currently just `custom_json.py`, the `events.json` shape used throughout this repo), parsing a provider's raw match data into a common shape. Kept independent of `translators/` so any sport works with any source instead of one class per (sport, provider) pair.

To add a new sport: implement `BaseSport` in `translators/`, register it in `translators/__init__.py`'s `SPORTS` dict, run with `--sport yourname`. `translators/rugby.py` is a worked example — see its module docstring for how territory-based threat and cards (marker-only, not fed into the decay sum) are modeled, and why.

To add a new data provider (Opta, StatsBomb, ...): implement `BaseDataSource` in `sources/`, mapping its raw fields into whatever shape your chosen `Sport.translate()` expects.

## Run it

```bash
pip install -e .
python momentum.py examples/events_arg_egy.json momentum_arg_egy.png
python momentum.py examples/events_rugby_demo.json momentum_rugby_demo.png --sport rugby
```

Edit an `examples/*.json` file (or point at your own) to chart any match. `events_rugby_demo.json` is hand-written synthetic data exercising the rugby translator's event vocabulary — not calibrated against a real broadcast graphic the way the football examples are.

## Tracer (live tagging)

The model needs an event stream, and typing one out during a match is slow and imprecise. `tracer/` is a NiceGUI app for logging a rugby match by **tracing the ball's path with the mouse**: one continuous drag per possession, auto-segmented into carries, passes and kicks by the geometry of the line alone.

![Live Trace](tracer_demo.png)

Amber carry, blue pass, red kick; the white dots are where the recognizer cut the line. Keyboard taps layer on player numbers, linebreaks and scores without interrupting the drag. Traced distance and territory feed the momentum weights directly instead of typed estimates.

Each possession also records **how it began** — scrum, lineout, penalty, restart, turnover, interception — because in rugby that is a large part of what the possession is worth. Most of it is read off the trace (a kick ending at a touchline is a lineout; the kick-to-touch-on-the-full law decides where the lineout is taken); the two things a line cannot show, a scrum and a penalty, are single taps. Every inferred attribution renders as a chip on the pitch, and the chip is the correction UI: there are two teams, so a wrong guess is one click from right.

The line is read from its **shape, never its speed** — the same trace classifies identically whether drawn in real time or sketched afterwards, which is what makes tracing from paused, scrubbed video possible. `tests/test_pace_invariance.py` pins that property.

Every export is validated by running the real `RugbySport` translator in-process; `examples/tracer-sample.json` is the round-trip proof artifact. See `tracer/README.md` for the mechanic and hotkeys, `tracer/TUNING.md` for the recognizer.

```bash
python -m tracer.app
```

**What this has not yet done:** the tracer has never been used on a real match. Its thresholds are tuned against 39 synthetic fixture scenarios and a pace-invariance fence, not against a human tracing live footage, and the `origin_factor` weights that price a lineout against a scrum are unvalidated judgement calls. The screenshot above is a synthetic trace. Until a real match has been traced end to end, treat this as a working instrument with an untested calibration — the same standard the football model is held to above.

The previous tagging tool — a React/TypeScript keyboard-only event logger — is archived unchanged in `legacy/tagger/`. It was replaced because a keyboard vocabulary can record *that* a carry happened but not *where*, and territory is most of rugby's momentum signal.
