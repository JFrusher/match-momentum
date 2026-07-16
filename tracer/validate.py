"""Pre-export validation by running the REAL pipeline, not a schema copy.

Because tracer/ shares a process with the momentum code, the strongest
possible check is simply: does RugbySport().translate() accept these events,
and does a dry-run MomentumEngine.compute() succeed? Nothing can KeyError
downstream that didn't already fail here.
"""

from core.engine import MomentumEngine
from translators.rugby import RugbySport


def validate_events(events: list[dict], home: str, away: str) -> list[str]:
    """Empty list = exportable. Non-empty = human-readable blockers."""
    sport = RugbySport()
    try:
        std = sport.translate(events)
    except Exception as e:
        return [f"translate() rejected events: {e!r}"]
    try:
        MomentumEngine(half_life_minutes=sport.decay_half_life).compute(
            std, home, away, sport.chart_profile().max_t)
    except Exception as e:
        return [f"engine dry-run failed: {e!r}"]
    return []
