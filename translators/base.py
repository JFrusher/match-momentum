"""Plug-in interface a sport-specific translator must implement.

A Sport owns match structure (duration, interval markers, decay half-life,
chart tick labels) and translate() -- turning one data source's raw events
into the engine's StandardEvent schema. It does not know or care which
DataSource produced those raw events.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChartProfile:
    max_t: float
    interval_markers: list       # e.g. [45] football half-time, [40] rugby half-time
    tick_positions: list
    tick_labels: list


class BaseSport(ABC):
    name: str
    decay_half_life: float  # minutes (or sport-defined time unit)

    @abstractmethod
    def chart_profile(self) -> ChartProfile:
        """Match structure for the chart renderer."""

    @abstractmethod
    def translate(self, raw_events: list) -> list:
        """Convert one data source's raw events into a list of StandardEvent."""
