"""Sweep's core: corpus scoring + config restoration."""

from tracer import config, sweep


def test_score_baseline_all_pass_and_config_untouched():
    before = (config.BOUNDARY_ACCEPT, config.W_PASS_LATERAL,
              config.MIN_SEGMENT_MS)
    passed, total, failed = sweep.score()
    assert (passed, failed) == (total, [])
    assert total >= 39
    after = (config.BOUNDARY_ACCEPT, config.W_PASS_LATERAL,
             config.MIN_SEGMENT_MS)
    assert after == before
