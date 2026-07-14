import { useMatchStore } from "../store/matchStore";
import { eventItems, teamNames } from "../data/rugbyInline";

function teamLabelFor(team: string | null): string {
  if (team === "home") return teamNames.home;
  if (team === "away") return teamNames.away;
  if (team === "neutral") return "Neutral";
  return "—";
}

export function SubmitBar() {
  const stagedTeam = useMatchStore((s) => s.stagedTeam);
  const stagedType = useMatchStore((s) => s.stagedType);
  const stagedModifier = useMatchStore((s) => s.stagedModifier);
  const submitStaged = useMatchStore((s) => s.submitStaged);

  const typeLabel = eventItems.find((i) => i.key === stagedType)?.label ?? "—";

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
