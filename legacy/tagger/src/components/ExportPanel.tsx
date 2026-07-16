import { useMatchStore } from "../store/matchStore";
import { validateForExport } from "../export/validate";
import { toMomentumJson } from "../export/toMomentumJson";
import { downloadJson } from "../export/download";

function slug(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "team";
}

export function ExportPanel() {
  const sportKey = useMatchStore((s) => s.sportKey);
  const teamNames = useMatchStore((s) => s.teamNames);
  const events = useMatchStore((s) => s.events);
  const setTeamName = useMatchStore((s) => s.setTeamName);

  const { errors, warnings, info } = validateForExport({ sportKey, teamNames, events });

  function handleDownload() {
    if (errors.length > 0) return;
    const data = toMomentumJson({ teamNames, events });
    downloadJson(data, `${slug(teamNames.home)}-vs-${slug(teamNames.away)}.json`);
  }

  return (
    <div className="export-panel">
      <h2>Export</h2>
      <div className="export-teams">
        <label>
          Home team
          <input
            type="text"
            value={teamNames.home}
            onChange={(e) => setTeamName("home", e.target.value)}
          />
        </label>
        <label>
          Away team
          <input
            type="text"
            value={teamNames.away}
            onChange={(e) => setTeamName("away", e.target.value)}
          />
        </label>
      </div>
      {(errors.length > 0 || warnings.length > 0 || info.length > 0) && (
        <ul className="export-checks">
          {errors.map((msg) => (
            <li key={msg} className="export-error">✕ {msg}</li>
          ))}
          {warnings.map((msg) => (
            <li key={msg} className="export-warning">⚠ {msg}</li>
          ))}
          {info.map((msg) => (
            <li key={msg} className="export-info">ℹ {msg}</li>
          ))}
        </ul>
      )}
      <button
        className="submit-button export-download"
        disabled={errors.length > 0}
        onClick={handleDownload}
      >
        Download momentum JSON
      </button>
    </div>
  );
}
