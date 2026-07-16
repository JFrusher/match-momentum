"""PlayChain -> raw rugby event dict(s). Pure translation, no UI.

Team attribution walks the chain: a carry never flips possession, a kick
always does (receiver is the opposing team), an intercepted pass does. Each
flip splits the chain; every sub-chain becomes one phase_sequence dict in
the exact shape RugbySport.translate() consumes. An interception also logs
turnover_won for the gaining team; a kick does not (tactical choice, not a
forced error).

`weight` is never emitted — translators/rugby_weights.json and
_territory_weight() stay the single source of truth.
"""

from .geometry import PitchCalibration


def _other(team):
    return "away" if team == "home" else "home"


def assign_teams(segments, start_team: str) -> str:
    """Set each segment's team in place; return who has possession after."""
    team = start_team
    for seg in segments:
        seg.team = team
        if seg.action == "KICK" or (seg.action == "PASS" and seg.intercepted):
            team = _other(team)
    return team


def chain_to_events(chain, team_names: dict, attack_dir_home: int,
                    cal: PitchCalibration = PitchCalibration()) -> list[dict]:
    """chain.segments must already be tap-applied and team-assigned."""
    if not chain.segments:
        return []
    t0 = chain.t0

    def minute_at(t):
        return round(chain.start_minute + (t - t0) / 60, 1)

    # split into runs of consecutive same-team segments
    subs, current = [], [chain.segments[0]]
    for seg in chain.segments[1:]:
        if seg.team == current[-1].team:
            current.append(seg)
        else:
            subs.append(current)
            current = [seg]
    subs.append(current)

    out = []
    for i, sub in enumerate(subs):
        team = sub[0].team
        attack_dir = attack_dir_home if team == "home" else -attack_dir_home
        start_pt, end_pt = sub[0].points[0], sub[-1].points[-1]
        ev = {
            "type": "phase_sequence",
            "team": team_names[team],
            "minute": minute_at(sub[0].start_t),
            "metres_gained": cal.metres_gained(start_pt.x, end_pt.x, attack_dir),
            "end_metres_from_line": cal.end_metres_from_line(end_pt.x, attack_dir),
            "linebreaks": sum(1 for s in sub if s.linebreak),
        }
        players = [{"number": p.number, "role": p.role}
                   for s in sub for p in s.players]
        if players:
            ev["players"] = players  # harmless extra, ignored by the translator
        out.append(ev)
        if i > 0 and subs[i - 1][-1].action == "PASS":  # team changed on an interception
            out.append({
                "type": "turnover_won",
                "team": team_names[team],
                "minute": minute_at(sub[0].start_t),
            })
    return out
