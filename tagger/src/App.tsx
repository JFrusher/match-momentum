import { useHotkeys } from "./hooks/useHotkeys";
import { TeamColumn } from "./components/TeamColumn";
import { EventColumn } from "./components/EventColumn";
import { ModifierColumn } from "./components/ModifierColumn";
import { SubmitBar } from "./components/SubmitBar";
import { ClockController } from "./components/ClockController";
import { TimelineLog } from "./components/TimelineLog/TimelineLog";

export default function App() {
  useHotkeys();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Tagger</h1>
        <ClockController />
      </header>
      <main className="columns">
        <TeamColumn />
        <EventColumn />
        <ModifierColumn />
      </main>
      <SubmitBar />
      <TimelineLog />
    </div>
  );
}
