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
