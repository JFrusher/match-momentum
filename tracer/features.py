"""Segment feature extraction + per-class linear scoring (Rubine-style).

extract() turns one segment's raw points into named squashed features;
score() turns features into per-class scores, softmax probabilities, the
winning action, and a confidence margin. CARRY is the fixed reference class
(score 0): PASS/KICK scores read as evidence *against* the carry default.

Weights/biases/scales are flat constants in config.py, read via getattr at
call time so sweep.py and fit.py setattr take effect without reimport.

Heading variance is deliberately absent: length-weighted per-step headings
telescope to net/path-length, which is exactly the `straight` feature.
"""

import math

from . import config

FEATURES = ("backward", "lateral", "fast", "short", "kickburst",
            "straight", "bursty", "dist")
SCORED_CLASSES = ("PASS", "KICK")
CLASSES = ("CARRY",) + SCORED_CLASSES  # tie-break order: CARRY wins


def _rect_tanh(value, scale):
    return math.tanh(max(0.0, value) / scale)


def extract(points, attack_dir):
    """(features, raw) for one segment. attack_dir: +1 = +x, -1 = -x."""
    px = config.PX_PER_M
    start, end = points[0], points[-1]
    fwd_m = attack_dir * (end.x - start.x) / px
    lat_m = (end.y - start.y) / px
    dur_s = end.t - start.t
    net_m = math.hypot(end.x - start.x, end.y - start.y) / px
    speed_net = net_m / dur_s if dur_s > 0 else 0.0

    path_m, step_speeds = 0.0, []
    for a, b in zip(points, points[1:]):
        d = math.hypot(b.x - a.x, b.y - a.y) / px
        path_m += d
        step_speeds.append(d / max(b.t - a.t, 1e-4))
    straightness = net_m / path_m if path_m > 1e-9 else 1.0
    peak_speed = sorted(step_speeds)[int(0.9 * (len(step_speeds) - 1))]
    mean_speed = path_m / dur_s if dur_s > 0 else 0.0
    burstiness = peak_speed / mean_speed if mean_speed > 1e-9 else 0.0

    fast = math.tanh((speed_net - config.FAST_SPEED_MPS) / config.F_SPEED_SCALE_MPS)
    short = math.tanh((config.SHORT_DURATION_MS / 1000 - dur_s) / config.F_DUR_SCALE_S)
    features = {
        "backward": _rect_tanh(-fwd_m, config.F_BACK_SCALE_M),
        "lateral": _rect_tanh(abs(lat_m) - config.LATERAL_RATIO * abs(fwd_m),
                              config.F_LAT_SCALE_M),
        "fast": fast,
        "short": short,
        "kickburst": min(max(0.0, fast), max(0.0, short)),
        "straight": math.tanh((straightness - config.F_STRAIGHT_CENTER)
                              / config.F_STRAIGHT_SCALE),
        "bursty": math.tanh((burstiness - config.F_BURSTY_CENTER)
                            / config.F_BURSTY_SCALE),
        "dist": _rect_tanh(net_m, config.F_DIST_SCALE_M),
    }
    raw = {"fwd_m": round(fwd_m, 2), "lat_m": round(lat_m, 2),
           "dur_s": round(dur_s, 3), "net_m": round(net_m, 2),
           "speed_net": round(speed_net, 2), "straightness": round(straightness, 3),
           "burstiness": round(burstiness, 2)}
    return features, raw


def class_weights(cls):
    """(bias, {feature: weight}) read live from config."""
    bias = getattr(config, f"B_{cls}")
    return bias, {f: getattr(config, f"W_{cls}_{f.upper()}") for f in FEATURES}


def score(features):
    """(scores, probs, action, confidence) — confidence = top prob - second."""
    scores = {"CARRY": 0.0}
    for cls in SCORED_CLASSES:
        bias, weights = class_weights(cls)
        scores[cls] = bias + sum(weights[f] * features[f] for f in FEATURES)
    peak = max(scores.values())
    exps = {c: math.exp(s - peak) for c, s in scores.items()}
    total = sum(exps.values())
    probs = {c: e / total for c, e in exps.items()}
    action = max(CLASSES, key=lambda c: (scores[c], -CLASSES.index(c)))
    ranked = sorted(probs.values(), reverse=True)
    return scores, probs, action, ranked[0] - ranked[1]
