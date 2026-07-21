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
from .devpanel import build_dev_panel
from .events import compute_score
from .export import export_json
from .review import open_review
from .setup import setup_form

DIR_ARROWS = {1: "→", -1: "←"}
REASON_TEXT = {"kick": "won on kick", "turnover": "won on turnover",
               "score": "restart"}
DEV_CLI = "dev" in sys.argv[1:]  # for the native window, where ?dev=1 is unreachable


@ui.page("/")
def index(dev: bool = False):  # ?dev=1 enables the dev drawer
    # per-connection state, built inside the page closure: module-level state
    # would let two tabs / a reload corrupt each other's match
    ctx = {"match": None}
    root = ui.column().classes("items-center gap-3 w-full")

    def handle_key(e):
        m = ctx["match"]
        if m is None:
            return
        t = time.monotonic()
        if e.action.keydown:
            m.key_down(e.key.name, t)
        elif e.action.keyup:
            m.key_up(e.key.name, t)

    ui.keyboard(on_key=handle_key, repeating=False)

    def save_now():
        if ctx["match"]:
            autosave.save_session(ctx["match"].to_dict())

    def build_match_ui(m):
        ctx["match"] = m
        root.clear()
        with root:
            with ui.row().classes("items-center gap-4"):
                clock_lbl = ui.label("00:00").classes("text-3xl font-mono")
                clock_btn = ui.button(icon="play_arrow", on_click=m.clock.toggle)
                score_lbl = ui.label().classes("text-2xl font-mono")
                status_lbl = ui.label().classes("text-lg")
                ui.button("Halftime flip", on_click=m.halftime_flip).props("outline")
                ui.button("Review", on_click=lambda: open_review(m)).props("outline")
            canvas = TraceCanvas(on_down=m.mouse_down, on_move=m.mouse_move,
                                 on_up=m.mouse_up)
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
                ui.label("Trace = hold mouse · A/Space = end play · K/P/R hint · "
                         "L break · Shift intercept · digits player · Z/X team · "
                         "T/N/G/V/B events · C/M conversion").classes("text-xs text-gray-500")

        def refresh():
            secs = int(m.clock.seconds())
            clock_lbl.text = f"{secs // 60:02d}:{secs % 60:02d}"
            clock_btn.props(f'icon={"pause" if m.clock.running else "play_arrow"}')
            score = compute_score(m.events, m.team_names)
            score_lbl.text = (f"{m.team_names['home']} {score['home']}"
                              f" – {score['away']} {m.team_names['away']}")
            poss_dir = m.attack_dir_home if m.possession == "home" else -m.attack_dir_home
            reason = REASON_TEXT.get(m.last_end_reason)
            status_lbl.text = (f"{m.team_names[m.possession]} {DIR_ARROWS[poss_dir]}"
                               + (f" · {reason}" if reason else "")
                               + f" · {len(m.events)} events")

        m.on_commit = lambda chain: canvas.render_segments(chain.segments)
        m.on_change = lambda: (save_now(), refresh())
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

    setup_form(root, begin, autosave.load_session())


if __name__ in {"__main__", "__mp_main__"}:
    port = next((int(a) for a in sys.argv[1:] if a.isdigit()), 8080)
    native = importlib.util.find_spec("webview") is not None
    ui.run(title="Live Trace", port=port, reload=False, native=native,
           window_size=(1200, 820) if native else None)
