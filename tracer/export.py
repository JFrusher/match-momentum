"""Final CustomJSONSource-shaped JSON writer."""

import json
from pathlib import Path

from .validate import validate_events


def build_payload(team_names: dict, events: list[dict], title: str = None,
                  footer: str = "Traced live with tracer/") -> dict:
    home, away = team_names["home"], team_names["away"]
    return {
        "teams": {"home": home, "away": away},
        "title": title or f"MATCH MOMENTUM  —  {home} vs {away}",
        "footer": footer,
        "events": sorted(events, key=lambda e: e["minute"]),
    }


def export_json(path, team_names: dict, events: list[dict]) -> list[str]:
    """Validate against the real pipeline, then write. Errors block the write."""
    errors = validate_events(events, team_names["home"], team_names["away"])
    if errors:
        return errors
    payload = build_payload(team_names, events)
    Path(path).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return []
