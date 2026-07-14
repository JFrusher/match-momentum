from .base import BaseSport, ChartProfile
from .football import FootballSport
from .rugby import RugbySport

SPORTS = {
    "football": FootballSport,
    "rugby": RugbySport,
}

__all__ = ["BaseSport", "ChartProfile", "SPORTS"]
