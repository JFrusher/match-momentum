"""Path -> classified Segments. The highest-risk module; pure, no NiceGUI.

Splits one continuous traced path into segments at geometric boundaries
(sharp heading changes, sudden speed changes), then classifies each as
CARRY/PASS/KICK:

  - PASS: net displacement backward or predominantly lateral — a forward
    pass is illegal in rugby, so this is the one reliable signal.
  - KICK: fast, short traced burst (assumes rough real-time tracing).
  - CARRY: everything else (the deliberate default — Decision 12).

Attack direction flips after every KICK segment: the receiver attacks the
other way, so their onward carry must not read as "backward = pass".
Interceptions are unknown at geometry time; a mislabelled return run is
corrected by an R type-hint tap or in review.
"""

import math

from . import config, features
from .continuity import PathPoint, PlayerTag, Segment

# Evidence from the most recent segment_path() + apply_taps() call, for the
# dev panel. Rebuilt per call; MatchState snapshots a reference per chain.
# Module-level is safe: NiceGUI handlers run synchronously on one event loop.
last_debug: dict = {}


def _smooth(points: list[PathPoint]) -> list[PathPoint]:
    half = config.SMOOTH_WINDOW_PTS // 2
    out = []
    for i in range(len(points)):
        window = points[max(0, i - half):i + half + 1]
        out.append(PathPoint(
            sum(p.x for p in window) / len(window),
            sum(p.y for p in window) / len(window),
            points[i].t,
        ))
    return out


def _mean_velocity(points, i, side):
    """Mean velocity vector over HEADING_WINDOW_MS before (-1) / after (+1) index i."""
    horizon = config.HEADING_WINDOW_MS / 1000
    t0 = points[i].t
    if side < 0:
        sel = [p for p in points[:i + 1] if t0 - p.t <= horizon]
    else:
        sel = [p for p in points[i:] if p.t - t0 <= horizon]
    if len(sel) < 2 or sel[-1].t <= sel[0].t:
        return None
    dt = sel[-1].t - sel[0].t
    return ((sel[-1].x - sel[0].x) / dt, (sel[-1].y - sel[0].y) / dt)


