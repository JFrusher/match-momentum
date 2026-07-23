"""NiceGUI entrypoint: page composition + ui.run.

Run:  .venv/Scripts/python -m tracer.app
Opens a browser tab; uses a native window instead if pywebview is installed.
reload=False is non-negotiable: dev auto-reload restarts the process and
silently drops in-memory match state.
"""

import importlib.util
import sys
import time

from nicegui import ui

from . import autosave
from .canvas import TraceCanvas
from .chips import build_chips
from .devpanel import build_dev_panel
from .events import compute_score
from .export import export_json
from .pitch import pitch_svg
from .raw_export import export_raw
from .review import open_review
from .setup import setup_form


def markings(m):
    """Pitch markings tinted for who is defending which end right now."""
    return pitch_svg(m.team_colors, m.attack_dir_home, m.team_names)

DIR_ARROWS = {1: "→", -1: "←"}
REASON_TEXT = {"kick": "won on kick", "turnover": "won on turnover",
               "score": "restart"}
DEV_CLI = "dev" in sys.argv[1:]  # for the native window, where ?dev=1 is unreachable


@ui.page("/")
def index(dev: bool = False):  # ?dev=1 enables the dev drawer
    # per-connection state, built inside the page closure: module-level state
    # would let two tabs / a reload corrupt each other's match
    ctx = {"match": None, "canvas": None}
    root = ui.column().classes("items-center gap-3 w-full")

    def undo():
        m = ctx["match"]
        if m:
            m.undo_last()
            ctx["canvas"].render_segments([])   # drop the drawing it belonged to

    def handle_key(e):
        m = ctx["match"]
        if m is None:
            return
        t = time.monotonic()
        # intercept before dispatch: "z" is also the home-possession key, so
        # an un-intercepted Ctrl+Z would undo AND hand the ball to home
        if e.action.keydown and e.modifiers.ctrl and e.key.name.lower() == "z":
            undo()
            return
        if e.action.keydown:
            m.key_down(e.key.name, t)
        elif e.action.keyup:
            m.key_up(e.key.name, t)

    ui.keyboard(on_key=handle_key, repeating=False)

    def save_now():
        m = ctx["match"]
        if m:
            autosave.save_session(m.to_dict(), autosave.session_path(
                m.team_names["home"], m.team_names["away"]))

    def build_match_ui(m):
        ctx["match"] = m
        root.clear()
        with root:
            with ui.row().classes("items-center gap-4"):
                clock_lbl = ui.label("00:00").classes("text-3xl font-mono")
                clock_btn = ui.button(icon="play_arrow", on_click=m.clock.toggle)
                chip_cls = ("px-2 py-0.5 rounded text-white text-2xl "
                            "font-mono font-bold")
                home_chip = ui.label().classes(chip_cls) \
                    .style(f"background:{m.team_colors['home']}")
                away_chip = ui.label().classes(chip_cls) \
                    .style(f"background:{m.team_colors['away']}")
                poss_lbl = ui.label().classes(
                    "px-4 py-1 rounded-full text-white text-3xl font-bold "
                    "shadow-lg")
                status_lbl = ui.label().classes("text-sm text-gray-500")
                ui.button("Halftime flip", on_click=m.halftime_flip).props("outline")
                ui.button("Review", on_click=lambda: open_review(m)).props("outline")
                ui.button("Undo", icon="undo", on_click=undo).props("outline") \
                    .tooltip("Ctrl+Z — rewind the last committed chain")
            canvas = TraceCanvas(on_down=m.mouse_down, on_move=m.mouse_move,
                                 on_up=m.mouse_up,
                                 on_segment_click=m.reclassify_segment,
                                 base_svg=markings(m))
            ctx["canvas"] = canvas
            chips = build_chips(m, canvas.chip_layer)
            with ui.row().classes("items-center gap-2"):
                path_in = ui.input("Export path", value="examples/tracer-sample.json") \
                    .classes("w-72")

                def do_export():
                    errors = export_json(path_in.value, m.team_names, m.events)
                    if errors:
                        ui.notify("; ".join(errors), type="negative", timeout=8000)
                    else:
                        ui.notify(f"exported {path_in.value}", type="positive")

                ui.button("Validate + export", on_click=do_export)

                data_dir = ui.input(
                    "Data folder",
                    value=f"exports/{m.team_names['home']}_v_{m.team_names['away']}"
                ).classes("w-64")

                def do_data_export():
                    path = export_raw(data_dir.value,
                                      {"date": m.date, "competition": m.competition},
                                      m.team_names, m.events, m.actions)
                    ui.notify(f"data exported to {path}", type="positive")

                ui.button("Export data (CSV)", on_click=do_data_export)
                ui.label("Trace = hold mouse · A/Space = end play · S scrum · "
                         "F penalty · K/P/R hint (or click a segment) · L break · "
                         "Shift intercept · digits player · Z/X team · "
                         "T/N/G/V/B events · C/M conversion · "
                         "E/W/H knock-on/fwd-pass/handling · Ctrl+Z undo"
                         ).classes("text-xs text-gray-500")

        # last score and direction drawn, so a change can react to itself
        shown = {"score": None, "dir": m.attack_dir_home, "poss": None}

        def refresh():
            secs = int(m.clock.seconds())
            if shown["dir"] != m.attack_dir_home:      # halftime: retint the ends
                shown["dir"] = m.attack_dir_home
                canvas.set_pitch(markings(m))
            clock_lbl.text = f"{secs // 60:02d}:{secs % 60:02d}"
            clock_btn.props(f'icon={"pause" if m.clock.running else "play_arrow"}')
            score = compute_score(m.events, m.team_names)
            home_chip.text = f"{m.team_names['home']} {score['home']}"
            away_chip.text = f"{score['away']} {m.team_names['away']}"
            if shown["score"] not in (None, score):
                ui.notify(f"{home_chip.text} – {away_chip.text}",
                          type="positive", position="top", timeout=3000)
            shown["score"] = dict(score)
            poss_dir = m.attack_dir_home if m.possession == "home" else -m.attack_dir_home
            reason = REASON_TEXT.get(m.last_end_reason)
            poss_lbl.text = f"{m.team_names[m.possession]} {DIR_ARROWS[poss_dir]}"
            if shown["poss"] != m.possession:   # restyle only on a real change
                shown["poss"] = m.possession
                poss_lbl.style(f"background:{m.team_colors[m.possession]}")
            status_lbl.text = ((f"{reason} · " if reason else "")
                               + f"{len(m.events)} events")

        def committed(chain):
            canvas.render_segments(chain.segments)
            if m.last_summary:  # catch a misread now, not in the dev panel
                ui.notify(m.last_summary, position="top", timeout=2500)

        m.on_commit = committed
        m.on_change = lambda: (save_now(), refresh(), chips.refresh())
        # timers must attach to a live slot: begin() runs inside the setup
        # form's click handler, whose slot root.clear() just deleted
        with root:
            ui.timer(0.5, refresh)
            ui.timer(5.0, save_now)  # plus save-on-commit via on_change
        refresh()
        if dev or DEV_CLI:
            with root:  # a live slot; the drawer/layout top-level rule doesn't apply
                build_dev_panel(m)

    def begin(match):
        build_match_ui(match)

    setup_form(root, begin, autosave.latest_session())


if __name__ in {"__main__", "__mp_main__"}:
    port = next((int(a) for a in sys.argv[1:] if a.isdigit()), 8080)
    native = importlib.util.find_spec("webview") is not None
    ui.run(title="Live Trace", port=port, reload=False, native=native,
           window_size=(1200, 820) if native else None)
