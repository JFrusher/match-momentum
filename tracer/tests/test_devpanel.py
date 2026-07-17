"""format_report is the dev panel's pure core — test it off-UI."""

from tracer import fixtures
from tracer.devpanel import format_report
from tracer.match_state import MatchState


def _run(name):
    m = MatchState("H", "A")
    m.clock.start(t=0.0)
    fixtures.inject(m, fixtures.SCENARIOS[name])
    return m


def test_format_report_committed_chain():
    m = _run("carry_pass_carry")
    r = format_report(m.last_debug, m.last_chain)
    assert "committed" in r and "segments:" in r and "boundaries:" in r
    assert "rule=" in r and "m/s" in r


def test_format_report_rejected_chain():
    m = _run("accidental_twitch")
    r = format_report(m.last_debug, m.last_chain)
    assert "REJECTED" in r and "net movement" in r


def test_format_report_shows_hint_relabel():
    m = _run("hint_k")
    r = format_report(m.last_debug, m.last_chain)
    assert "CARRY->KICK (hint)" in r
