"""Catch drift between config.py's event-type strings and the translator's vocabulary."""

import json
from pathlib import Path

from tracer import config

WEIGHTS = json.loads(
    (Path(__file__).parents[2] / "translators" / "rugby_weights.json").read_text())

# types rugby.py's translate() special-cases rather than looking up in the table
SPECIAL = {"sin_bin", "phase_sequence"}


def test_discrete_event_types_known_to_translator():
    for etype in config.DISCRETE_EVENT_KEYS.values():
        assert etype in WEIGHTS or etype in SPECIAL, etype


def test_conversion_types_known_to_translator():
    for etype in config.CONVERSION_KEYS.values():
        assert etype in WEIGHTS, etype


def test_no_key_collisions_across_vocab():
    groups = [set(config.TYPE_HINT_KEYS), {config.LINEBREAK_KEY},
              set(config.TEAM_KEYS), config.END_CHAIN_KEYS,
              set(config.DISCRETE_EVENT_KEYS), set(config.CONVERSION_KEYS),
              set("0123456789")]
    seen = set()
    for g in groups:
        assert not (g & seen), g & seen
        seen |= g
