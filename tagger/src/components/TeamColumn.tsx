import { useMatchStore } from "../store/matchStore";
import { teamNames } from "../data/rugbyInline";
import type { TeamRole } from "../store/types";

const TEAM_OPTIONS: { role: TeamRole; label: string; hotkey: string }[] = [
  { role: "home", label: teamNames.home, hotkey: "Z" },
  { role: "away", label: teamNames.away, hotkey: "X" },
  { role: "neutral", label: "Neutral", hotkey: "C" },
];

export function TeamColumn() {
  const stagedTeam = useMatchStore((s) => s.stagedTeam);
  const setStagedTeam = useMatchStore((s) => s.setStagedTeam);

  return (
    <div className="column team-column">
      <h2>Team</h2>
      {TEAM_OPTIONS.map((opt) => (
        <button
          key={opt.role}
          className={stagedTeam === opt.role ? "selected" : ""}
          onClick={() => setStagedTeam(opt.role)}
        >
          <kbd>{opt.hotkey}</kbd> {opt.label}
        </button>
      ))}
    </div>
  );
}
