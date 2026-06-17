/**
 * VoxLingua Desktop — main application layout.
 *
 * Minimalist design: animated voice circle in center, chat below, gear top-right.
 */

import { useVoxLingua } from "./hooks/useVoxLingua";
import VoiceCircle from "./components/VoiceCircle";
import MessageList from "./components/MessageList";
import SettingsPanel from "./components/SettingsPanel";
import "./App.css";

export default function App() {
  const {
    status,
    messages,
    audioLevel,
    settings,
    engineConnected,
    toggleRecord,
    updateSettings,
  } = useVoxLingua();

  return (
    <div className="app">
      {/* background gradient glow */}
      <div className="app-bg" />

      {/* header */}
      <header className="app-header">
        <h1>VoxLingua</h1>
      </header>

      {/* main area — circle + chat */}
      <main className="app-main">
        <section className="circle-section">
          <VoiceCircle
            status={status}
            audioLevel={audioLevel}
            onToggle={toggleRecord}
            engineConnected={engineConnected}
          />
        </section>

        <section className="chat-section">
          <MessageList messages={messages} />
        </section>
      </main>

      {/* settings */}
      <SettingsPanel
        settings={settings}
        onUpdate={updateSettings}
        engineConnected={engineConnected}
      />
    </div>
  );
}
