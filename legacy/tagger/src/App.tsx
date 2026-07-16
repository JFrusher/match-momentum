import { useHotkeys } from "./hooks/useHotkeys";
import { useAutosave } from "./hooks/useAutosave";
import { TeamColumn } from "./components/TeamColumn";
import { EventColumn } from "./components/EventColumn";
import { ModifierColumn } from "./components/ModifierColumn";
import { SubmitBar } from "./components/SubmitBar";
import { ClockController } from "./components/ClockController";
import { SportSelect } from "./components/SportSelect";
import { ScoreboardPanel } from "./components/ScoreboardPanel";
import { NewMatchDialog } from "./components/NewMatchDialog";
import { FollowUpModal } from "./components/FollowUpModal";
import { DerivedInputPanel } from "./components/DerivedInputPanel";
import { TimelineLog } from "./components/TimelineLog/TimelineLog";
import { ExportPanel } from "./components/ExportPanel";

export default function App() {
  useHotkeys();
  useAutosave();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Tagger</h1>
        <SportSelect />
        <ScoreboardPanel />
        <ClockController />
        <NewMatchDialog />
      </header>
      <main className="columns">
        <TeamColumn />
        <EventColumn />
        <ModifierColumn />
      </main>
      <SubmitBar />
      <TimelineLog />
      <ExportPanel />
      <FollowUpModal />
      <DerivedInputPanel />
    </div>
  );
}
