"""Exponential-decay + Gaussian-smoothing momentum math. Sport-agnostic.

momentum_team(t) = sum over events e of:  w_e * exp(-lambda * (t - t_e))   for t >= t_e
"""

import numpy as np
from scipy.ndimage import gaussian_filter1d


class MomentumEngine:
    def __init__(self, half_life_minutes: float, smooth_sigma: float = 1.2, resolution: int = 6):
        self.half_life = half_life_minutes
        self.smooth_sigma = smooth_sigma
        self.resolution = resolution
        self._lambda = np.log(2) / half_life_minutes

    def team_series(self, events, team, t):
        """Sum of exponentially-decaying, gaussian-smoothed impulses for one team.

        Public so callers that need a single team's raw (non-net) curve --
        e.g. compare.py's validation against per-team reference bars -- can
        get it without going through compute()'s net-momentum normalization.
        """
        y = np.zeros_like(t)
        for ev in events:
            if ev.team != team:
                continue
            dt = t - ev.t
            y += np.where(dt >= 0, ev.weight * np.exp(-self._lambda * np.clip(dt, 0, None)), 0.0)
        return gaussian_filter1d(y, self.smooth_sigma * self.resolution)

    def compute(self, events, home, away, max_t):
        """Returns (t, y_home, y_away): normalized net momentum split by side."""
        t = np.linspace(0, max_t, int(max_t * self.resolution) + 1)
        y_home = self.team_series(events, home, t)
        y_away = self.team_series(events, away, t)
        net = y_home - y_away
        peak = np.abs(net).max()
        if peak == 0:
            raise ValueError(f"no threat events found for {home}/{away}")
        net = net / peak
        return t, np.where(net > 0, net, 0), np.where(net < 0, -net, 0)
