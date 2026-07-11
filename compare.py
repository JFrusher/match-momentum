"""
Validation: our decay-model momentum vs independent reference graphics.

Reference = Flashscore's published Momentum graphics for the same matches,
traced by eye into per-minute bar values (their image files can't be
redistributed, so the bars below are manual digitizations - see README).

  - ARG vs EGY: Flashscore snapshot at 2-2 (~minute 85+)
  - AUS vs TUR: Flashscore snapshot at half-time (1-0), so comparison
    is restricted to minutes 0-48

Our model's curves are overlaid as lines on the traced bars.

Usage: python compare.py
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from momentum import build_series, RESOLUTION, BG_PANEL, BG_FIG

# ------------------------------------------------------------- traced bars
# (minute, value 0..1) eyeballed from the Flashscore graphics.
ARG_REF = {
    2: .1, 4: .15, 6: .1, 8: .2, 10: .25, 12: .55, 13: .9, 14: .5, 15: .3,
    16: .35, 18: .4, 20: .5, 21: .55, 22: .4, 24: .3, 26: .4, 27: .6, 28: .8,
    29: .55, 31: .45, 33: .35, 35: .45, 37: .4, 39: .5, 41: .7, 42: .6,
    43: .9, 44: .75, 45: .6, 46: .45, 48: .5, 50: .55, 52: .45, 54: .5,
    56: .4, 58: .45, 60: .35, 62: .4, 64: .3, 66: .2, 68: .25, 70: .35,
    72: .5, 74: .55, 76: .65, 78: .75, 79: .85, 80: .7, 82: 1.0, 83: .9,
    84: .95, 85: .7, 86: .6, 87: .5, 88: .45,
}
EGY_REF = {
    3: .1, 5: .15, 7: .2, 9: .25, 11: .2, 13: .45, 14: .6, 15: .9, 16: .8,
    17: .6, 18: .5, 19: .35, 20: .25, 25: .15, 28: .1, 31: .15, 34: .1,
    38: .1, 43: .2, 45: .5, 46: .35, 50: .3, 52: .2, 56: .1, 60: .15,
    64: .3, 66: .6, 67: .85, 68: .5, 70: .2, 74: .1, 80: .1, 85: .1,
}
AUS_REF = {  # first half only (Flashscore HT snapshot)
    2: .5, 3: .8, 4: .6, 5: .4, 8: .15, 10: .2, 12: .5, 13: .7, 14: .85,
    15: .6, 16: .5, 17: .45, 18: .4, 19: .35, 20: .3, 22: .25, 24: .2,
    26: .3, 27: .7, 28: .45, 30: .3, 33: .15, 36: .1, 40: .1, 43: .5, 45: .3,
}
TUR_REF = {
    1: .2, 3: .3, 5: .35, 7: .3, 9: .4, 11: .35, 13: .45, 15: .4, 17: .5,
    19: .45, 21: .4, 23: .5, 25: .45, 27: .3, 29: .5, 31: .65, 33: .8,
    34: .9, 35: .75, 36: .85, 37: .95, 38: .8, 39: .7, 40: .75, 41: .6,
    42: .7, 43: .65, 44: .8, 45: .9, 46: .7, 47: .6, 48: .5,
}


def panel(ax, events_file, ref_home, ref_away, home_color, away_color,
          title, tmax):
    with open(events_file) as f:
        data = json.load(f)
    t = np.linspace(0, tmax, tmax * RESOLUTION + 1)
    home, away = data["teams"]["home"], data["teams"]["away"]
    yh = build_series(data["events"], home, t)
    ya = build_series(data["events"], away, t)
    peak = max(yh.max(), ya.max())
    yh, ya = yh / peak, ya / peak

    ax.set_facecolor(BG_PANEL)
    ax.bar(list(ref_home), list(ref_home.values()), width=0.85,
           color=home_color, alpha=0.55,
           label=f"{home} — Flashscore graphic (traced)")
    ax.bar(list(ref_away), [-v for v in ref_away.values()], width=0.85,
           color=away_color, alpha=0.55,
           label=f"{away} — Flashscore graphic (traced)")
    ax.plot(t, yh, color="white", lw=2.8,
            label="our model (above line = " + home + ", below = " + away + ")")
    ax.plot(t, -ya, color="white", lw=2.8)
    ax.axhline(0, color="#d9d9d9", lw=1.5)
    ax.axvline(45, color="#c8c8c8", lw=1, alpha=0.6)
    ax.set_xlim(0, tmax)
    ax.set_ylim(-1.25, 1.25)
    ax.set_yticks([])
    ticks = [0, 15, 30, 45, 60, 75, 90][: (tmax // 15) + 1]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{m}'" if m not in (0, 45) else ("0'" if m == 0 else "HT")
                        for m in ticks])
    ax.tick_params(colors="#e0e0e0", labelsize=12)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, color="white", fontsize=13.5, fontweight="bold", pad=12)
    ax.legend(loc="lower left", fontsize=10, framealpha=0.25,
              labelcolor="white", facecolor=BG_PANEL, edgecolor="none")


fig, axes = plt.subplots(2, 1, figsize=(12, 9), dpi=200)
fig.patch.set_facecolor(BG_FIG)

panel(axes[0], "events.json", ARG_REF, EGY_REF, "#6CACE4", "#CE1126",
      "ARGENTINA 3–2 EGYPT  ·  Round of 16", 95)
panel(axes[1], "events_aus_tur.json", AUS_REF, TUR_REF, "#FFC72C", "#E30A17",
      "AUSTRALIA 2–0 TÜRKIYE  ·  Group D  ·  first half (reference is a HT snapshot)", 48)

fig.suptitle("HOW CLOSE IS THE REBUILD?  Our momentum model (white) vs a published graphic (bars)",
             color="white", fontsize=15, fontweight="bold")
fig.text(0.5, 0.01,
         "Bars traced by eye from Flashscore's Momentum graphics (flashscore.com) · "
         "white curve = exponential-decay threat model · World Cup 2026",
         ha="center", color="#9a9a9a", fontsize=9)
plt.tight_layout(rect=[0, 0.02, 1, 0.97])
fig.savefig("comparison_model_vs_reference.png", facecolor=BG_FIG,
            bbox_inches="tight")
print("saved comparison_model_vs_reference.png")
