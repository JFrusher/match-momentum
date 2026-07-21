"""Match/clock/possession orchestration + tap dispatch. Pure (no NiceGUI).

app.py wires UI events in and reads state back; optional callbacks
(on_commit, on_change) let the UI react without this module importing it.
"""

import time
from typing import Optional

from . import config, segmentation
from .continuity import ChainRecorder, PlayChain, new_chain_id
from .events import (assign_teams, chain_to_events, ChainOrigin, infer_origin,
                     summarise, RESTART_SCORE_TYPES)
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
                 possession: str = "home", cal: Optional[PitchCalibration] = None,
                 team_colors: Optional[dict] = None):
        self.team_names = {"home": home, "away": away}
        self.team_colors = dict(team_colors or config.TEAM_COLORS)
        self.possession = possession
        self.attack_dir_home = attack_dir_home
        self.cal = cal or PitchCalibration()
        self.clock = MatchClock()
        self.keystate = KeyState()
        self.recorder = ChainRecorder()
        self.events: list[dict] = []
        self._chain_start_minute: Optional[float] = None
        self._chain_events_start = 0   # len(events) at chain start, for score detection
        self.last_end_reason: Optional[str] = None  # "kick"/"turnover"/"score"
        self._pending_try = None  # (team_key, deadline_monotonic)
        self._undo = None         # state snapshot taken at mouse_down
        self._precommit = None    # state snapshot taken at commit, for re-classify
        self.last_summary = ""    # one-line commit description for the UI toast
        # how the NEXT possession begins, and whether a penalty option has
        # pre-armed what the next stroke means. Two nullable fields, not a
        # state machine: nothing here can get stuck.
        self.pending_start_reason = "kickoff"
        self.armed_next_action = None
        self.last_origin = None   # ChainOrigin for the chip the UI draws
        self.penalty_option = None
        self._chain_start_team = possession
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
        self._chain_events_start = len(self.events)
        self._chain_start_team = self.possession
        # snapshot here, not in end_chain: taps landing mid-trace (a try, a
        # turnover) already mutated events and possession by the time the
        # chain commits, and undo has to take those back too
        self._undo = (len(self.events), self.possession, self.last_end_reason,
                      self._pending_try, self.pending_start_reason,
                      self.armed_next_action)

    def mouse_move(self, x, y, t):
        self.recorder.extend(x, y, t)

    def mouse_up(self, t):
        """Fallback chain-end: primary flow is the A/Space tap."""
        if self.recorder.active:
            self.end_chain(t)

    # --- keys --------------------------------------------------------------
    def key_down(self, key: str, t: float):
        k = key.lower()
        if k in config.TAPPED_START_REASONS:
            self._tap_origin(k, t)
        elif k in config.END_CHAIN_KEYS:
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
        self._commit_chain(chain)
        return chain

    def _commit_chain(self, chain):
        """Team assignment, origin inference and export for one chain.

        Separate from end_chain so re-classifying a segment can rewind and run
        it again over the same points — the alternative is duplicating the
        whole tail and letting the two copies drift.
        """
        segments = chain.segments
        # Snapshot the pre-commit state so re-classifying can rerun this
        # cleanly. mouse_down's undo snapshot is no use: re-classifying happens
        # via a CLICK, which is itself a mouse_down and overwrites that
        # snapshot with the post-commit state before the handler runs.
        self._precommit = (self._chain_events_start, len(self.events),
                           self.possession, self.last_end_reason,
                           self._pending_try, self.pending_start_reason,
                           self.armed_next_action)
        final_team = assign_teams(segments, chain.team)
        scored_team = self._scored_team_this_chain()
        # the reason this chain BEGAN was decided when the last one ended;
        # capture it before inference overwrites it with the next one
        began_as = self.pending_start_reason
        origin = infer_origin(segments=segments, chain_start_team=chain.team,
                              final_team=final_team, scored_team=scored_team,
                              armed=self.armed_next_action,
                              attack_dir_home=self.attack_dir_home, cal=self.cal)
        self.possession = origin.team
        self.pending_start_reason = origin.reason
        self.last_origin = origin
        self.armed_next_action = None      # one-shot: arming never outlives a stroke
        self.last_end_reason = ("score" if scored_team
                                else "kick" if segments[-1].action == "KICK"
                                else "turnover")
        new_events = chain_to_events(
            chain, self.team_names, self.attack_dir_home, self.cal,
            start_reason=began_as)
        self.events.extend(new_events)
        self.last_summary = summarise(new_events, [s.action for s in segments])
        self._changed()
        if self.on_commit:
            self.on_commit(chain)

    def reclassify_segment(self, i: int):
        """Click a drawn segment to cycle its action, then re-commit the chain.

        Rewind-and-redo rather than patching the emitted events: a changed
        action can flip possession, split the chain differently and change the
        origin, so recomputing is both shorter and the only correct option.
        """
        chain = self.last_chain
        if chain is None or self._precommit is None or not 0 <= i < len(chain.segments):
            return
        order = ("CARRY", "PASS", "KICK")
        seg = chain.segments[i]
        seg.action = order[(order.index(seg.action) + 1) % len(order)]
        (self._chain_events_start, n, self.possession, self.last_end_reason,
         self._pending_try, self.pending_start_reason,
         self.armed_next_action) = self._precommit
        del self.events[n:]
        self._undo = self._precommit[1:]   # the re-committed chain stays undoable
        self._commit_chain(chain)

    def undo_last(self):
        """Rewind the last committed chain. Single level — no undo stack.

        ponytail: one level covers the "I just saw that go wrong" case, which
        is the only one that happens in practice; make _undo a deque if a real
        trace shows multi-step regret.
        """
        if self._undo is None:
            return
        (n, possession, reason, pending_try,
         start_reason, armed) = self._undo
        del self.events[n:]
        self.possession = possession
        self.last_end_reason = reason
        self._pending_try = pending_try
        self.pending_start_reason = start_reason
        self.armed_next_action = armed
        self._undo = None
        self.last_chain = None
        self.last_origin = None
        self.last_summary = ""
        self._changed()

    def _scored_team_this_chain(self) -> Optional[str]:
        """Home/away key if a restart-triggering score was tapped this chain."""
        name_to_key = {v: k for k, v in self.team_names.items()}
        found = None
        for e in self.events[self._chain_events_start:]:
            if e.get("type") in RESTART_SCORE_TYPES:
                found = name_to_key.get(e.get("team"))
        return found

    # --- tapped origins: what geometry can't see ------------------------------
    def _tap_origin(self, k: str, t: float):
        """S (scrum) / F (penalty) — the two set pieces a traced line can't show.

        A knock-on looks exactly like a tackle; a penalty looks like nothing at
        all. Both award against whoever was carrying, which is right most of the
        time — the chip flips the team when it isn't.
        """
        reason = config.TAPPED_START_REASONS[k]
        held_by = self._chain_start_team if self.recorder.active else self.possession
        mark = self._last_point()
        if self.recorder.active:
            self.end_chain(t)              # the tap ends the play as well
        team = _other(held_by)
        self.possession = team
        self.pending_start_reason = reason
        self.last_origin = ChainOrigin(reason, team, mark)
        if reason == "penalty":
            self.events.append({"type": config.PENALTY_WON_TYPE,
                                "team": self.team_names[team],
                                "minute": round(self.clock.minute(t), 1)})
            self.armed_next_action = config.PENALTY_DEFAULT_OPTION
            self.penalty_option = config.PENALTY_DEFAULT_OPTION
        self._changed()

    def choose_penalty_option(self, option: str):
        """Non-blocking: ignoring the chooser leaves the default guess standing."""
        self.penalty_option = option
        self.armed_next_action = ("kick_to_touch" if option == "kick_to_touch"
                                  else None)
        if option == "scrum":
            self.pending_start_reason = "scrum"
        self._changed()

    def flip_origin_team(self):
        """The chip's team badge. Two teams, so wrong is always one click away."""
        o = self.last_origin
        if o is None:
            return
        self.possession = _other(o.team)
        self.last_origin = ChainOrigin(o.reason, self.possession, o.mark,
                                       o.alt_mark)
        self._changed()

    def flip_origin_mark(self):
        """Swap a lineout between its two lawful marks — it bounced, or it didn't."""
        o = self.last_origin
        if o is None or o.alt_mark is None:
            return
        self.last_origin = ChainOrigin(o.reason, o.team, o.alt_mark, o.mark)
        self._changed()

    def _last_point(self):
        """Where the ball was last seen, for anchoring a chip."""
        pts = self.recorder.points or (
            self.last_chain.segments[-1].points if self.last_chain else None)
        return (pts[-1].x, pts[-1].y) if pts else None

    # --- discrete events -----------------------------------------------------
    def _discrete_event(self, k: str, t: float):
        etype = config.DISCRETE_EVENT_KEYS[k]
        minute = round(self.clock.minute(t), 1)
        if etype == "turnover_won":
            team_key = _other(self.possession)
            self.possession = team_key
        elif etype in config.CARD_TYPES:
            # ponytail: assumes the defending side got carded; flip in review if not
            team_key = _other(self.possession)
        else:
            team_key = self.possession
        name = self.team_names[team_key]
        ev = {"type": etype, "team": name, "minute": minute}
        if etype == "try":
            ev["label"] = f"{name} try {int(minute)}'"
            self._pending_try = (team_key, t + config.CONVERSION_LISTEN_S)
        elif etype == "penalty_try":
            # already worth the conversion, so it must NOT arm the C/M listener
            ev["label"] = f"{name} penalty try {int(minute)}'"
        elif etype in config.CARD_TYPES:
            colour = "yellow" if etype == "sin_bin" else "red"
            ev["label"] = f"{name} {colour} {int(minute)}'"
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
            "team_colors": self.team_colors,
            "possession": self.possession,
            "attack_dir_home": self.attack_dir_home,
            "clock_seconds": self.clock.seconds(),
            "events": self.events,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MatchState":
        m = cls(d["teams"]["home"], d["teams"]["away"],
                attack_dir_home=d["attack_dir_home"], possession=d["possession"],
                team_colors=d.get("team_colors"))
        m.clock = MatchClock(base_seconds=d["clock_seconds"])  # rehydrates paused
        m.events = list(d["events"])
        return m
