"""The decay + smoothing math the whole repo rests on.

This is the model the README describes, so these pin the four claims it makes:
energy decays with a half-life, an event has no effect before it happens, only
one team is on top at a time, and the output is normalised.

Smoothing is switched off (sigma=0) wherever the decay itself is under test,
so the assertion measures the exponential rather than the blur over it.
"""

import numpy as np
import pytest

from core.engine import MomentumEngine
from core.schema import StandardEvent


def _at(t_series, y, when):
    """Value of y at match-minute `when`."""
    return float(np.interp(when, t_series, y))


def test_energy_halves_over_one_half_life():
    engine = MomentumEngine(half_life_minutes=3.0, smooth_sigma=0)
    events = [StandardEvent(team="A", t=10.0, weight=1.0)]
    t = np.linspace(0, 30, 301)
    y = engine.team_series(events, "A", t)
    assert _at(t, y, 10.0) == pytest.approx(1.0, abs=1e-6)
    assert _at(t, y, 13.0) == pytest.approx(0.5, abs=1e-3)   # one half-life
    assert _at(t, y, 16.0) == pytest.approx(0.25, abs=1e-3)  # two


def test_an_event_has_no_effect_before_it_happens():
    engine = MomentumEngine(half_life_minutes=3.0, smooth_sigma=0)
    events = [StandardEvent(team="A", t=20.0, weight=1.0)]
    t = np.linspace(0, 30, 301)
    y = engine.team_series(events, "A", t)
    assert _at(t, y, 19.9) == 0.0
    assert _at(t, y, 20.0) > 0.0


def test_one_team_is_on_top_at_a_time():
    # the mirrored-area grammar: the two series never both carry value, so
    # the chart can never show both sides ahead at the same moment
    engine = MomentumEngine(half_life_minutes=3.0)
    events = [StandardEvent(team="A", t=5.0, weight=1.0),
              StandardEvent(team="B", t=25.0, weight=2.0)]
    _, y_home, y_away = engine.compute(events, "A", "B", 40)
    assert np.all(y_home >= 0) and np.all(y_away >= 0)
    assert np.all(y_home * y_away == 0)


def test_output_is_normalised_to_a_unit_peak():
    engine = MomentumEngine(half_life_minutes=3.0)
    events = [StandardEvent(team="A", t=5.0, weight=0.01),
              StandardEvent(team="B", t=25.0, weight=99.0)]
    _, y_home, y_away = engine.compute(events, "A", "B", 40)
    assert max(y_home.max(), y_away.max()) == pytest.approx(1.0)


def test_a_match_with_no_threat_events_is_an_error_not_a_flat_line():
    # dividing by a zero peak would silently produce NaNs all the way to the
    # rendered chart; failing loudly here is the point
    engine = MomentumEngine(half_life_minutes=3.0)
    with pytest.raises(ValueError):
        engine.compute([], "A", "B", 40)


def test_weights_from_the_same_team_accumulate():
    engine = MomentumEngine(half_life_minutes=3.0, smooth_sigma=0)
    t = np.linspace(0, 30, 301)
    one = engine.team_series([StandardEvent(team="A", t=10.0, weight=1.0)], "A", t)
    two = engine.team_series([StandardEvent(team="A", t=10.0, weight=1.0),
                              StandardEvent(team="A", t=10.0, weight=1.0)], "A", t)
    assert _at(t, two, 12.0) == pytest.approx(2 * _at(t, one, 12.0))


def test_the_other_teams_events_are_ignored():
    engine = MomentumEngine(half_life_minutes=3.0, smooth_sigma=0)
    t = np.linspace(0, 30, 301)
    y = engine.team_series([StandardEvent(team="B", t=10.0, weight=5.0)], "A", t)
    assert not y.any()
