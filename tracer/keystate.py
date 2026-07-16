"""Held-state (Shift) + timestamped tap log. Pure; NiceGUI feeds it key events.

One unified correlation mechanism: every recognized non-modifier key becomes
a TapEvent in an append-only log, matched against segment time windows at
chain end. Shift is continuous held-state, recorded as closed intervals.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TapEvent:
    key: str  # lowercase single char, or " " for space
    t: float


@dataclass
class KeyState:
    held: set = field(default_factory=set)
    taps: list = field(default_factory=list)             # list[TapEvent]
    shift_intervals: list = field(default_factory=list)  # list[(start, end)]
    _shift_down_t: Optional[float] = None

    def key_down(self, key: str, t: float):
        key = key.lower()
        if key == "shift":
            if self._shift_down_t is None:
                self._shift_down_t = t
            self.held.add("shift")
        else:
            self.taps.append(TapEvent(key, t))

    def key_up(self, key: str, t: float):
        key = key.lower()
        if key == "shift" and self._shift_down_t is not None:
            self.shift_intervals.append((self._shift_down_t, t))
            self._shift_down_t = None
            self.held.discard("shift")

    def intercept_held(self) -> bool:
        return "shift" in self.held

    def intervals_until(self, t_end: float) -> list:
        """Closed shift intervals, plus the still-open one clamped to t_end."""
        out = list(self.shift_intervals)
        if self._shift_down_t is not None:
            out.append((self._shift_down_t, t_end))
        return out

    def clear_chain(self):
        """Reset per-chain logs; a still-held Shift survives into the next chain."""
        self.taps.clear()
        self.shift_intervals.clear()
