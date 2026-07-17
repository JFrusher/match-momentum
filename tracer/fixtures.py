"""Emulated noisy input: fixture corpus + instant-injection harness.

noisy_path() turns waypoint scripts (metres) into human-ish pixel traces:
speed variation, hand-tremor wobble, corner rounding, sampling jitter —
deterministic per seed. inject_raw()/inject() fire raw inputs through a real
MatchState exactly as the live app would (all logic uses passed-in t, never
wall clock, so instant injection is faithful). check() compares outcomes
against a scenario's `expect` dict.

Consumed by tests/test_corpus.py, sweep.py, and the dev panel's replay.
Pure Python — no NiceGUI imports.
"""

import functools
import json
import math
import random
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .continuity import PathPoint
from .match_state import MatchState

PX = config.PX_PER_M
TRACES_DIR = Path(__file__).parent / "tests" / "traces"  # committed regressions
DEV_TRACES = Path(__file__).parent / "dev_traces"        # scratch, gitignored


def noisy_path(waypoints, durations, seed, hz=60, wobble_px=2.0,
               speed_var=0.2, jitter_ms=3.0, smooth_pts=3):
    """Human-ish trace of the waypoint script, in pixels, t relative from ~0."""
    rng = random.Random(seed)
    # two hand-tremor sines per axis, applied over absolute time. Physiological
    # tremor is 5-9 Hz: fast enough that the recognizer's 150ms heading windows
    # average it out, exactly like a real hand. Slower wobble (<4 Hz) reads as
    # deliberate heading change and would test the noise, not the recognizer.
    tremor = [[(wobble_px * rng.uniform(0.3, 0.7), rng.uniform(5.0, 9.0),
                rng.uniform(0, 2 * math.pi)) for _ in range(2)] for _ in range(2)]

    def wobble(axis, t):
        return sum(a * math.sin(2 * math.pi * f * t + ph)
                   for a, f, ph in tremor[axis])

    raw = []  # (x_px, y_px, t)
    t_leg = 0.0
    for (x0, y0), (x1, y1), dur in zip(waypoints, waypoints[1:], durations):
        n = max(2, int(dur * hz))
        phase = rng.uniform(0, 2 * math.pi)
        start = 1 if raw else 0  # skip duplicating the shared corner point
        for i in range(start, n + 1):
            f = i / n
            # integral of speed multiplier 1 + speed_var*sin(2*pi*f + phase):
            # endpoints preserved, monotonic for speed_var < 1
            fw = f + speed_var / (2 * math.pi) * (
                math.cos(phase) - math.cos(2 * math.pi * f + phase))
            t = t_leg + dur * f
            raw.append(((x0 + (x1 - x0) * fw) * PX + wobble(0, t),
                        (y0 + (y1 - y0) * fw) * PX + wobble(1, t), t))
        t_leg += dur

    # corner rounding (position moving-average) + sampling jitter on t
    half = smooth_pts // 2
    pts, prev_t = [], -1.0
    for i in range(len(raw)):
        win = raw[max(0, i - half):i + half + 1]
        t = raw[i][2] + rng.uniform(-jitter_ms, jitter_ms) / 1000
        t = max(t, prev_t + 1e-4)  # strictly increasing
        pts.append(PathPoint(sum(p[0] for p in win) / len(win),
                             sum(p[1] for p in win) / len(win), t))
        prev_t = t
    return pts


@dataclass(frozen=True)
class Scenario:
    name: str
    waypoints: tuple = ()   # ((x_m, y_m), ...) metre coords, mid-pitch y≈35
    durations: tuple = ()   # per-leg seconds, len == len(waypoints) - 1
    taps: tuple = ()        # ((rel_t_s, key), ...) fed to MatchState.key_down
    shift: tuple = ()       # ((rel_t0, rel_t1), ...) held-Shift intervals
    expect: dict = field(default_factory=dict)
    attack_dir: int = 1
    possession: str = "home"
    end: str = "a"          # "a" | "mouseup" — how the chain is ended

    @property
    def seed(self) -> int:
        return zlib.crc32(self.name.encode())  # stable across processes


SCENARIOS: dict[str, Scenario] = {}


def _sc(name, **kw):
    SCENARIOS[name] = Scenario(name=name, **kw)


