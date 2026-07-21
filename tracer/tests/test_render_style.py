"""Segment stroke style: colour by action, dashed when intercepted.

Pure so it can be asserted without standing up a NiceGUI page.

There is deliberately no confidence shading — see segment_style's docstring
for why the margin cannot carry that meaning.
"""

from tracer.canvas import ACTION_COLORS, segment_style
from tracer.continuity import Segment


def _seg(action="CARRY", **kw):
    return Segment(action=action, points=[], **kw)


def test_each_action_gets_its_own_colour():
    seen = {segment_style(_seg(a))[0] for a in ("CARRY", "PASS", "KICK")}
    assert len(seen) == 3
    assert seen == set(ACTION_COLORS.values())


def test_an_ordinary_segment_is_solid():
    assert segment_style(_seg())[1] == ""


def test_intercepted_segment_is_dashed():
    assert segment_style(_seg(intercepted=True))[1]


def test_confidence_does_not_change_how_a_segment_draws():
    # a clean carry scores a 0.09 margin purely because CARRY is the zero
    # reference class; shading by it would mark the safest calls as doubtful
    assert segment_style(_seg(confidence=0.09)) == segment_style(_seg(confidence=1.0))
