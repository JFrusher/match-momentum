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
    width_px: float = config.PITCH_WIDTH_M * config.PX_PER_M

    def field_x_m(self, x_px: float) -> float:
        """Metres from the left try line (0 = left try line, 100 = right)."""
        return (x_px - self.left_try_line_px) / self.px_per_m

    def metres_gained(self, x0_px: float, x1_px: float, attack_dir: int) -> float:
        """Net forward displacement along the attack axis, clamped >= 0."""
        return max(0.0, round(attack_dir * (x1_px - x0_px) / self.px_per_m, 1))

    def metres_from_line(self, x_px: float, attack_dir: int) -> float:
        """Distance from the attacking try line, clamped to [0, 100]."""
        fx = self.field_x_m(x_px)
        dist = (config.PITCH_LENGTH_M - fx) if attack_dir > 0 else fx
        return round(min(100.0, max(0.0, dist)), 1)

    def end_metres_from_line(self, x_px: float, attack_dir: int) -> float:
        """Same measurement, under the name the exported field uses."""
        return self.metres_from_line(x_px, attack_dir)

    def ends_in_touch(self, y_px: float) -> bool:
        """Did a path finish at a touchline?

        Proximity, not crossing: mousemove stops being reported once the
        cursor leaves the image, so a ball kicked out is a trace that stops
        at the edge rather than one seen passing through it.
        """
        margin = config.TOUCH_MARGIN_M * self.px_per_m
        return y_px <= margin or y_px >= self.width_px - margin

    def in_own_22(self, x_px: float, attack_dir: int) -> bool:
        """Is this point inside the 22 the attacking team is defending?"""
        return self.metres_from_line(x_px, attack_dir) >= (
            config.PITCH_LENGTH_M - config.TWENTY_TWO_M)

    def lineout_mark_x(self, kick_start_x_px: float, exit_x_px: float,
                       attack_dir: int) -> float:
        """Where the lineout is taken, per the kick-to-touch-on-the-full law.

        From inside your own 22 the ball may be kicked directly into touch and
        the ground is gained. From outside it, a direct kick to touch returns
        to the mark. The tool cannot see a bounce, so outside the 22 it assumes
        the ball went out on the full — the chip is clickable to say otherwise.
        """
        if self.in_own_22(kick_start_x_px, attack_dir):
            return exit_x_px
        return kick_start_x_px
