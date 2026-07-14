import { useMatchStore } from "../store/matchStore";
import { eventItems, modifierGroups } from "../data/rugbyInline";

const BADGES = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"];

export function ModifierColumn() {
  const stagedType = useMatchStore((s) => s.stagedType);
  const stagedModifier = useMatchStore((s) => s.stagedModifier);
  const stageModifier = useMatchStore((s) => s.stageModifier);
  const submitStaged = useMatchStore((s) => s.submitStaged);

  const stagedItem = eventItems.find((i) => i.key === stagedType);
  const group = stagedItem?.modifierGroupId ? modifierGroups[stagedItem.modifierGroupId] : undefined;

  return (
    <div className="column modifier-column">
      <h2>Modifier</h2>
      {!group && <p className="empty-hint">No modifiers for this event</p>}
      {group?.map((tag, i) => (
        <button
          key={tag.id}
          className={stagedModifier === tag.id ? "selected" : ""}
          onClick={() => {
            stageModifier(tag.id);
            submitStaged();
          }}
        >
          <kbd>{BADGES[i]}</kbd> {tag.label}
        </button>
      ))}
    </div>
  );
}
