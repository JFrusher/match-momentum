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

from dataclasses import dataclass

from . import config
from .geometry import PitchCalibration

# Score types that end a possession and trigger a restart (scoring team
# receives). Conversions follow a try by the same team, so they don't
# independently determine the next possessor.
RESTART_SCORE_TYPES = ("try", "penalty_try", "penalty_kick", "drop_goal")


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


def infer_next_possession(chain_start_team: str, final_team: str,
                          scored_team) -> str:
    """Who has the ball for the NEXT chain, given how this one ended.

    - a score -> the scoring team receives the restart;
    - a kick/interception already flipped possession in-chain (final_team);
    - otherwise the possession was lost at the breakdown (knock-on / scrum /
      jackal = the coarse "turnover"), so it goes to the other side.
    ponytail: plain-end assumes possession lost; tap Z/X if it was retained
    (e.g. penalty won and played on).
    """
    if scored_team:
        return scored_team
    if final_team != chain_start_team:
        return final_team
    return _other(chain_start_team)


@dataclass(frozen=True)
class ChainOrigin:
    """How the next possession begins, and where to draw its chip."""
    reason: str
    team: str                      # "home"/"away" — who has the ball next
    mark: tuple | None = None      # (x_px, y_px) chip anchor; None = no chip
    alt_mark: tuple | None = None  # the other lawful mark, when there are two


def infer_origin(*, segments, chain_start_team, final_team, scored_team,
                 armed, attack_dir_home, cal: PitchCalibration = PitchCalibration()
                 ) -> ChainOrigin:
    """Read how this chain ended to decide how the next one starts.

    Everything here is derived from geometry the trace already contains, so
    the common cases need no extra input. What cannot be seen in a line — a
    penalty, a knock-on — is tapped instead and never reaches this function.
    """
    team = infer_next_possession(chain_start_team, final_team, scored_team)
    if scored_team:
        return ChainOrigin("restart", team, _halfway(cal))

    last = segments[-1]
    end = last.points[-1]
    if last.action == "KICK" and cal.ends_in_touch(end.y):
        if armed == "kick_to_touch":
            # a penalty to touch keeps the throw AND the ground, unlike an
            # open-play kick, which is why the armed case bypasses the law
            return ChainOrigin("lineout", chain_start_team, (end.x, end.y))
        kicker_dir = attack_dir_home if last.team == "home" else -attack_dir_home
        kick_from = last.points[0].x
        mark_x = cal.lineout_mark_x(kick_from, end.x, kicker_dir)
        # the other lawful mark: a bounce before the line makes it the exit
        # point, a kick on the full makes it the kick itself
        alt_x = end.x if mark_x == kick_from else kick_from
        return ChainOrigin("lineout", team, (mark_x, end.y), (alt_x, end.y))
    if last.action == "KICK":
        return ChainOrigin("kick_return", team)
    if any(s.intercepted for s in segments):
        return ChainOrigin("interception", team)
    return ChainOrigin("turnover_open", team, (end.x, end.y))


def _halfway(cal: PitchCalibration) -> tuple:
    return (cal.left_try_line_px + config.PITCH_LENGTH_M / 2 * cal.px_per_m,
            cal.width_px / 2)


def summarise(events: list[dict], actions: list[str]) -> str:
    """One-line commit summary for the UI toast — 'ENG · CARRY-PASS · 12m'.

    Reads the events the chain just produced rather than recomputing geometry,
    so the toast can never disagree with what was actually recorded.
    """
    if not events:
        return ""
    metres = sum(e.get("metres_gained", 0) for e in events)
    return f"{events[0]['team']} · {'-'.join(actions)} · {metres:g}m"


def compute_score(events, team_names: dict) -> dict:
    """Sum point-scoring events into {"home": int, "away": int}."""
    score = {"home": 0, "away": 0}
    name_to_key = {v: k for k, v in team_names.items()}
    for e in events:
        pts = config.POINTS.get(e.get("type"))
        key = name_to_key.get(e.get("team"))
        if pts and key:
            score[key] += pts
    return score


def chain_to_events(chain, team_names: dict, attack_dir_home: int,
                    cal: PitchCalibration = PitchCalibration(),
                    start_reason: str = None) -> list[dict]:
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
        if i == 0:
            # only the first sub-chain has an origin worth naming: later ones
            # exist because a kick or interception split this chain, which is
            # already recorded in the segment that did it
            ev["start_metres_from_line"] = cal.metres_from_line(
                start_pt.x, attack_dir)
            if start_reason:
                ev["start_reason"] = start_reason
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
