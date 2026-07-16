"""Pixel<->metre calibration + territory field math. Pure.

Isolated from pitch.py so a real pitch image can replace the placeholder
later without touching this math. x runs along the pitch's length; the
field-of-play spans [left_try_line_px, left_try_line_px + 100m].
"""

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class PitchCalibration:
    px_per_m: float = config.PX_PER_M
    left_try_line_px: float = config.IN_GOAL_DEPTH_M * config.PX_PER_M

    def field_x_m(self, x_px: float) -> float:
        """Metres from the left try line (0 = left try line, 100 = right)."""
        return (x_px - self.left_try_line_px) / self.px_per_m

    def metres_gained(self, x0_px: float, x1_px: float, attack_dir: int) -> float:
        """Net forward displacement along the attack axis, clamped >= 0."""
        return max(0.0, round(attack_dir * (x1_px - x0_px) / self.px_per_m, 1))

    def end_metres_from_line(self, x_px: float, attack_dir: int) -> float:
        """Distance from the attacking try line, clamped to [0, 100]."""
        fx = self.field_x_m(x_px)
        dist = (config.PITCH_LENGTH_M - fx) if attack_dir > 0 else fx
        return round(min(100.0, max(0.0, dist)), 1)
