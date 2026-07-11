"""
Match Momentum — a FIFA-broadcast-style momentum chart, rebuilt from scratch.

Model: each threat event (shot, chance, goal, sustained pressure) injects
"momentum energy" for its team, which decays exponentially over the following
minutes. Per-minute energy is smoothed with a Gaussian kernel and the two
teams are plotted as mirrored area fills around a center line — exactly the
visual grammar of the FIFA 2026 broadcast graphic.

Usage:  python momentum.py [events.json] [output.png]
"""

import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

# ---------------------------------------------------------------- parameters
DECAY_HALF_LIFE = 3.0      # minutes for an event's influence to halve
SMOOTH_SIGMA = 1.2         # gaussian smoothing of the per-minute series
RESOLUTION = 6             # samples per minute
MAX_MINUTE = 95            # 90 + stoppage

HOME_COLOR = "#6CACE4"     # Argentina sky blue
AWAY_COLOR = "#CE1126"     # Egypt red
BG_PANEL = "#3d4147"
BG_FIG = "#23262b"
GOAL_LINE = "#e8e8e8"


def build_series(events, team, t):
    """Sum of exponentially-decaying impulses for one team."""
    lam = np.log(2) / DECAY_HALF_LIFE
    y = np.zeros_like(t)
    for ev in events:
        if ev["team"] != team:
            continue
        dt = t - ev["minute"]
        y += np.where(dt >= 0, ev["weight"] * np.exp(-lam * np.clip(dt, 0, None)), 0.0)
    return gaussian_filter1d(y, SMOOTH_SIGMA * RESOLUTION)


def main(events_path="events.json", out_path="momentum_arg_egy.png"):
    with open(events_path) as f:
        data = json.load(f)

    events = sorted(data["events"], key=lambda e: e["minute"])
    home, away = data["teams"]["home"], data["teams"]["away"]
    colors = data.get("colors", {})
    home_color = colors.get("home", HOME_COLOR)
    away_color = colors.get("away", AWAY_COLOR)
    title = data.get("title", f"MATCH MOMENTUM  —  {home} vs {away}")
    t = np.linspace(0, MAX_MINUTE, MAX_MINUTE * RESOLUTION + 1)

    y_home = build_series(events, home, t)
    y_away = build_series(events, away, t)
    peak = max(y_home.max(), y_away.max())
    if peak == 0:
        raise ValueError(f"no threat events found for {home}/{away} in {events_path}")
    y_home, y_away = y_home / peak, y_away / peak

    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=200)
    fig.patch.set_facecolor(BG_FIG)
    ax.set_facecolor(BG_PANEL)

    # mirrored fills
    ax.fill_between(t, 0, y_home, color=home_color, alpha=0.95, lw=0)
    ax.fill_between(t, 0, -y_away, color=away_color, alpha=0.95, lw=0)
    ax.axhline(0, color="#d9d9d9", lw=2)

    # half-time divider
    ax.axvline(45, color="#c8c8c8", lw=1.2, alpha=0.7)

    # goal markers (stagger labels that fall within 12 minutes of each other)
    last_x = {1: -100, -1: -100}
    high = {1: False, -1: False}
    for ev in events:
        if ev["type"] != "goal":
            continue
        sign = 1 if ev["team"] == home else -1
        if ev["minute"] - last_x[sign] < 12:
            high[sign] = not high[sign]
        else:
            high[sign] = False
        last_x[sign] = ev["minute"]
        tip = 1.12 + (0.14 if high[sign] else 0)
        ax.plot([ev["minute"], ev["minute"]], [0, sign * tip],
                color=GOAL_LINE, lw=1.4)
        ax.plot(ev["minute"], sign * tip, marker="o", ms=9,
                mfc="white", mec="#555", zorder=5)
        ax.annotate(ev.get("label", ""), (ev["minute"], sign * (tip + 0.12)),
                    ha="center", va="center", fontsize=8.5,
                    color="#f0f0f0", fontweight="bold")

    # penalty-saved marker (drawn on the side of the team that missed)
    for ev in events:
        if ev["type"] == "penalty_missed":
            sign = 1 if ev["team"] == home else -1
            ax.plot(ev["minute"], sign * 1.12, marker="x", ms=9, mew=2.5,
                    color="#f5c518", zorder=5)
            ax.annotate(ev.get("label", ""), (ev["minute"], sign * 1.24),
                        ha="center", va="center", fontsize=8.5,
                        color="#f5c518", fontweight="bold")

    # axes cosmetics
    ax.set_xlim(0, MAX_MINUTE)
    ax.set_ylim(-1.55, 1.55)
    ticks = [0, 15, 30, 45, 60, 75, 90]
    ax.set_xticks(ticks)
    ax.set_xticklabels(["0'", "15'", "30'", "HT", "60'", "75'", "FT"],
                       color="#e0e0e0", fontsize=11, fontweight="bold")
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    ax.set_title(title, color="white", fontsize=15, fontweight="bold", pad=18)
    ax.text(0.012, 0.96, home, transform=ax.transAxes, color=home_color,
            fontsize=13, fontweight="bold", va="top")
    ax.text(0.012, 0.04, away, transform=ax.transAxes, color=away_color,
            fontsize=13, fontweight="bold", va="bottom")
    fig.text(0.5, 0.015, data.get("footer", ""),
             ha="center", color="#9a9a9a", fontsize=8)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(out_path, facecolor=BG_FIG, bbox_inches="tight")
    print(f"saved {out_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)
