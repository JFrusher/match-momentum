from tracer.keystate import KeyState


def test_taps_logged_lowercase():
    ks = KeyState()
    ks.key_down("K", 1.0)
    ks.key_down("5", 1.2)
    assert [(t.key, t.t) for t in ks.taps] == [("k", 1.0), ("5", 1.2)]


def test_shift_is_held_state_not_tap():
    ks = KeyState()
    ks.key_down("Shift", 1.0)
    assert ks.intercept_held() and ks.taps == []
    ks.key_up("Shift", 2.5)
    assert not ks.intercept_held()
    assert ks.shift_intervals == [(1.0, 2.5)]


def test_open_shift_interval_clamped():
    ks = KeyState()
    ks.key_down("shift", 3.0)
    assert ks.intervals_until(4.0) == [(3.0, 4.0)]
    assert ks.shift_intervals == []  # still open, not committed


def test_clear_chain_keeps_held_shift():
    ks = KeyState()
    ks.key_down("shift", 1.0)
    ks.key_down("l", 1.5)
    ks.clear_chain()
    assert ks.taps == [] and ks.shift_intervals == []
    assert ks.intercept_held()
    ks.key_up("shift", 9.0)  # closes against the ORIGINAL down; acceptable
    assert len(ks.shift_intervals) == 1


def test_repeated_keydown_autorepeat_ignored_for_shift():
    ks = KeyState()
    ks.key_down("shift", 1.0)
    ks.key_down("shift", 1.1)  # OS auto-repeat must not reset the interval start
    ks.key_up("shift", 2.0)
    assert ks.shift_intervals == [(1.0, 2.0)]