# --- corpus ----------------------------------------------------------------
# Realistic tracing speeds: carry 2-8 m/s, pass a 0.45-0.6s flick, kick
# 35-40m in ~0.5s. Legs >= 0.45s (> MIN_SEGMENT_MS); corner angles clear of
# ANGLE_THRESHOLD_DEG on the intended side.
CS = dict(waypoints=((10, 35), (22, 35)), durations=(3.0,))       # 1-seg carry
CPC = dict(waypoints=((10, 35), (20, 35), (19, 43), (31, 43)),    # boundary
           durations=(2.5, 0.45, 3.0))                            # ~2.5s, ~2.95s

# geometry: every movement shape the recognizer must get right
_sc("carry_straight", **CS, expect={"actions": ["CARRY"]})
_sc("carry_diagonal", waypoints=((10, 30), (20, 38)), durations=(2.5,),
    expect={"actions": ["CARRY"]})                    # lat 8 < 1.2 x fwd 10
_sc("carry_weave", waypoints=((10, 35), (16, 34), (22, 36), (28, 35)),
    durations=(1.5, 1.5, 1.5),                        # ~28 deg turns: no split
    expect={"forbid": {"PASS", "KICK"}, "n_segments": (1, 2)})
_sc("pass_backward", waypoints=((40, 35), (33, 37)), durations=(0.5,),
    expect={"actions": ["PASS"]})
_sc("pass_lateral", waypoints=((40, 35), (41, 45)), durations=(0.5,),
    expect={"actions": ["PASS"]})
_sc("pass_ratio_edge", waypoints=((40, 35), (46, 45)), durations=(0.6,),
    expect={"actions": ["PASS"]})                     # lat 10 > 1.2 x fwd 6
_sc("carry_ratio_edge", waypoints=((40, 35), (50, 45)), durations=(1.8,),
    expect={"actions": ["CARRY"]})                    # lat 10 < 1.2 x fwd 10
_sc("kick_long", waypoints=((30, 35), (68, 33)), durations=(0.55,),
    expect={"actions": ["KICK"]})
_sc("kick_return", waypoints=((30, 35), (62, 35), (52, 34)),
    durations=(0.5, 2.5),                             # receiver runs it back
    expect={"actions": ["KICK", "CARRY"]})
_sc("carry_pass_carry", **CPC, expect={"actions": ["CARRY", "PASS", "CARRY"]})
_sc("carry_pass_carry_kick",
    waypoints=CPC["waypoints"] + ((71, 38),), durations=CPC["durations"] + (0.5,),
    expect={"actions": ["CARRY", "PASS", "CARRY", "KICK"]})
_sc("phase_chain_5",
    waypoints=((10, 35), (18, 35), (17, 42), (26, 42), (25, 50), (34, 50)),
    durations=(2.0, 0.45, 2.2, 0.45, 2.2),
    expect={"actions": ["CARRY", "PASS", "CARRY", "PASS", "CARRY"]})
_sc("switchback_cut", waypoints=((10, 35), (18, 35), (16.5, 35), (26, 35)),
    durations=(2.0, 0.3, 2.0),                        # 300ms agility cut
    expect={"forbid": {"PASS", "KICK"}, "n_segments": (1, 3)})
_sc("hesitation_carry", waypoints=((10, 35), (16, 35), (16.8, 35), (24, 35)),
    durations=(1.5, 0.6, 2.0),                        # slow-down, no turn
    expect={"forbid": {"PASS", "KICK"}, "n_segments": (1, 3)})
_sc("speed_burst_carry", waypoints=((10, 35), (16, 35), (40, 35)),
    durations=(2.0, 2.0),                             # 12 m/s but 2s: not a kick
    expect={"forbid": {"PASS", "KICK"}})
_sc("accidental_twitch", waypoints=((30, 35), (30.3, 35)), durations=(0.2,),
    expect={"rejected": True})
_sc("mirrored_attack", attack_dir=-1,
    waypoints=((90, 35), (80, 35), (81, 43), (69, 43)),
    durations=(2.5, 0.45, 3.0),
    expect={"actions": ["CARRY", "PASS", "CARRY"]})
_sc("away_possession_chain", possession="away",
    waypoints=((60, 35), (48, 35)), durations=(3.0,),
    expect={"actions": ["CARRY"], "possession_after": "away"})

# taps & keys: digits, hints, linebreak, interception
_sc("digit_start_actor", **CS, taps=((0.15, "9"),),
    expect={"actions": ["CARRY"], "players": [(0, 9, "start")]})
_sc("digit_two_digit", **CS, taps=((0.15, "1"), (0.27, "0")),
    expect={"players": [(0, 10, "start")]})
