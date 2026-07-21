"""Scoreboard: compute_score sums point events into a home/away tally."""

from translators.rugby import RugbySport

from tracer.events import compute_score, RESTART_SCORE_TYPES
from tracer.match_state import MatchState

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


# --- penalty try and cards -------------------------------------------------
def test_penalty_try_is_seven_and_takes_no_conversion():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    m.key_down("y", 160.0)
    assert compute_score(m.events, m.team_names) == {"home": 7, "away": 0}
    m.key_down("c", 170.0)          # a conversion tap must find nothing to attach to
    assert compute_score(m.events, m.team_names) == {"home": 7, "away": 0}


def test_penalty_try_restarts_with_the_scoring_team():
    assert "penalty_try" in RESTART_SCORE_TYPES


def test_red_card_goes_against_the_defending_side_like_a_yellow():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    m.key_down("b", 160.0)          # yellow
    m.key_down("d", 200.0)          # red
    assert [(e["type"], e["team"]) for e in m.events] == \
        [("sin_bin", "WAL"), ("red_card", "WAL")]


def test_cards_stay_marker_only_in_the_momentum_model():
    for etype in ("sin_bin", "red_card"):
        (std,) = RugbySport().translate(
            [{"type": etype, "team": "ENG", "minute": 5.0}])
        assert std.weight == 0.0, etype
        assert std.category == "card", etype


def test_penalty_try_is_a_score_in_the_momentum_model():
    (std,) = RugbySport().translate(
        [{"type": "penalty_try", "team": "ENG", "minute": 5.0}])
    assert std.category == "score"
    assert std.weight == 2.3          # declared, not defaulted
