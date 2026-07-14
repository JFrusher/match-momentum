"""Sport-agnostic event schema consumed by the momentum engine."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StandardEvent:
    """A single threat-energy impulse for one team.

    `t` is a continuous match-clock position; each Sport translator defines
    its unit and scale (real minutes for football/rugby; a sport without a
    wall clock, e.g. tennis, would map points/games onto a synthetic axis).
    """

    team: str
    t: float
    weight: float
    category: str = "generic"
    label: Optional[str] = None
    marker: Optional[str] = None  # "score" | "note" | None -> chart marker hint