_sc("digit_burst_split", **CS, taps=((0.15, "1"), (0.70, "0")),
    # 550ms gap > DIGIT_BURST_MS: splits into 1 and 0 — the documented sharp edge
    expect={"players": [(0, 1, "start"), (0, 0, "start")]})
_sc("digit_before_boundary", **CPC, taps=((2.30, "1"), (2.42, "2")),
    expect={"players": [(0, 12, "end")]})
_sc("digit_after_boundary", **CPC, taps=((2.62, "7"),),
    expect={"players": [(1, 7, "start")]})
_sc("digit_end_of_chain", **CS, taps=((3.1, "8"),),
    expect={"players": [(0, 8, "end")]})
_sc("hint_k", **CS, taps=((1.0, "k"),),
    # relabel does NOT re-run the kick direction flip (geometry already ran)
    expect={"actions": ["KICK"]})
_sc("hint_p", **CS, taps=((1.0, "p"),), expect={"actions": ["PASS"]})
_sc("hint_r", waypoints=((40, 35), (33, 37)), durations=(0.5,),
    taps=((0.3, "r"),),                               # intercept-return correction
    expect={"actions": ["CARRY"]})
_sc("hint_grace_late", **CS, taps=((3.15, "k"),),
    expect={"actions": ["KICK"]})                     # within 250ms grace
_sc("hint_beyond_grace", **CS, taps=((3.35, "k"),),
    expect={"actions": ["CARRY"]})                    # 350ms > grace: ignored
_sc("linebreak_carry", **CS, taps=((1.5, "l"),), expect={"linebreaks": [0]})
_sc("linebreak_pass_ignored", waypoints=((40, 35), (33, 37)), durations=(0.5,),
    taps=((0.25, "l"),),
    expect={"actions": ["PASS"], "linebreaks": []})   # L only applies to CARRY
_sc("shift_intercept_pass", **CPC, shift=((2.55, 2.90),),
    expect={"intercepted": [1], "possession_after": "away",
            "event_types": ["phase_sequence", "phase_sequence", "turnover_won"]})
_sc("shift_during_carry_only", **CPC, shift=((0.5, 1.5),),
    expect={"intercepted": [], "possession_after": "home"})

# state-level: possession keys, kick flips, discrete events, fallback end
_sc("team_key_then_chain", taps=((-0.2, "x"),),       # X tapped before the trace
    waypoints=((60, 35), (48, 35)), durations=(3.0,),
    expect={"actions": ["CARRY"], "possession_after": "away"})
_sc("kick_flips_possession", waypoints=((10, 35), (20, 35), (60, 35)),
    durations=(2.5, 0.5),
    expect={"actions": ["CARRY", "KICK"], "possession_after": "away",
            "event_types": ["phase_sequence"]})
_sc("kick_tennis",
    waypoints=((30, 35), (62, 35), (57, 35), (25, 34), (30, 34)),
    durations=(0.5, 1.2, 0.5, 1.5),                   # kick, return, kick back
    expect={"actions": ["KICK", "CARRY", "KICK", "CARRY"],
            "possession_after": "home",
            "event_types": ["phase_sequence"] * 3})
_sc("discrete_try_conversion", taps=((0.0, "t"), (5.0, "c")),
    expect={"event_types": ["try", "conversion"]})
_sc("discrete_all_events",
    taps=((0.0, "t"), (5.0, "n"), (10.0, "g"), (15.0, "v"), (20.0, "b")),
    expect={"event_types": ["try", "penalty_kick", "drop_goal",
                            "turnover_won", "sin_bin"],
            "possession_after": "away"})
_sc("mouseup_fallback_end", **CS, end="mouseup",
    expect={"actions": ["CARRY"], "event_types": ["phase_sequence"]})


