import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import WorkLog from "./WorkLog.jsx";

const STARTERS = [
  "Here's a job link: ",
  "How well do I fit this job? <paste the description>",
  "Which of my tracked jobs should I prioritize?",
];

export default function Chat({ messages, busy, disabled, hasResume, onSend }) {
  const [draft, setDraft] = useState("");
  const end = useRef(null);
  const box = useRef(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  function submit(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy || disabled) return;
    onSend(text);
    setDraft("");
  }

  return (
    <section className="chat" aria-label="Assistant">
      <div className="messages" aria-live="polite">
        {messages.length === 0 ? (
          <div className="empty">
            <h1>Will this job fit you?</h1>
            <p>
              {hasResume
                ? "Paste a job link or description and I'll score your fit, show your gaps and help you apply."
                : "Start by uploading your resume, then paste a job link or description here."}
            </p>
            <div className="starters">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  className="starter"
                  onClick={() => {
                    setDraft(s);
                    box.current?.focus();
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="msg msg-user">
              <p>{m.text}</p>
            </div>
          ) : m.role === "error" ? (
            <div key={i} className="msg msg-error" role="alert">
              <p>{m.text}</p>
            </div>
          ) : (
            <article key={i} className="msg msg-agent">
              {m.trace?.length ? <WorkLog steps={m.trace} /> : null}
              <div className="prose">
                <Markdown remarkPlugins={[remarkGfm]}>{m.text}</Markdown>
              </div>
            </article>
          ),
        )}

        {busy ? (
          <div className="msg msg-agent thinking" aria-label="The agent is working">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
            <span className="thinking-label">Working through your request</span>
          </div>
        ) : null}
        <div ref={end} />
      </div>

      <form className="composer" onSubmit={submit}>
        <label htmlFor="composer-input" className="visually-hidden">
          Message the assistant
        </label>
        <textarea
          id="composer-input"
          ref={box}
          value={draft}
          rows={2}
          placeholder={disabled ? "Waiting for the server…" : "Paste a job link or description, or ask a question"}
          disabled={disabled}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
        />
        <button className="button button-primary" type="submit" disabled={busy || disabled || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
