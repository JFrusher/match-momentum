"""Placeholder pitch SVG: programmatic rectangle + markings at fixed 1:1 scale.

World Rugby standard: 100m field-of-play + in-goal areas, 70m wide. No image
asset, no responsive resize — the fixed PX_PER_M scale is what keeps the
pixel<->metre calibration trivial (geometry.py owns that math).
"""

from . import config

_M = config.PX_PER_M
IMAGE_W = (config.PITCH_LENGTH_M + 2 * config.IN_GOAL_DEPTH_M) * _M
IMAGE_H = config.PITCH_WIDTH_M * _M

_LEFT_TRY = config.IN_GOAL_DEPTH_M * _M
_RIGHT_TRY = _LEFT_TRY + config.PITCH_LENGTH_M * _M
_HALFWAY = (_LEFT_TRY + _RIGHT_TRY) / 2
_22_LEFT = _LEFT_TRY + 22 * _M
_22_RIGHT = _RIGHT_TRY - 22 * _M


def _vline(x, color="white", width=2, dash=""):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x}" y1="0" x2="{x}" y2="{IMAGE_H}" '
            f'stroke="{color}" stroke-width="{width}"{dash_attr} />')


def pitch_svg() -> str:
    return "".join([
        f'<rect x="0" y="0" width="{IMAGE_W}" height="{IMAGE_H}" fill="#2e7d3a" />',
        f'<rect x="0" y="0" width="{_LEFT_TRY}" height="{IMAGE_H}" fill="#276a32" />',
        f'<rect x="{_RIGHT_TRY}" y="0" width="{_LEFT_TRY}" height="{IMAGE_H}" fill="#276a32" />',
        _vline(_LEFT_TRY, width=3),
        _vline(_RIGHT_TRY, width=3),
        _vline(_HALFWAY),
        _vline(_22_LEFT, dash="10,8"),
        _vline(_22_RIGHT, dash="10,8"),
        f'<rect x="0" y="0" width="{IMAGE_W}" height="{IMAGE_H}" fill="none" '
        f'stroke="white" stroke-width="2" />',
    ])
