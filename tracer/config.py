"""All tunable constants for the tracer, in one place.

Segmentation thresholds are empirical: tuned against the synthetic fixtures
in tests/test_segmentation.py, expected to be re-tuned against real
hand-traced data. Units are metres/seconds where physical, milliseconds
where they name a *_MS window, degrees for angles.
"""

# --- pitch / calibration -------------------------------------------------
PX_PER_M = 8                # fixed 1:1 scale, no responsive resize (MVP)
PITCH_LENGTH_M = 100        # try line to try line
PITCH_WIDTH_M = 70
IN_GOAL_DEPTH_M = 10

# --- segmentation thresholds (the tunable heart of Live Trace) -----------
SMOOTH_WINDOW_PTS = 5       # sliding-average window to cut mouse jitter
HEADING_WINDOW_MS = 150     # mean-velocity window each side of a candidate
ANGLE_THRESHOLD_DEG = 55    # heading change that marks a boundary
SPEED_RATIO_THRESHOLD = 2.5 # sudden accel/decel that marks a boundary
BOUNDARY_GROUP_MS = 150     # consecutive candidates this close = one turn
MIN_SEGMENT_MS = 350        # boundaries closer than this: keep the stronger
FAST_SPEED_MPS = 15.0       # traced faster than this = kick candidate
SHORT_DURATION_MS = 1500    # ...if the burst is also this short
LATERAL_RATIO = 1.2         # |lateral| > ratio*|forward| = pass
MIN_MOVEMENT_PX = 6         # smaller total displacement = accidental click

# --- tap correlation ------------------------------------------------------
DIGIT_BURST_MS = 400        # sequential digit taps within this = one number
TYPE_HINT_GRACE_MS = 250    # late K/P/R tap still applies to just-ended segment
CONVERSION_LISTEN_S = 90    # after a Try tap, C/M within this = its conversion

# --- key vocabulary --------------------------------------------------------
TYPE_HINT_KEYS = {"k": "KICK", "p": "PASS", "r": "CARRY"}
LINEBREAK_KEY = "l"
TEAM_KEYS = {"z": "home", "x": "away"}
END_CHAIN_KEYS = {"a", " "}
DISCRETE_EVENT_KEYS = {
    "t": "try",
    "n": "penalty_kick",
    "g": "drop_goal",
    "v": "turnover_won",
    "b": "sin_bin",
}
CONVERSION_KEYS = {"c": "conversion", "m": "conversion_missed"}
