import { useMatchStore } from "../store/matchStore";
import { SPORT_CONFIGS, type SportConfig } from "../sport-config";

export function useSportConfig(): SportConfig {
  const sportKey = useMatchStore((s) => s.sportKey);
  return SPORT_CONFIGS[sportKey];
}
