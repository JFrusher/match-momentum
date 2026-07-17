"""ui.interactive_image wiring: path capture + live preview + classified redraw.

Timestamps are stamped server-side (time.monotonic()) on event arrival —
MouseEventArguments carries no client timestamp. Fine for local use; WAN
latency jitter would degrade segmentation timing.
"""

import time

from nicegui import ui

from .pitch import IMAGE_W, IMAGE_H, pitch_svg

ACTION_COLORS = {"CARRY": "#ffd54f", "PASS": "#64b5f6", "KICK": "#ef5350"}


def _polyline(points, color, width=3, dash=""):
    if len(points) < 2:
        return ""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash_attr = f' stroke-dasharray="6,5"' if dash else ""
    return (f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round"{dash_attr} />')


class TraceCanvas:
    """Owns the interactive image; forwards raw gestures, renders paths back."""

    def __init__(self, *, on_down, on_move, on_up):
        self._on_down, self._on_move, self._on_up = on_down, on_move, on_up
        self._base = pitch_svg()
        self._live: list[tuple[float, float]] = []
        self._overlay = ""
        self.image = ui.interactive_image(
            size=(IMAGE_W, IMAGE_H),
            content=self._base,
            on_mouse=self._mouse,
            events=["mousedown", "mousemove", "mouseup"],
            cross=True,
        ).style(f"width:{IMAGE_W}px;max-width:100%")  # size= sets only aspect-ratio, not CSS width

    def _mouse(self, e):
        t = time.monotonic()
        if e.type == "mousedown":
            self._live = [(e.image_x, e.image_y)]
            self._overlay = ""  # previous chain's drawing clears on new trace
            self._on_down(e.image_x, e.image_y, t)
            self._redraw()
        elif e.type == "mousemove" and e.buttons:
            self._live.append((e.image_x, e.image_y))
            self._on_move(e.image_x, e.image_y, t)
            if len(self._live) % 3 == 0:  # ponytail: redraw every 3rd point; virtual-canvas diffing if it lags
                self._redraw()
        elif e.type == "mouseup":
            self._on_up(t)

    def render_segments(self, segments):
        """Replace the raw live line with the classified, color-coded result."""
        parts = []
        for seg in segments:
            color = ACTION_COLORS.get(seg.action, "white")
            parts.append(_polyline([(p.x, p.y) for p in seg.points], color,
                                   width=4, dash="dash" if seg.intercepted else ""))
        self._overlay = "".join(parts)
        self._live = []
        self._redraw()

    def _redraw(self):
        self.image.content = (self._base + self._overlay
                              + _polyline(self._live, "white", width=2))
