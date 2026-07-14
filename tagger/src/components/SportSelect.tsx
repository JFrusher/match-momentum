import { useMatchStore } from "../store/matchStore";
import { SPORT_CONFIGS } from "../sport-config";

export function SportSelect() {
  const sportKey = useMatchStore((s) => s.sportKey);
  const setSportKey = useMatchStore((s) => s.setSportKey);

  return (
    <select
      className="sport-select"
      value={sportKey}
      onChange={(e) => {
        setSportKey(e.target.value);
        // Return focus to the page so positional hotkeys work immediately.
        e.target.blur();
      }}
    >
      {Object.entries(SPORT_CONFIGS).map(([key, cfg]) => (
        <option key={key} value={key}>
          {cfg.displayName}
        </option>
      ))}
    </select>
  );
}
