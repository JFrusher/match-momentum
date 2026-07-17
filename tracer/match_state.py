"""Match/clock/possession orchestration + tap dispatch. Pure (no NiceGUI).

app.py wires UI events in and reads state back; optional callbacks
(on_commit, on_change) let the UI react without this module importing it.
"""

import time
from typing import Optional

from . import config, segmentation
from .continuity import ChainRecorder, PlayChain, new_chain_id
from .events import assign_teams, chain_to_events
from .geometry import PitchCalibration
from .keystate import KeyState
from .segmentation import apply_taps, segment_path


def _other(team):
    return "away" if team == "home" else "home"


class MatchClock:
    """start/pause wall clock; time.monotonic()-based, rehydrates paused."""

    def __init__(self, base_seconds: float = 0.0):
        self.base_seconds = base_seconds
        self.running = False
        self._started_at: Optional[float] = None

    def start(self, t: Optional[float] = None):
        if not self.running:
            self._started_at = time.monotonic() if t is None else t
            self.running = True

    def pause(self, t: Optional[float] = None):
        if self.running:
            now = time.monotonic() if t is None else t
            self.base_seconds += now - self._started_at
            self.running = False
            self._started_at = None

    def toggle(self):
        self.pause() if self.running else self.start()

    def seconds(self, t: Optional[float] = None) -> float:
        now = time.monotonic() if t is None else t
        return self.base_seconds + (now - self._started_at if self.running else 0.0)

    def minute(self, t: Optional[float] = None) -> float:
        return self.seconds(t) / 60


class MatchState:
    def __init__(self, home: str, away: str, attack_dir_home: int = 1,
                 possession: str = "home", cal: Optional[PitchCalibration] = None):
        self.team_names = {"home": home, "away": away}
        self.possession = possession
        self.attack_dir_home = attack_dir_home
        self.cal = cal or PitchCalibration()
        self.clock = MatchClock()
        self.keystate = KeyState()
        self.recorder = ChainRecorder()
        self.events: list[dict] = []
        self._chain_start_minute: Optional[float] = None
        self._pending_try = None  # (team_key, deadline_monotonic)
        self.on_commit = None     # callback(chain) after a chain is committed
        self.on_change = None     # callback() after any state change
        # dev-panel evidence: last end_chain attempt, accepted or rejected
        self.chain_seq = 0
        self.last_debug: dict = {}
        self.last_raw: Optional[dict] = None
        self.last_chain: Optional[PlayChain] = None

    # --- mouse -----------------------------------------------------------
    def mouse_down(self, x, y, t):
        self.recorder.start(x, y, t)
        self._chain_start_minute = self.clock.minute(t)

    def mouse_move(self, x, y, t):
        self.recorder.extend(x, y, t)

    def mouse_up(self, t):
        """Fallback chain-end: primary flow is the A/Space tap."""
        if self.recorder.active:
            self.end_chain(t)

    # --- keys --------------------------------------------------------------
    def key_down(self, key: str, t: float):
        k = key.lower()
        if k in config.END_CHAIN_KEYS:
            if self.recorder.active:
                self.end_chain(t)
        elif k in config.TEAM_KEYS:
            self.possession = config.TEAM_KEYS[k]
            self._changed()
        elif k in config.DISCRETE_EVENT_KEYS:
            self._discrete_event(k, t)
        elif k in config.CONVERSION_KEYS:
            self._conversion(k, t)
        else:
            self.keystate.key_down(key, t)

    def key_up(self, key: str, t: float):
        self.keystate.key_up(key, t)

    # --- chain lifecycle ---------------------------------------------------
    def end_chain(self, t: float) -> Optional[PlayChain]:
        points = self.recorder.finish()
        taps = list(self.keystate.taps)
        intervals = self.keystate.intervals_until(t)
        self.keystate.clear_chain()
        self.chain_seq += 1
        self.last_raw = {"points": [[p.x, p.y, p.t] for p in points],
                         "taps": [[tp.key, tp.t] for tp in taps],
                         "shift": [list(iv) for iv in intervals],
                         "possession": self.possession,
                         "attack_dir_home": self.attack_dir_home}
        attack_dir = (self.attack_dir_home if self.possession == "home"
                      else -self.attack_dir_home)
        segments = segment_path(points, attack_dir)
        self.last_debug = segmentation.last_debug  # by ref; apply_taps appends
        if not segments:
            self.last_chain = None
            return None
        apply_taps(segments, taps, intervals)
        chain = PlayChain(
            chain_id=new_chain_id(),
            team=self.possession,
            start_minute=self._chain_start_minute
            if self._chain_start_minute is not None else self.clock.minute(t),
            segments=segments,
        )
        self.last_chain = chain
        self.possession = assign_teams(segments, chain.team)
        self.events.extend(chain_to_events(
            chain, self.team_names, self.attack_dir_home, self.cal))
        self._changed()
        if self.on_commit:
            self.on_commit(chain)
        return chain

    # --- discrete events -----------------------------------------------------
    def _discrete_event(self, k: str, t: float):
        etype = config.DISCRETE_EVENT_KEYS[k]
        minute = round(self.clock.minute(t), 1)
        if etype == "turnover_won":
            team_key = _other(self.possession)
            self.possession = team_key
        elif etype == "sin_bin":
            # ponytail: assumes the defending side got binned; flip in review if not
            team_key = _other(self.possession)
        else:
            team_key = self.possession
        name = self.team_names[team_key]
        ev = {"type": etype, "team": name, "minute": minute}
        if etype == "try":
            ev["label"] = f"{name} try {int(minute)}'"
            self._pending_try = (team_key, t + config.CONVERSION_LISTEN_S)
        elif etype == "sin_bin":
            ev["label"] = f"{name} yellow {int(minute)}'"
        self.events.append(ev)
        self._changed()

    def _conversion(self, k: str, t: float):
        if not self._pending_try or t > self._pending_try[1]:
            return
        team_key, _ = self._pending_try
        self._pending_try = None
        self.events.append({
            "type": config.CONVERSION_KEYS[k],
            "team": self.team_names[team_key],
            "minute": round(self.clock.minute(t), 1),
        })
        self._changed()

    # --- misc ------------------------------------------------------------------
    def halftime_flip(self):
        self.attack_dir_home = -self.attack_dir_home
        self._changed()

    def _changed(self):
        if self.on_change:
            self.on_change()

    # --- persistence shape -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "teams": self.team_names,
            "possession": self.possession,
            "attack_dir_home": self.attack_dir_home,
            "clock_seconds": self.clock.seconds(),
            "events": self.events,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MatchState":
        m = cls(d["teams"]["home"], d["teams"]["away"],
                attack_dir_home=d["attack_dir_home"], possession=d["possession"])
        m.clock = MatchClock(base_seconds=d["clock_seconds"])  # rehydrates paused
        m.events = list(d["events"])
        return m
