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
BOUNDARY_GROUP_MS = 150     # consecutive candidates this close = one turn
MIN_SEGMENT_MS = 350        # boundaries closer than this: keep the stronger
FAST_SPEED_MPS = 15.0       # traced faster than this = kick candidate
SHORT_DURATION_MS = 1500    # ...if the burst is also this short
LATERAL_RATIO = 1.2         # |lateral| > ratio*|forward| = pass
MIN_MOVEMENT_PX = 6         # smaller total displacement = accidental click

# --- boundary evidence scoring (Layer 1) ----------------------------------
# A point is a boundary iff its combined evidence score clears BOUNDARY_ACCEPT.
# Evidence is measured against THIS path's own baseline (median angle/ratio),
# so a wobbly hand raises the bar and a clean hand lowers it.
BOUNDARY_ANGLE_FLOOR_DEG = 8.0   # baseline never below this much wobble
BOUNDARY_ANGLE_BASE_MULT = 2.0   # evidence starts this far above path median
BOUNDARY_ANGLE_SCALE_DEG = 45.0  # tanh scale for angle excess
BOUNDARY_RATIO_FLOOR = 1.2
BOUNDARY_RATIO_BASE_MULT = 1.5
BOUNDARY_RATIO_SCALE = 1.0
W_BOUNDARY_ANGLE = 1.0
W_BOUNDARY_SPEED = 1.0
BOUNDARY_ACCEPT = 0.75           # single accept threshold on the combined score
                                 # (sweep 2026-07-20: 0.65-0.85 all-pass; 0.75 =
                                 # band center; genuine turns >=0.92, release
                                 # wobble <=0.73 on noisy corpus)

# --- classification feature squashing (Layer 2) ---------------------------
# Each feature is tanh((raw - center)/scale); evidence features are rectified
# (max(0, .) before tanh) so absence of evidence is 0, never negative.
# LATERAL_RATIO / FAST_SPEED_MPS / SHORT_DURATION_MS above are the centers.
F_BACK_SCALE_M = 0.5             # sharp: near-step at fwd=0 (rugby law edge)
F_LAT_SCALE_M = 1.5
F_SPEED_SCALE_MPS = 4.0
F_DUR_SCALE_S = 0.5
F_STRAIGHT_CENTER = 0.85         # net/path-length above this reads deliberate
F_STRAIGHT_SCALE = 0.10
F_BURSTY_CENTER = 1.6            # 90th-pct/mean step speed above this = impulsive
F_BURSTY_SCALE = 0.4
F_DIST_SCALE_M = 15.0

# --- classification weights: score_c = B_c + sum(W_c_f * feature_f) -------
# CARRY is the fixed reference class (score 0, no constants here). Initial
# values reproduce the legacy rule cascade (pinned by tests/test_scoring.py);
# zeros are trainer headroom — python -m tracer.fit proposes, never writes.
B_PASS = -0.2
W_PASS_BACKWARD = 8.0
W_PASS_LATERAL = 7.0
W_PASS_FAST = 0.0
W_PASS_SHORT = 0.0
W_PASS_KICKBURST = 0.0
W_PASS_STRAIGHT = 0.0
W_PASS_BURSTY = 0.0
W_PASS_DIST = 0.0
B_KICK = -0.2
W_KICK_BACKWARD = 0.0
W_KICK_LATERAL = 0.0
W_KICK_FAST = 0.0
W_KICK_SHORT = 0.0
W_KICK_KICKBURST = 6.0
W_KICK_STRAIGHT = 0.0
W_KICK_BURSTY = 0.0
W_KICK_DIST = 0.0

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
