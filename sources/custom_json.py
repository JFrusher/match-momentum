"""Reference DataSource adapter: the events.json shape used throughout this repo."""

import json

from .base import BaseDataSource


class CustomJSONSource(BaseDataSource):
    def parse(self, path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {
            "events": sorted(data["events"], key=lambda e: e["minute"]),
            "teams": data["teams"],
            "colors": data.get("colors", {}),
            "title": data.get("title"),
            "footer": data.get("footer", ""),
        }
