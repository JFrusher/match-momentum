# Tuning the line recognizer

How to adapt the parameters that decide what a traced line *is*. Both
decision layers are **evidence-scored**: every decision is a weighted sum of
named features, every weight a plain number in [`config.py`](config.py),
every score breakdown visible in the dev panel. The logic lives in
[`segmentation.py`](segmentation.py) + [`features.py`](features.py); tuning
never requires touching either.

## The two decision layers

**Layer 1 — boundary detection** (where does one action end?). Each interior
point of the smoothed path gets heading-change (`angle`) and speed-change
(`ratio`) measurements from `HEADING_WINDOW_MS` velocity windows. Evidence is
scored against **this path's own baselines** (median angle/ratio, floored) —
a wobbly hand raises the bar automatically:

```
score = W_BOUNDARY_ANGLE * tanh(max(0, angle - angle_base) / BOUNDARY_ANGLE_SCALE_DEG)
      + W_BOUNDARY_SPEED * tanh(max(0, ratio - ratio_base) / BOUNDARY_RATIO_SCALE)
boundary iff score >= BOUNDARY_ACCEPT
```

where `angle_base = max(BOUNDARY_ANGLE_FLOOR_DEG, median angle) * BOUNDARY_ANGLE_BASE_MULT`
(ratio analogous). Either evidence alone can clear the accept threshold.
Grouping (`BOUNDARY_GROUP_MS`), end-drop and thinning (`MIN_SEGMENT_MS`), and
the accidental-click reject (`MIN_MOVEMENT_PX`) are unchanged.

Calibration on the noisy corpus: genuine turns score **>= 0.92**, end-of-trace
release wobble **<= 0.73** — `BOUNDARY_ACCEPT = 0.75` sits mid-band (sweep
2026-07-20, 0.65-0.85 all-pass).

**Layer 2 — classification** (what is each segment?). Eight named features
per segment ([`features.py`](features.py)), each squashed to roughly [-1, 1]:

| Feature | What it measures | Evidence for |
|---|---|---|
| `backward` | net motion against attack direction (rectified, sharp) | PASS — the rugby-law signal |
| `lateral` | lateral excess over `LATERAL_RATIO` x forward (rectified) | PASS |
| `fast` | net speed vs `FAST_SPEED_MPS` | (trainable) |
| `short` | duration vs `SHORT_DURATION_MS` | (trainable) |
| `kickburst` | `min(rect(fast), rect(short))` — fast AND short | KICK |
| `straight` | net displacement / path length | (trainable) |
| `bursty` | 90th-pct / mean step speed | (trainable) |
| `dist` | net displacement magnitude | (trainable) |

Per class: `score = B_c + Σ W_c_FEATURE * feature`; **CARRY is the fixed
reference class** (score 0 — no constants). Softmax gives probabilities;
argmax wins (CARRY wins ties); `confidence = top prob - second prob` (dev
panel only). Attack direction still flips after every KICK — a marginal kick
call corrupts everything downstream, and the dev panel now shows you its
margin. Known limit: a K/P/R hint that changes a KICK call does **not**
re-flip downstream attack direction (taps run after geometry).

Shipped weights encode the retired rule cascade exactly (pinned by the
parity test in `tests/test_scoring.py`): `W_PASS_BACKWARD=8 > W_PASS_LATERAL=7 >
W_KICK_KICKBURST=6` mirrors old rule priority; the zeros are trainer headroom.

## Symptom -> knob