def _angle_deg(a, b) -> float:
    na, nb = math.hypot(*a), math.hypot(*b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    dot = (a[0] * b[0] + a[1] * b[1]) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def _boundary_candidates(points):
    """(candidates, info): per-point evidence scores vs path-adaptive baselines.

    candidates: (index, score, angle, ratio) tuples where the combined
    heading/speed-change evidence clears BOUNDARY_ACCEPT. Baselines are this
    path's own medians (floored), so a wobbly hand raises the bar and either
    evidence alone can still clear the accept threshold.
    """
    measured = []
    for i in range(1, len(points) - 1):
        before = _mean_velocity(points, i, -1)
        after = _mean_velocity(points, i, +1)
        if before is None or after is None:
            continue
        speed_b, speed_a = math.hypot(*before), math.hypot(*after)
        if speed_b < 1e-6 and speed_a < 1e-6:
            continue  # stationary hover, heading is noise
        angle = _angle_deg(before, after)
        ratio = max(speed_b, speed_a) / max(min(speed_b, speed_a), 1e-6)
        measured.append((i, angle, ratio))
    if not measured:
        return [], {}
    med_angle = sorted(a for _, a, _ in measured)[len(measured) // 2]
    med_ratio = sorted(r for _, _, r in measured)[len(measured) // 2]
    angle_base = (max(config.BOUNDARY_ANGLE_FLOOR_DEG, med_angle)
                  * config.BOUNDARY_ANGLE_BASE_MULT)
    ratio_base = (max(config.BOUNDARY_RATIO_FLOOR, med_ratio)
                  * config.BOUNDARY_RATIO_BASE_MULT)
    accepted, near = [], []
    for i, angle, ratio in measured:
        score = (config.W_BOUNDARY_ANGLE * math.tanh(
                     max(0.0, angle - angle_base) / config.BOUNDARY_ANGLE_SCALE_DEG)
                 + config.W_BOUNDARY_SPEED * math.tanh(
                     max(0.0, ratio - ratio_base) / config.BOUNDARY_RATIO_SCALE))
        if score >= config.BOUNDARY_ACCEPT:
            accepted.append((i, score, angle, ratio))
        elif score > 0:
            near.append((score, i, angle, ratio))
    info = {"med_angle": round(med_angle, 1), "med_ratio": round(med_ratio, 2),
            "angle_base": round(angle_base, 1), "ratio_base": round(ratio_base, 2),
            "accept": config.BOUNDARY_ACCEPT,
            "near_misses": [{"i": i, "score": round(s, 2), "angle": round(a, 1),
                             "ratio": round(r, 2)}
                            for s, i, a, r in sorted(near, reverse=True)[:3]]}
    return accepted, info


def _pick_boundaries(points, candidates, notes):
    """Collapse candidate runs to one boundary each, enforce min segment length.

    Appends one human-readable string per drop/demote decision into notes.
    """
    if not candidates:
        return []
    t_start, t_end = points[0].t, points[-1].t
    # group consecutive candidates closer than BOUNDARY_GROUP_MS: one turn each
    groups, current = [], [candidates[0]]
    for cand in candidates[1:]:
        if (points[cand[0]].t - points[current[-1][0]].t) * 1000 <= config.BOUNDARY_GROUP_MS:
            current.append(cand)
        else:
            groups.append(current)
            current = [cand]
    groups.append(current)
    picked = [max(g, key=lambda c: c[1]) for g in groups]
    for g, p in zip(groups, picked):
        if len(g) > 1:
            notes.append(f"group of {len(g)} cands @{points[p[0]].t - t_start:.2f}s"
                         f" -> picked i={p[0]}")

    # drop boundaries hugging the path's ends, then thin to MIN_SEGMENT_MS spacing
    min_gap = config.MIN_SEGMENT_MS / 1000
    survivors = []
    for c in picked:
        if points[c[0]].t - t_start < min_gap or t_end - points[c[0]].t < min_gap:
            notes.append(f"cand @{points[c[0]].t - t_start:.2f}s dropped:"
                         f" within {config.MIN_SEGMENT_MS}ms of path end")
        else:
            survivors.append(c)
    kept = []
    for cand in survivors:
        if kept and points[cand[0]].t - points[kept[-1][0]].t < min_gap:
            if cand[1] > kept[-1][1]:
                notes.append(f"cand @{points[kept[-1][0]].t - t_start:.2f}s dropped:"
                             f" <{config.MIN_SEGMENT_MS}ms before stronger cand")
                kept[-1] = cand
            else:
                notes.append(f"cand @{points[cand[0]].t - t_start:.2f}s dropped:"
                             f" <{config.MIN_SEGMENT_MS}ms after previous, weaker")
        else:
            kept.append(cand)
    return [c[0] for c in kept]


def _classify(points: list[PathPoint], attack_dir: int) -> tuple:
    """(action, evidence dict) — per-class weighted feature scores, argmax wins."""
    feats, raw = features.extract(points, attack_dir)
    scores, probs, action, confidence = features.score(feats)
    if action == "CARRY":
        rule = f"carry (default, margin {confidence:.2f})"
    else:
        _, weights = features.class_weights(action)
        top = max(features.FEATURES, key=lambda f: weights[f] * feats[f])
        rule = (f"{action.lower()}: {top} {weights[top] * feats[top]:+.1f}"
                f" (p={probs[action]:.2f})")
    return action, {
        "action_geo": action, "rule": rule,
        "forward_px": round(raw["fwd_m"] * config.PX_PER_M, 1),
        "lateral_px": round(raw["lat_m"] * config.PX_PER_M, 1),
        "duration_s": raw["dur_s"], "speed_mps": raw["speed_net"],
        "n_points": len(points), "attack_dir": attack_dir,
        "features": {f: round(feats[f], 3) for f in features.FEATURES},
        "raw": raw,
        "scores": {c: round(s, 2) for c, s in scores.items()},
        "probs": {c: round(p, 3) for c, p in probs.items()},
        "confidence": round(confidence, 3),
    }


def _segment_at(segments, t, grace_s):
    """Segment whose window contains t; else one that ended within grace_s before t."""
    for seg in segments:
        if seg.start_t <= t <= seg.end_t:
            return seg
    late = [s for s in segments if 0 < t - s.end_t <= grace_s]
    return late[-1] if late else None


def _digit_bursts(taps):
    """Group sequential digit taps within DIGIT_BURST_MS into (number, first_t)."""
    out, digits, t0, last_t = [], "", 0.0, None
    for tap in taps:
        if not tap.key.isdigit():
            continue
        if digits and (tap.t - last_t) * 1000 > config.DIGIT_BURST_MS:
            out.append((int(digits), t0))
            digits = ""
        if not digits:
            t0 = tap.t
        digits += tap.key
        last_t = tap.t
    if digits:
        out.append((int(digits), t0))
    return out


def apply_taps(segments: list[Segment], taps, shift_intervals) -> list[Segment]:
    """Layer keyboard annotations onto geometrically-detected segments.

    Taps never move boundaries (Decision 10) — they relabel, flag, and
    attribute. Unrecognized keys in the log are ignored, so callers can feed
    the whole per-chain tap log straight in.
    """
    if not segments:
        return segments
    log = last_debug.setdefault("taps", [])  # harmless on standalone calls
    t0 = segments[0].start_t
    grace = config.TYPE_HINT_GRACE_MS / 1000

    for tap in taps:
        if tap.key in config.TYPE_HINT_KEYS:
            seg = _segment_at(segments, tap.t, grace)
            if seg:
                log.append(f"{tap.t - t0:.2f}s '{tap.key}' hint -> "
                           f"seg{segments.index(seg)} {seg.action}->"
                           f"{config.TYPE_HINT_KEYS[tap.key]}")
                seg.action = config.TYPE_HINT_KEYS[tap.key]
            else:
                log.append(f"{tap.t - t0:.2f}s '{tap.key}' hint -> "
                           "no segment within grace")
        elif tap.key == config.LINEBREAK_KEY:
            seg = _segment_at(segments, tap.t, grace)
            if seg and seg.action == "CARRY":
                seg.linebreak = True
                log.append(f"{tap.t - t0:.2f}s 'l' -> seg{segments.index(seg)} linebreak")
            elif seg:
                log.append(f"{tap.t - t0:.2f}s 'l' -> ignored: "
                           f"seg{segments.index(seg)} is {seg.action}")
            else:
                log.append(f"{tap.t - t0:.2f}s 'l' -> no segment within grace")

    # player numbers: nearest boundary decides segment and role (Decision 11)
    boundaries = [segments[0].start_t] + [s.end_t for s in segments]
    for number, t in _digit_bursts(taps):
        b = min(boundaries, key=lambda bt: abs(bt - t))
        if t >= b:  # just after a boundary: actor starting the next action
            following = [s for s in segments if s.start_t == b]
            seg, role = (following[0], "start") if following else (segments[-1], "end")
        else:       # just before: whoever ended the previous action
            ending = [s for s in segments if s.end_t == b]
            seg, role = (ending[-1], "end") if ending else (segments[0], "start")
        seg.players.append(PlayerTag(number=number, role=role, at_ts=t))
        log.append(f"{t - t0:.2f}s digit-burst {number} -> boundary @{b - t0:.2f}s "
                   f"({'after' if t >= b else 'before'}) -> "
                   f"seg{segments.index(seg)} {role}")

    for seg in segments:
        if seg.action != "PASS":
            continue
        for s, e in shift_intervals:
            if s < seg.end_t and e > seg.start_t:
                seg.intercepted = True
                log.append(f"shift {s - t0:.2f}-{e - t0:.2f}s overlaps "
                           f"seg{segments.index(seg)} PASS -> intercepted")
                break
    return segments


def segment_path(points: list[PathPoint], attack_dir: int) -> list[Segment]:
    """Split one traced path into classified Segments. attack_dir: +1 = +x, -1 = -x."""
    global last_debug
    d: dict = {"rejected": None}
    last_debug = d
    if len(points) < 3:
        d["rejected"] = f"too few points ({len(points)} < 3)"
        return []
    net_px = math.hypot(points[-1].x - points[0].x, points[-1].y - points[0].y)
    duration = points[-1].t - points[0].t
    d.update(t0=points[0].t, n_points=len(points), duration_s=round(duration, 3),
             hz=round((len(points) - 1) / duration, 1) if duration > 0 else 0.0,
             net_px=round(net_px, 1))
    if net_px < config.MIN_MOVEMENT_PX:
        d["rejected"] = f"net movement {net_px:.1f}px < {config.MIN_MOVEMENT_PX}px"
        return []
    smoothed = _smooth(points)
    candidates, boundary_info = _boundary_candidates(smoothed)
    notes: list[str] = []
    boundaries = _pick_boundaries(smoothed, candidates, notes)
    t0 = points[0].t
    d["boundary"] = boundary_info
    d["candidates"] = [{"i": i, "t": smoothed[i].t - t0, "x": round(smoothed[i].x, 1),
                        "y": round(smoothed[i].y, 1), "angle": round(angle, 1),
                        "ratio": round(ratio, 2), "strength": round(score, 2),
                        "score": round(score, 2)}
                       for i, score, angle, ratio in candidates]
    d["picked"] = [{"i": b, "t": smoothed[b].t - t0, "x": round(smoothed[b].x, 1),
                    "y": round(smoothed[b].y, 1)} for b in boundaries]
    d["boundary_notes"] = notes
    d["segments"] = []
    slices = []
    prev = 0
    for b in boundaries:
        slices.append(points[prev:b + 1])
        prev = b
    slices.append(points[prev:])

    segments, direction = [], attack_dir
    for sl in slices:
        action, evidence = _classify(sl, direction)
        d["segments"].append(evidence)
        segments.append(Segment(action=action, points=sl,
                                scores=evidence["scores"],
                                confidence=evidence["confidence"]))
        if action == "KICK":
            direction = -direction  # receiver attacks the other way
    return segments
