"""Set-piece chips: the correction UI, drawn where the set piece happened.

Every inferred attribution renders as a chip, and the chip's team badge is a
switch — there are two teams, so a wrong guess is always one click from right.
The type is never editable: it is either geometrically certain (a kick
finishing at a touchline is a lineout, a score is a restart) or it was tapped.
A lineout would never become a scrum, so offering that would be noise.

Chips are DOM elements positioned over the image rather than shapes drawn into
it: ui.interactive_image reports mouse coordinates, not element targets, so a
clickable shape inside its content would be unreachable. The layer itself is
pointer-events-none so drags still reach the canvas underneath.

Anchors are percentages, not pixels, so a chip stays on its mark when the
image scales down on a narrow window.
"""

from nicegui import ui

from . import config
from .pitch import IMAGE_W, IMAGE_H

ICONS = {
    "lineout": "swap_vert", "scrum": "groups", "penalty": "sports",
    "restart": "replay", "turnover_open": "cached",
    "interception": "back_hand", "kick_return": "sports_rugby",
    "kickoff": "flag", "drop_out_22": "vertical_align_top",
}
OPTION_LABELS = {
    "kick_to_touch": "to touch", "at_goal": "at goal",
    "tap_and_go": "tap", "scrum": "scrum",
}


def build_chips(match, layer):
    """Draw match.last_origin inside `layer`. Returns the refreshable."""

    @ui.refreshable
    def chip():
        o = match.last_origin
        if o is None or o.mark is None:
            return
        x, y = o.mark
        # Floats clear of its mark, like a map pin: anchored ON the point it
        # would sit over the traced line and swallow the clicks that
        # re-classify the segment underneath. A lineout mark is by definition
        # at a touchline, so near the top edge it hangs below instead of
        # sailing off the pitch.
        shift = "-125%" if y > IMAGE_H * 0.15 else "25%"
        with ui.element("div").classes("absolute pointer-events-auto").style(
                f"left:{x / IMAGE_W * 100:.2f}%;top:{y / IMAGE_H * 100:.2f}%;"
                f"transform:translate(-50%,{shift})"):
            with ui.column().classes("items-center gap-1"):
                _badge(match, o)
                if o.reason == "penalty":
                    _options(match)

    with layer:
        chip()
    return chip


def _badge(match, o):
    with ui.row().classes(
            "items-center gap-1 rounded-full pl-2 pr-1 py-0.5 shadow-lg "
            "text-xs font-bold text-white whitespace-nowrap"
    ).style(f"background:{match.team_colors[o.team]}"):
        ui.icon(ICONS.get(o.reason, "place")).classes("text-sm")
        ui.label(o.reason.replace("_", " ").upper())
        ui.button(match.team_names[o.team], on_click=match.flip_origin_team) \
            .props("flat dense no-caps size=sm color=white") \
            .tooltip("wrong team? click to swap")
        if o.alt_mark:
            ui.button(icon="swap_horiz", on_click=match.flip_origin_mark) \
                .props("flat dense size=sm color=white") \
                .tooltip("it bounced before going out — move the mark")


def _options(match):
    """The penalty chooser. Pre-selected on the guess; ignoring it accepts that."""
    with ui.row().classes("gap-0 rounded bg-white/90 shadow"):
        for opt in config.PENALTY_OPTIONS:
            chosen = match.penalty_option == opt
            ui.button(OPTION_LABELS[opt],
                      on_click=lambda o=opt: match.choose_penalty_option(o)) \
                .props(f"dense no-caps size=sm {'unelevated' if chosen else 'flat'} "
                       f"color={'primary' if chosen else 'grey-8'}")