| Symptom | Likely fix |
|---|---|
| One action splits into phantom segments | Raise `BOUNDARY_ACCEPT`; check the dev report — accepted candidates show their score |
| Real turn not detected (two actions read as one) | Lower `BOUNDARY_ACCEPT` — the report's **near-miss** lines show exactly what the missed turn scored; if its angle sat under `angle_base`, lower `BOUNDARY_ANGLE_BASE_MULT` |
| Double boundaries at one turn | Raise `BOUNDARY_GROUP_MS` |
| Quick phases swallowed | Lower `MIN_SEGMENT_MS` |
| Kicks read as carries | Check segment's `kickburst` row in the score table: if `fast` or `short` sat at 0, lower `FAST_SPEED_MPS` / raise `SHORT_DURATION_MS`; else raise `W_KICK_KICKBURST` |
| Carries read as kicks | Raise `FAST_SPEED_MPS` or lower `W_KICK_KICKBURST` |
| Flat passes read as carries | Raise `W_PASS_LATERAL` or lower `F_LAT_SCALE_M` (sharper) or lower `LATERAL_RATIO` |
| Crabbing runs read as passes | Raise `LATERAL_RATIO` or lower `W_PASS_LATERAL` |
| Driven-back carries read as passes | The soft-backward payoff: add CARRY-favoring evidence via **negative** PASS weights on `straight`/`short` (a tackle wiggle is neither straight nor brief) — or let `python -m tracer.fit` find them once such traces are promoted |
| Short legitimate traces vanish | Lower `MIN_MOVEMENT_PX` |
| Everything after one segment wrong | Marginal KICK call flipped attack direction — the score table shows its confidence |

## The tuning loop

1. **Capture with evidence** — `python -m tracer.app 8080 dev`. The drawer
   shows, per segment, every feature's squashed value, weight, and
   contribution per class, plus scores/probs/confidence; per path, the
   boundary baselines and the top near-miss candidates. Misreads become
   numeric instructions ("the missed turn scored 0.68 against accept 0.75").
2. **Save the trace** — *Save last trace* snapshots raw inputs to
   `tracer/dev_traces/` (gitignored). Replay to confirm determinism.
3. **Promote to ground truth** — move to `tracer/tests/traces/`, add
   `"expect"` (vocabulary: `fixtures.check`). `test_corpus.py` picks it up;
   it also joins the **fit training set** automatically.
4. **Propose** — two tools, same philosophy (print, never write):
   - `python -m tracer.sweep` — grid over any config constants (edit `GRID`;
     weights sweep the same as thresholds). Ranked pass-count table.
   - `python -m tracer.fit` — softmax regression over every exact-actions
     corpus case (hint scenarios excluded), L2-anchored to your current
     values; prints a paste-ready weight block + before/after corpus pass
     counts + confusion. Weights barely move until real traces disagree with
     the synthetic corpus — that is correct behavior.
5. **Decide and edit by hand** — paste/adjust in `config.py`.
6. **Verify** — `python -m pytest tracer/tests/` (the parity test only pins
   the *initial* weights encoding; once you deliberately retune, update or
   retire it — it exists to guarantee the switchover, not to freeze tuning
   forever). Then re-trace live in dev mode.

## Old -> new constants

| Retired | Replaced by |
|---|---|
| `ANGLE_THRESHOLD_DEG = 55` | `BOUNDARY_*` baselines/scales + `BOUNDARY_ACCEPT` |
| `SPEED_RATIO_THRESHOLD = 2.5` | same |
| cascade rule "backward => PASS" | `W_PASS_BACKWARD` (soft, sharply squashed) |
| cascade rule "lateral => PASS" | `W_PASS_LATERAL` + `F_LAT_SCALE_M` |
| cascade rule "fast+short => KICK" | `W_KICK_KICKBURST` (min-composed AND) |
| `LATERAL_RATIO`, `FAST_SPEED_MPS`, `SHORT_DURATION_MS` | still present — now feature *centers* |

## Adapting beyond thresholds

- **New scenario**: `_sc(...)` in [`fixtures.py`](fixtures.py) — joins corpus,
  sweep, and fit automatically.
- **New feature** (e.g. curvature for spiral kicks): add its formula +
  `F_*` scale in `features.py`/`config.py`, append to `FEATURES`, add
  `W_PASS_*`/`W_KICK_*` zeros — extraction, scoring, dev table, sweep, and
  fit all pick it up by name with no further wiring.
- **New class** (e.g. OFFLOAD): add to `SCORED_CLASSES` + its `B_`/`W_`
  block; downstream consumers of `seg.action` must learn the new string
  (canvas color, events possession logic).
- **Different sport/scale**: `PX_PER_M`, pitch dims, `FAST_SPEED_MPS` are the
  physical anchors; gesture dynamics transfer roughly as-is.
