"""Expected-vs-got over the emulated-input corpus (+ promoted real traces).

Every scenario in fixtures.SCENARIOS runs through a real MatchState via
instant injection; any committed trace in tests/traces/*.json joins
automatically (promotion recipe in tracer/README.md).
"""

import pytest

from tracer import fixtures

CASES = fixtures.iter_cases()


@pytest.mark.parametrize("name,run_case", CASES, ids=[n for n, _ in CASES])
def test_scenario(name, run_case):
    mismatches = run_case()
    assert mismatches == [], "\n".join(mismatches)
