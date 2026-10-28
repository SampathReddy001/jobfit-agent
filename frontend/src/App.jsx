import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import ResumePanel from "./components/ResumePanel.jsx";
import Chat from "./components/Chat.jsx";
import Tracker from "./components/Tracker.jsx";

const TRACKER_TOOLS = new Set(["save_application", "update_application", "save_cover_letter"]);

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [startupError, setStartupError] = useState("");
  const [model, setModel] = useState("");
  const [resume, setResume] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("assistant");
  const [applications, setApplications] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const started = useRef(false);

  const loadApplications = useCallback(async () => {
    try {
      const data = await api.listApplications();
      setApplications(data.applications);
      setStatuses(data.statuses);
    } catch {
      /* the tracker view shows its own empty state */
    }
  }, []);

  useEffect(() => {
    if (started.current) return; // StrictMode runs effects twice in development
    started.current = true;
    (async () => {
      try {
        const health = await api.health();
        setModel(health.model);
        const { session_id } = await api.createSession();
        setSessionId(session_id);
      } catch (err) {
        setStartupError(err.message);
      }
      loadApplications();
    })();
  }, [loadApplications]);

  async function send(text) {
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const res = await api.chat(sessionId, text);
      setMessages((m) => [...m, { role: "assistant", text: res.reply, trace: res.trace }]);
      if (res.trace.some((s) => TRACKER_TOOLS.has(s.tool))) loadApplications();
    } catch (err) {
      setMessages((m) => [...m, { role: "error", text: err.message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">JobFit</span>
        </div>
        <p className="topbar-note">
          {model ? <>Agent running on {model}</> : "Connecting…"}
        </p>
      </header>

      <aside className="sidebar">
        <ResumePanel sessionId={sessionId} resume={resume} onUploaded={setResume} />
      </aside>

      <main className="main">
        <nav className="tabs" aria-label="Views">
          <button className={tab === "assistant" ? "tab active" : "tab"} onClick={() => setTab("assistant")}>
            Assistant
          </button>
          <button className={tab === "tracker" ? "tab active" : "tab"} onClick={() => setTab("tracker")}>
            Tracker <span className="tab-count">{applications.length}</span>
          </button>
        </nav>

        {startupError ? (
          <div className="banner banner-error" role="alert">
            <strong>The assistant couldn't start.</strong> {startupError}
          </div>
        ) : null}

        {tab === "assistant" ? (
          <Chat messages={messages} busy={busy} disabled={!sessionId} hasResume={!!resume} onSend={send} />
        ) : (
          <Tracker
            applications={applications}
            statuses={statuses}
            onChange={loadApplications}
            onAsk={(text) => {
              setTab("assistant");
              send(text);
            }}
          />
        )}
      </main>
    </div>
  );
}
