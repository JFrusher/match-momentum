"""Phase-4 proof: tracer output feeds the REAL RugbySport translator.

Expected weights are hand-computed from _territory_weight()'s formula and
hard-coded, so a drift in either side fails loudly.
"""

from core.engine import MomentumEngine
from translators.rugby import RugbySport

from tracer import config
from tracer.continuity import PathPoint, PlayChain, PlayerTag, Segment
from tracer.events import assign_teams, chain_to_events
from tracer.match_state import MatchState

PX = config.PX_PER_M
LEFT = config.IN_GOAL_DEPTH_M * PX
NAMES = {"home": "ENG", "away": "WAL"}


def seg(action, x0_m, x1_m, t0, t1, **kw):
    return Segment(action=action,
                   points=[PathPoint(LEFT + x0_m * PX, 280, t0),
                           PathPoint(LEFT + x1_m * PX, 280, t1)], **kw)


def make_chain(segments, team="home", start_minute=12.4):
    chain = PlayChain(chain_id="c1", team=team, start_minute=start_minute,
                      segments=segments)
    assign_teams(segments, team)
    return chain


def test_single_possession_weight_matches_hand_computed():
    # 10m -> 33m net, ends 67m out, one linebreak:
    # base = .15 + .35*(23/40) = .35125; territory = .3*(1-.67) = .099
    # weight = round((.35125+.099)*1.25, 2) = 0.56
    chain = make_chain([
        seg("CARRY", 10, 20, 100.0, 102.5),
        seg("PASS", 20, 19, 102.5, 103.0),
        seg("CARRY", 19, 33, 103.0, 106.0, linebreak=True),
    ])
    events = chain_to_events(chain, NAMES, attack_dir_home=1)
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "phase_sequence" and ev["team"] == "ENG"
    assert ev["metres_gained"] == 23.0
    assert ev["end_metres_from_line"] == 67.0
    assert ev["linebreaks"] == 1
    (std,) = RugbySport().translate(events)
    assert std.weight == 0.56
    assert std.team == "ENG" and std.t == 12.4


def test_kick_splits_chain_no_turnover():
    chain = make_chain([
        seg("CARRY", 10, 20, 100.0, 102.5),
        seg("KICK", 20, 60, 102.5, 103.1),
        seg("CARRY", 60, 55, 103.1, 106.0),  # receiver (away) attacks -x
    ])
    events = chain_to_events(chain, NAMES, attack_dir_home=1)
    assert [e["type"] for e in events] == ["phase_sequence", "phase_sequence"]
    kicker, receiver = events
    assert kicker["team"] == "ENG" and kicker["metres_gained"] == 50.0
    assert receiver["team"] == "WAL" and receiver["metres_gained"] == 5.0
    assert receiver["end_metres_from_line"] == 55.0  # 55m from left try line


def test_interception_splits_and_logs_turnover():
    chain = make_chain([
        seg("CARRY", 30, 40, 100.0, 102.0),
        seg("PASS", 40, 39, 102.0, 102.4, intercepted=True),
        seg("CARRY", 39, 25, 102.4, 105.0),
    ])
    events = chain_to_events(chain, NAMES, attack_dir_home=1)
    assert [e["type"] for e in events] == ["phase_sequence", "phase_sequence",
                                           "turnover_won"]
    assert events[2]["team"] == "WAL"
    assert events[1]["metres_gained"] == 14.0  # 39 -> 25 toward -x


def test_players_attached():
    s = seg("CARRY", 10, 20, 100.0, 102.5)
    s.players.append(PlayerTag(number=9, role="start", at_ts=100.1))
    events = chain_to_events(make_chain([s]), NAMES, attack_dir_home=1)
    assert events[0]["players"] == [{"number": 9, "role": "start"}]


def test_match_state_full_flow_trace_plus_taps():
    """Phase-4 exit criteria: traced + tap-annotated chain -> expected weight."""
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    m.mouse_down(LEFT + 10 * PX, 280, 100.0)
    for i in range(1, 151):  # 10m -> 20m carry over 2.5s at 60Hz
        m.mouse_move(LEFT + (10 + 10 * i / 150) * PX, 280, 100.0 + 2.5 * i / 150)
    m.key_down("9", 100.15)   # actor tapped just after chain start
    m.key_down("l", 101.2)    # linebreak mid-carry
    m.key_down("a", 102.6)    # authoritative chain end
    assert not m.recorder.active
    (ev,) = m.events
    # 10m gained, ends 80m out, 1 linebreak:
    # round((.15+.35*.25 + .3*.2)*1.25, 2) = 0.37
    assert ev["metres_gained"] == 10.0
    assert ev["end_metres_from_line"] == 80.0
    assert ev["linebreaks"] == 1
    assert ev["players"] == [{"number": 9, "role": "start"}]
    (std,) = RugbySport().translate([ev])
    assert std.weight == 0.37
    # evidence capture: raw inputs + segmentation debug snapshot per chain
    assert m.chain_seq == 1
    assert m.last_chain is not None
    assert len(m.last_raw["points"]) == 151
    assert m.last_debug["segments"]


def test_discrete_events_and_conversion_window():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=100.0)
    m.key_down("t", 160.0)                    # ENG try at 1'
    m.key_down("c", 200.0)                    # conversion within window
    m.key_down("v", 260.0)                    # WAL turnover; possession flips
    assert m.possession == "away"
    m.key_down("b", 300.0)                    # sin bin: against non-possessing ENG
    types = [(e["type"], e["team"]) for e in m.events]
    assert types == [("try", "ENG"), ("conversion", "ENG"),
                     ("turnover_won", "WAL"), ("sin_bin", "ENG")]


def test_synthetic_match_round_trips_through_engine():
    m = MatchState("ENG", "WAL")
    m.clock.start(t=0.0)
    m.key_down("t", 60.0)
    m.key_down("n", 120.0)  # note: N logs for possessing team (still home)
    chain = make_chain([seg("CARRY", 10, 30, 200.0, 205.0)], team="away")
    m.events.extend(chain_to_events(chain, NAMES, attack_dir_home=1))
    std = RugbySport().translate(m.events)
    MomentumEngine(half_life_minutes=4.5).compute(std, "ENG", "WAL", 82)  # must not raise
