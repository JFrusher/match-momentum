"""Scored boundary detection: path-adaptive baselines + accept threshold."""

import pytest

from tracer import config, fixtures, segmentation


def trace(waypoints, durations, seed=7):
    return fixtures.noisy_path(waypoints, durations, seed)


def test_right_angle_turn_splits():
    segs = segmentation.segment_path(trace(((10, 35), (20, 35), (20, 43)),
                                           (2.0, 2.0)), +1)
    assert len(segs) == 2


def test_gentle_weave_stays_whole():
    segs = segmentation.segment_path(
        trace(((10, 35), (16, 34), (22, 36), (28, 35)), (1.5, 1.5, 1.5)), +1)
    assert len(segs) <= 2  # ~28 deg turns must not all split


def test_boundary_debug_block():
    segmentation.segment_path(
        trace(((10, 35), (20, 35), (19, 43), (31, 43)), (2.5, 0.45, 3.0)), +1)
    b = segmentation.last_debug["boundary"]
    for key in ("med_angle", "med_ratio", "angle_base", "ratio_base",
                "accept", "near_misses"):
        assert key in b
    assert b["accept"] == config.BOUNDARY_ACCEPT
    floor = config.BOUNDARY_ANGLE_FLOOR_DEG * config.BOUNDARY_ANGLE_BASE_MULT
    assert b["angle_base"] >= floor  # floor holds even on clean paths


def test_candidates_keep_legacy_keys_and_gain_score():
    segmentation.segment_path(
        trace(((10, 35), (20, 35), (19, 43), (31, 43)), (2.5, 0.45, 3.0)), +1)
    cands = segmentation.last_debug["candidates"]
    assert cands
    for c in cands:
        for key in ("i", "t", "x", "y", "angle", "ratio", "strength", "score"):
            assert key in c
        assert c["strength"] == c["score"]
        assert c["score"] >= config.BOUNDARY_ACCEPT


def test_accept_threshold_is_live(monkeypatch):
    pts = trace(((10, 35), (20, 35), (20, 43)), (2.0, 2.0))
    monkeypatch.setattr(config, "BOUNDARY_ACCEPT", 99.0)
    assert len(segmentation.segment_path(pts, +1)) == 1
    monkeypatch.setattr(config, "BOUNDARY_ACCEPT", 0.75)
    assert len(segmentation.segment_path(pts, +1)) == 2
