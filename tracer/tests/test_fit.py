"""fit.py: corpus extraction, training smoke, never-writes-config guarantee."""

import math

from tracer import config, fit


def test_training_set_skips_hints_and_covers_classes():
    xs, labels, names = fit.training_set()
    assert len(xs) == len(labels) > 20
    assert not any(n.startswith("hint") for n in names)
    assert {"CARRY", "PASS", "KICK"} <= set(labels)


def test_short_fit_reduces_loss_and_leaves_config_alone():
    before = (config.W_PASS_BACKWARD, config.B_PASS, config.W_KICK_DIST)
    xs, labels, _ = fit.training_set()
    params, losses = fit.train(xs, labels, epochs=50, lr=0.1, l2=0.01)
    assert all(math.isfinite(l) for l in losses)
    assert losses[-1] <= losses[0]
    assert set(params) == set(fit.PARAM_NAMES)
    assert (config.W_PASS_BACKWARD, config.B_PASS, config.W_KICK_DIST) == before
