"""Scored classification: parity fence vs legacy cascade + pipeline contracts.

The parity test is the regression-free-switchover guarantee: the scored
argmax must reproduce the retired rule cascade on every segment the corpus
produces. If it fails, sharpen the offending feature scale or bias in
config.py — never edit the cascade copy below; the copy IS the spec.
"""

import math

import pytest

from tracer import config, features, fixtures
from tracer.match_state import MatchState


def run_scenario(sc):
    m = MatchState("HOME", "AWAY", attack_dir_home=sc.attack_dir,
                   possession=sc.possession)
    m.clock.start(t=0.0)
    fixtures.inject(m, sc)
    return m


def legacy_cascade(points, attack_dir):
    """Verbatim copy of the retired _classify decision logic (the spec)."""
    start, end = points[0], points[-1]
    forward = attack_dir * (end.x - start.x)
    lateral = end.y - start.y
    duration = end.t - start.t
    speed_mps = (math.hypot(end.x - start.x, lateral) / duration / config.PX_PER_M
                 if duration > 0 else 0.0)
    if forward < 0:
        return "PASS"
    if abs(lateral) > abs(forward) * config.LATERAL_RATIO:
        return "PASS"
    if speed_mps > config.FAST_SPEED_MPS and duration * 1000 < config.SHORT_DURATION_MS:
        return "KICK"
    return "CARRY"


@pytest.mark.parametrize("name", list(fixtures.SCENARIOS))
def test_scored_argmax_matches_legacy_cascade(name):
    m = run_scenario(fixtures.SCENARIOS[name])
    if m.last_chain is None:
        return  # rejected traces produce no segments
    for seg, ev in zip(m.last_chain.segments, m.last_debug["segments"]):
        assert ev["action_geo"] == legacy_cascade(seg.points, ev["attack_dir"]), (
            f"{name}: fwd={ev['forward_px']}px lat={ev['lateral_px']}px "
            f"dur={ev['duration_s']}s speed={ev['speed_mps']}m/s "
            f"scores={ev.get('scores')}")


def test_segments_carry_scores_and_confidence():
    m = run_scenario(fixtures.SCENARIOS["carry_pass_carry_kick"])
    for seg in m.last_chain.segments:
        assert set(seg.scores) == {"CARRY", "PASS", "KICK"}
        assert seg.scores["CARRY"] == 0.0
        assert 0.0 <= seg.confidence <= 1.0


def test_evidence_has_score_breakdown():
    m = run_scenario(fixtures.SCENARIOS["carry_straight"])
    ev = m.last_debug["segments"][0]
    for key in ("features", "scores", "probs", "confidence", "action_geo", "rule"):
        assert key in ev
    assert set(ev["features"]) == set(features.FEATURES)
    assert ev["rule"]
    assert sum(ev["probs"].values()) == pytest.approx(1.0, abs=2e-3)  # display-rounded


def test_decisive_calls_have_high_confidence():
    m = run_scenario(fixtures.SCENARIOS["pass_backward"])
    assert m.last_chain.segments[0].confidence > 0.95


def test_hint_overrides_action_but_not_geometry():
    m = run_scenario(fixtures.SCENARIOS["hint_k"])
    assert m.last_chain.segments[0].action == "KICK"          # hint applied
    assert m.last_debug["segments"][0]["action_geo"] == "CARRY"  # geometry kept
