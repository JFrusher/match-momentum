"""Grid-sweep segmentation thresholds over the fixture corpus.

Runs every scenario in fixtures.SCENARIOS (plus promoted real traces in
tests/traces/) under each threshold combination and prints a pass-count
table. Informs manual tuning of config.py; NEVER writes config — read the
table, decide, edit by hand.

Run: .venv/Scripts/python -m tracer.sweep      Edit GRID to change knobs.
"""

import itertools

from . import config, fixtures

GRID = {
    "ANGLE_THRESHOLD_DEG": [45, 55, 65],
    "SPEED_RATIO_THRESHOLD": [2.0, 2.5, 3.0],
    "MIN_SEGMENT_MS": [250, 350, 450],
}


def score():
    """(passed, total, failed names) over the whole corpus at current config."""
    cases = fixtures.iter_cases()
    failed = [name for name, run_case in cases if run_case()]
    return len(cases) - len(failed), len(cases), failed


def main():
    keys = list(GRID)
    baseline = tuple(getattr(config, k) for k in keys)
    rows = []
    try:
        for combo in itertools.product(*(GRID[k] for k in keys)):
            for k, v in zip(keys, combo):
                setattr(config, k, v)
            passed, total, failed = score()
            rows.append((passed, total, combo, failed))
    finally:
        for k, v in zip(keys, baseline):
            setattr(config, k, v)

    rows.sort(key=lambda r: -r[0])
    for passed, total, combo, failed in rows:
        label = " ".join(f"{k.split('_')[0]}={v}" for k, v in zip(keys, combo))
        mark = "  (baseline)" if combo == baseline else ""
        tail = ""
        if failed:
            shown = ", ".join(failed[:4]) + ("..." if len(failed) > 4 else "")
            tail = f"  fail: {shown}"
        print(f"{label:<38} {passed}/{total}{mark}{tail}")


if __name__ == "__main__":
    main()
