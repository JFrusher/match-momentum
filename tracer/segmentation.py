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

from . import config
from .continuity import PathPoint, PlayerTag, Segment


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
    """(index, strength) where heading or speed changes sharply."""
    out = []
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
        if angle > config.ANGLE_THRESHOLD_DEG or ratio > config.SPEED_RATIO_THRESHOLD:
            out.append((i, angle / config.ANGLE_THRESHOLD_DEG
                        + ratio / config.SPEED_RATIO_THRESHOLD))
    return out


def _pick_boundaries(points, candidates):
    """Collapse candidate runs to one boundary each, enforce min segment length."""
    if not candidates:
        return []
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

    # drop boundaries hugging the path's ends, then thin to MIN_SEGMENT_MS spacing
    min_gap = config.MIN_SEGMENT_MS / 1000
    t_start, t_end = points[0].t, points[-1].t
    picked = [c for c in picked
              if points[c[0]].t - t_start >= min_gap and t_end - points[c[0]].t >= min_gap]
    kept = []
    for cand in picked:
        if kept and points[cand[0]].t - points[kept[-1][0]].t < min_gap:
            if cand[1] > kept[-1][1]:
                kept[-1] = cand
        else:
            kept.append(cand)
    return [i for i, _ in kept]


def _classify(points: list[PathPoint], attack_dir: int) -> str:
    start, end = points[0], points[-1]
    forward = attack_dir * (end.x - start.x)
    lateral = end.y - start.y
    duration = end.t - start.t
    if forward < 0 or abs(lateral) > abs(forward) * config.LATERAL_RATIO:
        return "PASS"
    speed_mps = (math.hypot(end.x - start.x, lateral) / duration / config.PX_PER_M
                 if duration > 0 else 0.0)
    if speed_mps > config.FAST_SPEED_MPS and duration * 1000 < config.SHORT_DURATION_MS:
        return "KICK"
    return "CARRY"


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
    grace = config.TYPE_HINT_GRACE_MS / 1000

    for tap in taps:
        if tap.key in config.TYPE_HINT_KEYS:
            seg = _segment_at(segments, tap.t, grace)
            if seg:
                seg.action = config.TYPE_HINT_KEYS[tap.key]
        elif tap.key == config.LINEBREAK_KEY:
            seg = _segment_at(segments, tap.t, grace)
            if seg and seg.action == "CARRY":
                seg.linebreak = True

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

    for seg in segments:
        if seg.action == "PASS" and any(
                s < seg.end_t and e > seg.start_t for s, e in shift_intervals):
            seg.intercepted = True
    return segments


def segment_path(points: list[PathPoint], attack_dir: int) -> list[Segment]:
    """Split one traced path into classified Segments. attack_dir: +1 = +x, -1 = -x."""
    if len(points) < 3:
        return []
    if math.hypot(points[-1].x - points[0].x, points[-1].y - points[0].y) < config.MIN_MOVEMENT_PX:
        return []
    smoothed = _smooth(points)
    boundaries = _pick_boundaries(smoothed, _boundary_candidates(smoothed))
    slices = []
    prev = 0
    for b in boundaries:
        slices.append(points[prev:b + 1])
        prev = b
    slices.append(points[prev:])

    segments, direction = [], attack_dir
    for sl in slices:
        action = _classify(sl, direction)
        segments.append(Segment(action=action, points=sl))
        if action == "KICK":
            direction = -direction  # receiver attacks the other way
    return segments
