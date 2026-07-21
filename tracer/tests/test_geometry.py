from tracer import config
from tracer.geometry import PitchCalibration

cal = PitchCalibration()
PX = config.PX_PER_M
LEFT = config.IN_GOAL_DEPTH_M * PX


def test_field_x_round_trip():
    assert cal.field_x_m(LEFT) == 0.0
    assert cal.field_x_m(LEFT + 100 * PX) == 100.0
    assert cal.field_x_m(LEFT + 37.5 * PX) == 37.5


def test_metres_gained_forward_and_clamp():
    assert cal.metres_gained(LEFT, LEFT + 25 * PX, +1) == 25.0
    assert cal.metres_gained(LEFT + 25 * PX, LEFT, +1) == 0.0   # net backward clamps
    assert cal.metres_gained(LEFT + 25 * PX, LEFT, -1) == 25.0  # mirrored attack


def test_end_metres_from_line_and_clamps():
    assert cal.end_metres_from_line(LEFT + 92 * PX, +1) == 8.0
    assert cal.end_metres_from_line(LEFT + 92 * PX, -1) == 92.0
    assert cal.end_metres_from_line(LEFT + 110 * PX, +1) == 0.0    # in-goal: clamp low
    assert cal.end_metres_from_line(LEFT - 5 * PX, +1) == 100.0    # behind own line: clamp high


def test_metres_from_line_measures_a_start_point_too():
    assert cal.metres_from_line(LEFT + 5 * PX, +1) == 95.0


# --- touch, and the kick-to-touch-on-the-full law --------------------------
WIDTH = config.PITCH_WIDTH_M * PX


def test_path_ending_at_a_touchline_is_out():
    assert cal.ends_in_touch(0.0)
    assert cal.ends_in_touch(WIDTH)
    assert cal.ends_in_touch(config.TOUCH_MARGIN_M * PX)      # inside the margin


def test_path_ending_in_midfield_is_not_out():
    assert not cal.ends_in_touch(WIDTH / 2)


def test_own_22_depends_on_which_way_you_attack():
    assert cal.in_own_22(LEFT + 10 * PX, +1)      # attacking right: own line is left
    assert not cal.in_own_22(LEFT + 10 * PX, -1)
    assert cal.in_own_22(LEFT + 90 * PX, -1)
    assert not cal.in_own_22(LEFT + 90 * PX, +1)


def test_kick_from_inside_own_22_gains_the_ground():
    # kicked from 10m, found touch at 60m — lineout is where it went out
    mark = cal.lineout_mark_x(LEFT + 10 * PX, LEFT + 60 * PX, +1)
    assert cal.field_x_m(mark) == 60.0


def test_kick_from_outside_own_22_comes_back_on_the_full():
    # kicked from 40m, out at 75m. No bounce is visible to the tool, so the
    # law applies: the lineout goes back to the kick.
    mark = cal.lineout_mark_x(LEFT + 40 * PX, LEFT + 75 * PX, +1)
    assert cal.field_x_m(mark) == 40.0


def test_calibration_holds_at_every_offered_scale():
    # the scale selector changes px_per_m; every exported metre figure depends
    # on this staying exact, so a wrong scale silently corrupts the whole match
    for px in (6, 8, 10):
        c = PitchCalibration(px_per_m=px, left_try_line_px=config.IN_GOAL_DEPTH_M * px,
                             width_px=config.PITCH_WIDTH_M * px)
        left = config.IN_GOAL_DEPTH_M * px
        assert c.field_x_m(left + 40 * px) == 40.0
        assert c.metres_gained(left, left + 25 * px, +1) == 25.0
        assert c.metres_from_line(left + 78 * px, +1) == 22.0
        assert c.in_own_22(left + 10 * px, +1)
        assert c.ends_in_touch(0.0)
        assert not c.ends_in_touch(config.PITCH_WIDTH_M * px / 2)


def test_on_the_full_law_mirrors_for_the_other_direction():
    assert cal.field_x_m(cal.lineout_mark_x(LEFT + 90 * PX, LEFT + 40 * PX, -1)) == 40.0
    assert cal.field_x_m(cal.lineout_mark_x(LEFT + 60 * PX, LEFT + 25 * PX, -1)) == 60.0
