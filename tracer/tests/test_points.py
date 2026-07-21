"""Scoreboard: compute_score sums point events into a home/away tally."""

from tracer.events import compute_score

NAMES = {"home": "ENG", "away": "WAL"}


def test_empty():
    assert compute_score([], NAMES) == {"home": 0, "away": 0}


def test_union_values_by_team():
    events = [
        {"type": "try", "team": "ENG"},          # 5
        {"type": "conversion", "team": "ENG"},   # 2
        {"type": "penalty_kick", "team": "WAL"}, # 3
        {"type": "drop_goal", "team": "ENG"},    # 3
    ]
    assert compute_score(events, NAMES) == {"home": 10, "away": 3}


def test_ignores_nonscoring_and_missed():
    events = [
        {"type": "try", "team": "ENG"},
        {"type": "conversion_missed", "team": "ENG"},
        {"type": "turnover_won", "team": "WAL"},
        {"type": "phase_sequence", "team": "WAL", "metres_gained": 20},
        {"type": "sin_bin", "team": "ENG"},
    ]
    assert compute_score(events, NAMES) == {"home": 5, "away": 0}


def test_unknown_team_name_contributes_nothing():
    assert compute_score([{"type": "try", "team": "SCO"}], NAMES) == \
        {"home": 0, "away": 0}
