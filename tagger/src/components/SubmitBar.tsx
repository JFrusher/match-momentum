import { useMatchStore } from "../store/matchStore";
import { useSportConfig } from "../hooks/useSportConfig";
import { eventLabel } from "../sport-config";

export function SubmitBar() {
  const config = useSportConfig();
  const teamNames = useMatchStore((s) => s.teamNames);
  const stagedTeam = useMatchStore((s) => s.stagedTeam);
  const stagedType = useMatchStore((s) => s.stagedType);
  const stagedModifier = useMatchStore((s) => s.stagedModifier);
  const submitStaged = useMatchStore((s) => s.submitStaged);

  function teamLabelFor(team: string | null): string {
    if (team === "home") return teamNames.home;
    if (team === "away") return teamNames.away;
    if (team === "neutral") return config.teamColumn.neutralLabel;
    return "—";
  }

  const typeLabel = stagedType ? eventLabel(config, stagedType) : "—";

  return (
    <div className="submit-bar">
      <span className="staged-preview">
        {teamLabelFor(stagedTeam)} &rarr; {typeLabel}
        {stagedModifier ? ` (${stagedModifier})` : ""}
      </span>
      <button className="submit-button" disabled={!stagedTeam || !stagedType} onClick={submitStaged}>
        Submit <kbd>Enter</kbd>
      </button>
    </div>
  );
}
