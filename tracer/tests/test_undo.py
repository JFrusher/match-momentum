"""Undo the last committed chain.

One level only: the snapshot is taken inside end_chain, so undo_last() rewinds
exactly what end_chain touched — the events it appended (including any score
tapped mid-chain), the possession it inferred, and the end reason it set.
"""

from tracer import config
from tracer.events import compute_score
from tracer.match_state import MatchState

PX = config.PX_PER_M
LEFT = config.IN_GOAL_DEPTH_M * PX


def _trace(m, x0_m, x1_m, t0, dur, n=60):
    m.mouse_down(LEFT + x0_m * PX, 280, t0)
    for i in range(1, n + 1):
        m.mouse_move(LEFT + (x0_m + (x1_m - x0_m) * i / n) * PX, 280,
                     t0 + dur * i / n)
    return t0 + dur


def test_undo_restores_events_and_possession():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    t = _trace(m, 10, 22, 100.0, 3.0)
    m.key_down("a", t)
    assert m.events and m.possession == "away"
    m.undo_last()
    assert m.events == []
    assert m.possession == "home"
    assert m.last_end_reason is None


def test_undo_removes_a_score_tapped_during_the_chain():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    t = _trace(m, 10, 22, 100.0, 3.0)
    m.key_down("t", t)                 # try, logged before the chain commits
    m.key_down("a", t + 0.01)
    assert compute_score(m.events, m.team_names) == {"home": 5, "away": 0}
    m.undo_last()
    assert compute_score(m.events, m.team_names) == {"home": 0, "away": 0}


def test_undo_reverts_only_the_last_chain():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    t = _trace(m, 10, 22, 100.0, 3.0)
    m.key_down("a", t)
    after_first, poss_after_first = list(m.events), m.possession
    t2 = _trace(m, 40, 52, t + 1.0, 3.0)
    m.key_down("a", t2)
    assert len(m.events) > len(after_first)
    m.undo_last()
    assert m.events == after_first
    assert m.possession == poss_after_first


def test_undo_is_single_level():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    t = _trace(m, 10, 22, 100.0, 3.0)
    m.key_down("a", t)
    after_first = list(m.events)
    t2 = _trace(m, 40, 52, t + 1.0, 3.0)
    m.key_down("a", t2)
    m.undo_last()
    m.undo_last()                      # nothing further to rewind
    assert m.events == after_first


def test_undo_with_nothing_committed_is_a_noop():
    m = MatchState("ENG", "WAL")
    m.undo_last()
    assert m.events == []
    assert m.possession == "home"
