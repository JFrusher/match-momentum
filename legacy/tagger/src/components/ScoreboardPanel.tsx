import { useMatchStore } from "../store/matchStore";

// Score = Σ(points of team's events) + manual override delta. The override
// ([ / ] hotkeys) never overwrites the computed total — it rides on top, so
// fixing a mistake later (edit/delete the event) still reconciles.
export function ScoreboardPanel() {
  const teamNames = useMatchStore((s) => s.teamNames);
  const events = useMatchStore((s) => s.events);
  const scoreOverride = useMatchStore((s) => s.scoreOverride);

  const computed = { home: 0, away: 0 };
  for (const ev of events) {
    if (ev.team === "home" || ev.team === "away") computed[ev.team] += ev.points;
  }
  const home = computed.home + scoreOverride.home;
  const away = computed.away + scoreOverride.away;

  return (
    <div className="scoreboard" title="[ / Shift+[ adjust home · ] / Shift+] adjust away">
      <span className="scoreboard-team">{teamNames.home}</span>
      <span className="scoreboard-score">
        {home} — {away}
      </span>
      <span className="scoreboard-team">{teamNames.away}</span>
      {(scoreOverride.home !== 0 || scoreOverride.away !== 0) && (
        <span className="scoreboard-override">
          (adj {scoreOverride.home >= 0 ? "+" : ""}{scoreOverride.home} / {scoreOverride.away >= 0 ? "+" : ""}{scoreOverride.away})
        </span>
      )}
    </div>
  );
}
