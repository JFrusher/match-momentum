# Match Momentum

[![tests](https://github.com/Jfrusher/match-momentum/actions/workflows/tests.yml/badge.svg)](https://github.com/Jfrusher/match-momentum/actions/workflows/tests.yml)

**Capture a rugby match by tracing the ball with your mouse, and get a broadcast-style momentum chart out of it.**

One continuous drag per possession. The software reads the geometry of that line — its turns, its distances, the shape of each leg — and segments it into carries, passes and kicks. Keyboard taps layer on player numbers, linebreaks and scores without interrupting the drag. Traced distance and field position feed the momentum model directly, so the chart is built from where the ball actually went rather than from typed estimates.

![Live Trace](tracer_demo.png)

*Amber carry, blue pass, red kick. White dots mark where the recognizer cut the line.*

Behind the tracer sits a sport-agnostic momentum engine: exponential decay over weighted threat events, rendered as the mirrored area chart familiar from football broadcasts. Football and rugby ship as translators; the engine itself knows about neither.

![Rugby momentum chart](momentum_rugby_demo.png)

## Quick start

Python 3.11+.

```bash
pip install -e ".[dev]"

# trace a match
python -m tracer.app                 # opens a browser tab (native window if pywebview is installed)
python -m tracer.app 8123            # optional port, default 8080

# chart an event file
python momentum.py examples/tracer-sample.json out.png --sport rugby
python momentum.py examples/events_arg_egy.json out.png --sport football
```

`examples/tracer-sample.json` is a real tracer export, validated end to end through the rugby translator — it is the round-trip proof that what the tracer writes is what `momentum.py` reads.

## Live Trace

Full mechanic, hotkey table and tuning workflow: **[tracer/README.md](tracer/README.md)**.

The essentials:

- **Hold** the mouse button when a possession starts and follow the ball. Pass, run, pass, tackle are one unbroken line.
- **Tap `A` or `Space`** when the play dies. That, not releasing the button, is the authoritative end of the chain.
- The line redraws colour-coded by inferred action as you go, which is the recognizer's feedback channel.

Two design decisions shape everything else:

**The line is read from its shape, never its speed.** The same trace classifies identically whether it was drawn in real time or sketched afterwards, which is what makes tracing from paused or scrubbed video possible. [`tracer/tests/test_pace_invariance.py`](tracer/tests/test_pace_invariance.py) pins that property.

**Every inferred attribution renders as a chip, and the chip is the correction UI.** Each possession records how it began — scrum, lineout, penalty, restart, turnover, interception — because in rugby that is a large part of what the possession is worth. Most of it is read off the trace: a kick ending at a touchline is a lineout, and the kick-to-touch-on-the-full law decides where that lineout is taken. The two things a line cannot show, a scrum and a penalty, are single taps. There are only ever two teams, so a wrong guess is one click from right.

## The momentum model

Each threat event injects momentum energy for its team, which decays exponentially (half-life ≈ 3 min for football, set per sport by the translator):

```
momentum_team(t) = Σ over events e:  w_e · exp(-λ · (t - t_e))   for t ≥ t_e
```

The chart shows **net** momentum — home energy minus away energy, smoothed with a Gaussian kernel — so at any moment exactly one team is on top. That matches the visual grammar of the broadcast graphics the model was built to reproduce: when one side has momentum, the other by definition doesn't.

Weighting is where the sports differ. Football keys off discrete threat events (shot, chance, goal, sustained pressure) via a flat lookup table. Rugby has no equivalent discrete moment for phase play, so [`translators/rugby.py`](translators/rugby.py) derives weight in code from metres gained, field position and linebreaks instead.

## Architecture

The decay math and the chart renderer don't know what sport they're drawing. Three independent pieces compose:

```
DataSource.parse()  ->  Sport.translate()  ->  MomentumEngine.compute()  ->  chart.render()
   (raw provider          (raw events ->           (decay + smoothing,        (figure, driven
    format in)              StandardEvent)           sport-agnostic)            by ChartProfile)
```

| Package | Role |
|---|---|
| [`core/`](core/) | `schema.py` — `StandardEvent`, the only shape the math ever sees. `engine.py` — decay and smoothing. `chart.py` — the area-chart renderer, driven by a `ChartProfile`. |
| [`translators/`](translators/) | One `BaseSport` per sport: event weighting plus match structure (duration, half-time marker, decay half-life, axis labels). Static weight tables live alongside as JSON. |
| [`sources/`](sources/) | One `BaseDataSource` per data provider, parsing raw match data into a common shape. Kept independent of `translators/` so any sport works with any source, rather than one class per (sport, provider) pair. |
| [`tracer/`](tracer/) | The Live Trace app: capture, recognition, review and export. Writes the same JSON the sources read. |

**To add a sport:** implement `BaseSport` in `translators/`, register it in `translators/__init__.py`'s `SPORTS` dict, run with `--sport yourname`. [`translators/rugby.py`](translators/rugby.py) is the worked example — its module docstring covers territory-based threat and why cards are marker-only rather than fed into the decay sum.

**To add a data provider** (Opta, StatsBomb, …): implement `BaseDataSource` in `sources/`, mapping its raw fields into the shape your chosen `Sport.translate()` expects. The decay and rendering pipeline is unchanged either way.

## Tests

225 tests, run on every push and pull request:

```bash
python -m pytest -q
```

The recognizer is gated by a corpus of 39 synthetic trace scenarios ([`tracer/fixtures.py`](tracer/fixtures.py)) replayed at baseline config, plus the pace-invariance fence. Every threshold and weight it depends on is a flat constant in [`tracer/config.py`](tracer/config.py); the tuning loop that moves them — save a trace, promote it with its expected truth, sweep or fit — is documented in [tracer/TUNING.md](tracer/TUNING.md), alongside the current calibration status.

## Background

This is a fork of [JakeBonnici22/match-momentum](https://github.com/JakeBonnici22/match-momentum), a reconstruction of FIFA's World Cup 2026 broadcast momentum graphic: an exponential-decay model over a hand-built football event stream, validated against published Flashscore graphics. That original write-up — the ARG–EGY match narrative, the validation against reference charts, and the honest limits of both — is worth reading in the [upstream README](https://github.com/JakeBonnici22/match-momentum#readme).

Two things pulled this repo away from there. First, the model is not really about football, so the football-specific parts were factored out into the translator and source split above. Second, the model needs an event stream, and typing one out during a match is slow and imprecise — which is what the tracer exists to solve. An earlier attempt at that, a keyboard-only React event logger, is archived unchanged in [`legacy/tagger/`](legacy/tagger/): a keyboard vocabulary can record *that* a carry happened but not *where*, and territory is most of rugby's momentum signal.

## Acknowledgements

Thanks to [Jake Bonnici](https://github.com/JakeBonnici22) for [match-momentum](https://github.com/JakeBonnici22/match-momentum), the project this one is forked from. The decay-and-smoothing engine in `core/engine.py` and the broadcast-style chart it feeds are his work, and they remain the heart of everything here — the rugby translator and the tracer are input layers wrapped around a model that already worked.

## Contributing

Issues and pull requests welcome. Run `python -m pytest -q` before opening one; anything touching the recognizer should come with a fixture scenario in `tracer/fixtures.py` covering it.

## Licence

[MIT](LICENSE).
