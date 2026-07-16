"""Pre-match setup screen (teams, attack direction, kickoff possession)."""

from nicegui import ui

from .match_state import MatchState


def setup_form(container, on_start, saved: dict = None):
    """Render the setup card into container; call on_start(MatchState) when ready."""
    with container:
        with ui.card() as card:
            ui.label("Match setup").classes("text-xl font-bold")
            if saved and saved.get("events"):
                ui.label(f"Unfinished session found "
                         f"({saved['teams']['home']} vs {saved['teams']['away']}, "
                         f"{len(saved['events'])} events).").classes("text-amber-700")
                ui.button("Resume session",
                          on_click=lambda: on_start(MatchState.from_dict(saved)))
                ui.separator()
            home = ui.input("Home team", value="HOME")
            away = ui.input("Away team", value="AWAY")
            direction = ui.select({1: "Home attacks →", -1: "Home attacks ←"},
                                  value=1, label="First-half direction")
            possession = ui.select({"home": "Home", "away": "Away"},
                                   value="home", label="Kickoff possession")
            # ponytail: squad-number rosters skipped; add if digit-tap typos get annoying
            ui.button("Start match", on_click=lambda: on_start(MatchState(
                home.value.strip() or "HOME", away.value.strip() or "AWAY",
                attack_dir_home=direction.value, possession=possession.value)))
    return card
