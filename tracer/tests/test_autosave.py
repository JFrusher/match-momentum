import json
import os

from tracer.autosave import (clear_session, latest_session, load_session,
                             save_session, session_path)
from tracer.match_state import MatchState


def test_round_trip(tmp_path):
    f = tmp_path / "session.json"
    m = MatchState("ENG", "WAL")
    m.events.append({"type": "try", "team": "ENG", "minute": 3.0})
    save_session(m.to_dict(), f)
    restored = MatchState.from_dict(load_session(f))
    assert restored.team_names == {"home": "ENG", "away": "WAL"}
    assert restored.events == m.events
    assert not restored.clock.running  # always rehydrates paused


def test_interrupted_write_leaves_previous_file_intact(tmp_path):
    f = tmp_path / "session.json"
    save_session({"good": 1}, f)
    (f.with_suffix(".tmp")).write_text('{"partial', encoding="utf-8")  # simulated crash mid-write
    assert load_session(f) == {"good": 1}


def test_corrupt_or_missing_loads_none(tmp_path):
    f = tmp_path / "session.json"
    assert load_session(f) is None
    f.write_text("not json", encoding="utf-8")
    assert load_session(f) is None
    clear_session(f)
    clear_session(f)  # idempotent


def test_saved_file_is_valid_json(tmp_path):
    f = tmp_path / "s.json"
    save_session({"events": [], "teams": {"home": "A", "away": "B"}}, f)
    json.loads(f.read_text(encoding="utf-8"))


# --- one file per match, so a second game can't clobber the first ----------
def test_session_path_slugs_team_names():
    assert session_path("England", "New Zealand").name == "england_v_new_zealand.json"


def test_session_path_survives_punctuation_and_spaces():
    assert session_path("Côte d'Ivoire", "St. Helena").name.endswith(".json")
    assert "/" not in session_path("A/B", "C D").name


def test_latest_session_returns_the_newest(tmp_path):
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    save_session({"events": [1]}, old)
    save_session({"events": [2]}, new)
    os.utime(old, (1, 1))
    assert latest_session(tmp_path) == {"events": [2]}


def test_latest_session_with_no_sessions_is_none(tmp_path):
    assert latest_session(tmp_path) is None
