"""
Match Momentum — a FIFA-broadcast-style momentum chart, sport-agnostic core.

Pipeline: DataSource.parse() -> Sport.translate() -> MomentumEngine.compute()
-> chart.render(). The decay/smoothing math and the chart renderer know
nothing about football specifically; match structure (duration, half-time
marker, decay half-life, axis labels) and event weighting come from the
chosen Sport translator (see translators/).

Usage:  python momentum.py [events.json] [output.png] [--sport football|rugby]
"""

import argparse

from core.engine import MomentumEngine
from core.chart import render
from sources.custom_json import CustomJSONSource
from translators import SPORTS

DEFAULT_HOME_COLOR = "#6CACE4"
DEFAULT_AWAY_COLOR = "#CE1126"


def main(events_path="examples/events_arg_egy.json", out_path="momentum_arg_egy.png", sport="football"):
    data = CustomJSONSource().parse(events_path)
    home, away = data["teams"]["home"], data["teams"]["away"]
    title = data["title"] or f"MATCH MOMENTUM  —  {home} vs {away}"

    sport_impl = SPORTS[sport]()
    events = sport_impl.translate(data["events"])
    chart_profile = sport_impl.chart_profile()

    engine = MomentumEngine(half_life_minutes=sport_impl.decay_half_life)
    t, y_home, y_away = engine.compute(events, home, away, chart_profile.max_t)

    render(
        t, y_home, y_away, events, home, away, chart_profile,
        home_color=data["colors"].get("home", DEFAULT_HOME_COLOR),
        away_color=data["colors"].get("away", DEFAULT_AWAY_COLOR),
        title=title, footer=data["footer"], out_path=out_path,
    )
    print(f"saved {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("events_path", nargs="?", default="examples/events_arg_egy.json")
    parser.add_argument("out_path", nargs="?", default="momentum_arg_egy.png")
    parser.add_argument("--sport", choices=list(SPORTS), default="football")
    args = parser.parse_args()
    main(args.events_path, args.out_path, args.sport)
