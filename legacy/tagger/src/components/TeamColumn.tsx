import { useMatchStore } from "../store/matchStore";
import { useSportConfig } from "../hooks/useSportConfig";
import type { TeamRole } from "../store/types";

export function TeamColumn() {
  const config = useSportConfig();
  const teamNames = useMatchStore((s) => s.teamNames);
  const stagedTeam = useMatchStore((s) => s.stagedTeam);
  const setStagedTeam = useMatchStore((s) => s.setStagedTeam);

  const options: { role: TeamRole; label: string; hotkey: string }[] = [
    { role: "home", label: teamNames.home, hotkey: "Z" },
    { role: "away", label: teamNames.away, hotkey: "X" },
  ];
  if (config.teamColumn.includeNeutral) {
    options.push({ role: "neutral", label: config.teamColumn.neutralLabel, hotkey: "C" });
  }

  return (
    <div className="column team-column">
      <h2>Team</h2>
      {options.map((opt) => (
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
