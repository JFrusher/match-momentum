"""Football translator -- behavior-preserving port of the original model.

Discrete threat events (shots, chances, goals, sustained pressure) map to
weights via a static table. Existing calibrated data can still override the
table by carrying an explicit "weight" field on the raw event, exactly as
events.json already does.
"""

import json
from pathlib import Path

from core.schema import StandardEvent
from .base import BaseSport, ChartProfile

_WEIGHTS = json.loads((Path(__file__).parent / "football_weights.json").read_text())


class FootballSport(BaseSport):
    name = "football"
    decay_half_life = 3.0  # minutes for an event's influence to halve

    def chart_profile(self):
        return ChartProfile(
            max_t=95,  # 90 + stoppage
            interval_markers=[45],
            tick_positions=[0, 15, 30, 45, 60, 75, 90],
            tick_labels=["0'", "15'", "30'", "HT", "60'", "75'", "FT"],
        )

    def translate(self, raw_events):
        out = []
        for ev in raw_events:
            etype = ev["type"]
            weight = ev.get("weight", _WEIGHTS.get(etype, _WEIGHTS["_default"]))
            marker = "score" if etype == "goal" else ("note" if etype == "penalty_missed" else None)
            out.append(StandardEvent(
                team=ev["team"],
                t=ev["minute"],
                weight=weight,
                category="score" if etype == "goal" else etype,
                label=ev.get("label"),
                marker=marker,
            ))
        return out
