"""Dev drawer: per-chain evidence report + fixture replay + trace capture.

Enabled via ?dev=1 or `python -m tracer.app <port> dev`. Shows exactly what
the recognizer decided about each chain and why (segmentation.last_debug),
replays any fixture or saved trace through the real pipeline, and snapshots
the last chain's raw inputs to tracer/dev_traces/ for offline replay or
promotion to a regression (recipe in README).
"""

import json
import time

from nicegui import ui

from . import autosave, fixtures

MAX_CANDIDATE_LINES = 15


def _score_table(ev: dict) -> list[str]:
    """Per-feature contribution rows: squashed value x weight per scored class."""
    from . import features
    out = [f"     {'feature':<10}{'sq':>7}"
           + "".join(f"{'w' + c[0]:>7}{'->' + c[0]:>8}" for c in features.SCORED_CLASSES)]
    for f in features.FEATURES:
        sq = ev["features"][f]
        row = f"     {f:<10}{sq:>7.3f}"
        for cls in features.SCORED_CLASSES:
            _, weights = features.class_weights(cls)
            row += f"{weights[f]:>7.1f}{weights[f] * sq:>+8.2f}"
        out.append(row)
    scores, probs = ev["scores"], ev["probs"]
    out.append("     scores " + " ".join(f"{c[0]}={scores[c]:+.2f}" for c in scores)
               + " | probs " + " ".join(f"{c[0]}={probs[c]:.2f}" for c in probs)
               + f" | conf {ev['confidence']:.2f}")
    return out


def format_report(debug: dict, chain) -> str:
    """Monospace block of everything the recognizer decided and why."""
    d = debug
    lines = [f"== {chain.chain_id if chain else 'no chain'}"
             f" | {d.get('n_points', 0)} pts"
             f" | {d.get('duration_s', 0):.2f}s"
             f" | {d.get('hz', 0):.1f} Hz"
             f" | net {d.get('net_px', 0):.0f}px"
             f" | {'committed' if chain else 'REJECTED'}"]
    if d.get("rejected"):
        lines.append(f"  rejected: {d['rejected']}")
        return "\n".join(lines)

    final = [s.action for s in chain.segments] if chain else []
    lines.append("segments:")
    for i, ev in enumerate(d.get("segments", [])):
        label = ev["action_geo"]
        if i < len(final) and final[i] != ev["action_geo"]:
            label = f"{ev['action_geo']}->{final[i]} (hint)"
        arrow = "->" if ev["attack_dir"] > 0 else "<-"
        lines.append(f"  #{i} {label:<20} rule={ev['rule']:<24}"
                     f" fwd {ev['forward_px']:+7.1f}px lat {ev['lateral_px']:+7.1f}px"
                     f" {ev['duration_s']:.2f}s {ev['speed_mps']:.1f}m/s"
                     f" {ev['n_points']}pts atk{arrow}")
        if "features" in ev:
            lines += _score_table(ev)

    cands, picked = d.get("candidates", []), d.get("picked", [])
    picked_i = {p["i"] for p in picked}
    lines.append(f"boundaries: {len(cands)} candidates -> {len(picked)} picked")
    b = d.get("boundary")
    if b:
        lines.append(f"  baseline: angle {b['angle_base']:.1f}deg (med {b['med_angle']:.1f})"
                     f" ratio {b['ratio_base']:.2f} (med {b['med_ratio']:.2f})"
                     f" accept>={b['accept']:.2f}")
        for n in b.get("near_misses", []):
            lines.append(f"  near-miss i={n['i']} score={n['score']:.2f}"
                         f" angle={n['angle']:.1f} ratio={n['ratio']:.2f}")
    for c in cands[:MAX_CANDIDATE_LINES]:
        mark = "picked" if c["i"] in picked_i else "candidate"
        lines.append(f"  i={c['i']} @{c['t']:.2f}s angle={c['angle']:.1f}"
                     f" ratio={c['ratio']:.2f} strength={c['strength']:.2f}"
                     f" -> {mark}")
    if len(cands) > MAX_CANDIDATE_LINES:
        lines.append(f"  ... and {len(cands) - MAX_CANDIDATE_LINES} more candidates")
    lines += [f"  {note}" for note in d.get("boundary_notes", [])]

    if d.get("taps"):
        lines.append("taps:")
        lines += [f"  {t}" for t in d["taps"]]
    return "\n".join(lines)


def _trace_files():
    if not fixtures.DEV_TRACES.is_dir():
        return []
    return [f"file:{f.name}" for f in sorted(fixtures.DEV_TRACES.glob("*.json"))]


def build_dev_panel(match):
    """Right drawer: replay controls + rolling evidence log."""
    options = sorted(fixtures.SCENARIOS) + _trace_files()
    with ui.right_drawer(value=True, fixed=True).props("width=560 bordered"):
        ui.label("Live Trace dev").classes("text-lg font-bold")
        with ui.row().classes("items-center gap-2 w-full"):
            sel = ui.select(options, value=options[0], label="fixture") \
                .classes("grow")

            def replay():
                name = sel.value
                if not name:
                    return
                if name.startswith("file:"):
                    d = json.loads((fixtures.DEV_TRACES / name[5:])
                                   .read_text(encoding="utf-8"))
                    match.possession = d.get("possession", match.possession)
                    match.attack_dir_home = d.get("attack_dir_home",
                                                  match.attack_dir_home)
                    ts = ([t for _, _, t in d["points"]]
                          + [t for _, t in d.get("taps", [])]
                          + [t for iv in d.get("shift", []) for t in iv])
                    t0 = time.monotonic() - max(ts, default=0.0) - 0.5
                    fixtures.inject_raw(match, d["points"], d.get("taps", ()),
                                        d.get("shift", ()), t0=t0)
                else:
                    sc = fixtures.SCENARIOS[name]
                    match.possession = sc.possession
                    match.attack_dir_home = sc.attack_dir
                    ts = ([sum(sc.durations)] + [t for t, _ in sc.taps]
                          + [t for iv in sc.shift for t in iv])
                    t0 = time.monotonic() - max(ts) - 0.5
                    fixtures.inject(match, sc, t0=t0)

            def save():
                raw = match.last_raw
                if not raw or not raw["points"]:
                    ui.notify("no trace to save", type="warning")
                    return
                t0 = raw["points"][0][2]
                data = {**raw,
                        "points": [[x, y, round(t - t0, 4)]
                                   for x, y, t in raw["points"]],
                        "taps": [[k, round(t - t0, 4)] for k, t in raw["taps"]],
                        "shift": [[round(a - t0, 4), round(b - t0, 4)]
                                  for a, b in raw["shift"]]}
                path = (fixtures.DEV_TRACES
                        / f"trace-{time.strftime('%Y%m%d-%H%M%S')}.json")
                autosave.save_session(data, path)
                sel.options = sorted(fixtures.SCENARIOS) + _trace_files()
                sel.update()
                ui.notify(f"saved {path.name}", type="positive")

            ui.button("Replay", on_click=replay)
            ui.button("Save last trace", on_click=save)
        log = ui.log(max_lines=600).classes("w-full font-mono text-xs") \
            .style("height:72vh")

        seen = {"seq": 0}

        def poll():
            # poll chain_seq, not on_commit: rejected chains must report too
            if match.chain_seq != seen["seq"]:
                seen["seq"] = match.chain_seq
                for line in format_report(match.last_debug,
                                          match.last_chain).splitlines():
                    log.push(line)
                log.push("")

        ui.timer(0.3, poll)