# --- harness ---------------------------------------------------------------
def inject_raw(match, points, taps=(), shift=(), t0=0.0, end="a"):
    """Fire raw inputs into a MatchState instantly, merged in timestamp order.

    points: [[x, y, t_rel], ...]; taps: [[key, t_rel], ...];
    shift: [[t_down, t_up], ...] — exactly the saved-trace JSON shape.
    Ends the chain (key 'a' or mouse_up) just after the last input.
    Returns match.last_chain.
    """
    stream = []  # (t, kind, payload); kind: 0=down 1=move 2=keydown 3=keyup
    for i, (x, y, t) in enumerate(points):
        stream.append((t, 0 if i == 0 else 1, (x, y)))
    for key, t in taps:
        stream.append((t, 2, key))
    for t_down, t_up in shift:
        stream.append((t_down, 2, "shift"))
        stream.append((t_up, 3, "shift"))
    stream.sort(key=lambda ev: (ev[0], ev[1]))
    for t, kind, payload in stream:
        if kind == 0:
            match.mouse_down(payload[0], payload[1], t0 + t)
        elif kind == 1:
            match.mouse_move(payload[0], payload[1], t0 + t)
        elif kind == 2:
            match.key_down(payload, t0 + t)
        else:
            match.key_up(payload, t0 + t)
    if points:
        t_end = t0 + max(ev[0] for ev in stream) + 0.05
        if end == "a":
            match.key_down("a", t_end)
        else:
            match.mouse_up(t_end)
    return match.last_chain


def inject(match, sc: Scenario, t0=0.0):
    """Run a scenario's synthetic inputs; the caller owns match setup."""
    pts = noisy_path(sc.waypoints, sc.durations, sc.seed) if sc.waypoints else []
    return inject_raw(match, [[p.x, p.y, p.t] for p in pts],
                      taps=[[k, t] for t, k in sc.taps],
                      shift=sc.shift, t0=t0, end=sc.end)


def check(match, expect: dict) -> list[str]:
    """Compare outcome against the expect vocabulary; [] = pass."""
    segs = match.last_chain.segments if match.last_chain else []
    got_actions = [s.action for s in segs]
    out = []

    def bad(key, want, got):
        out.append(f"{key}: expected {want}, got {got}")

    if "actions" in expect and got_actions != expect["actions"]:
        bad("actions", expect["actions"], got_actions or "no chain")
    if "forbid" in expect:
        hit = [a for a in got_actions if a in expect["forbid"]]
        if hit:
            bad("forbid", f"none of {sorted(expect['forbid'])}", got_actions)
    if "n_segments" in expect:
        want = expect["n_segments"]
        lo, hi = (want, want) if isinstance(want, int) else want
        if not lo <= len(segs) <= hi:
            bad("n_segments", want, len(segs))
    if expect.get("rejected"):
        if match.last_chain is not None or not match.last_debug.get("rejected"):
            bad("rejected", "rejected chain", got_actions or "no rejection reason")
    if "linebreaks" in expect:
        got = [i for i, s in enumerate(segs) if s.linebreak]
        if got != expect["linebreaks"]:
            bad("linebreaks", expect["linebreaks"], got)
    if "intercepted" in expect:
        got = [i for i, s in enumerate(segs) if s.intercepted]
        if got != expect["intercepted"]:
            bad("intercepted", expect["intercepted"], got)
    if "players" in expect:
        got = [(i, p.number, p.role) for i, s in enumerate(segs) for p in s.players]
        want = [tuple(w) for w in expect["players"]]
        if got != want:
            bad("players", want, got)
    if "possession_after" in expect and match.possession != expect["possession_after"]:
        bad("possession_after", expect["possession_after"], match.possession)
    if "event_types" in expect:
        got = [e["type"] for e in match.events]
        if got != expect["event_types"]:
            bad("event_types", expect["event_types"], got)
    return out


def run(sc: Scenario) -> list[str]:
    """Fresh MatchState -> inject -> check. The uniform corpus runner."""
    m = MatchState("HOME", "AWAY", attack_dir_home=sc.attack_dir,
                   possession=sc.possession)
    m.clock.start(t=0.0)
    inject(m, sc)
    return check(m, sc.expect)


def run_trace_file(path) -> list[str]:
    """Saved-trace JSON -> fresh MatchState -> inject_raw -> check."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    m = MatchState("HOME", "AWAY",
                   attack_dir_home=d.get("attack_dir_home", 1),
                   possession=d.get("possession", "home"))
    m.clock.start(t=0.0)
    inject_raw(m, d["points"], d.get("taps", ()), d.get("shift", ()))
    return check(m, d.get("expect", {}))


def iter_cases():
    """(name, runner) per scenario + committed real-trace regressions."""
    cases = [(name, functools.partial(run, sc)) for name, sc in SCENARIOS.items()]
    if TRACES_DIR.is_dir():
        cases += [(f"trace:{f.stem}", functools.partial(run_trace_file, f))
                  for f in sorted(TRACES_DIR.glob("*.json"))]
    return cases
