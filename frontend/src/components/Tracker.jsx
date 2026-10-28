import { useState } from "react";
import { api } from "../api.js";

const STATUS_LABELS = {
  interested: "Interested",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
};

function CoverLetter({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <details className="cover">
      <summary>Cover letter</summary>
      <p className="cover-text">{text}</p>
      <button
        className="button button-quiet"
        onClick={async () => {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? "Copied" : "Copy cover letter"}
      </button>
    </details>
  );
}

export default function Tracker({ applications, statuses, onChange, onAsk }) {
  const [error, setError] = useState("");

  async function act(fn) {
    setError("");
    try {
      await fn();
      onChange();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!applications.length) {
    return (
      <section className="tracker empty">
        <h1>No saved jobs yet</h1>
        <p>After the assistant scores a job, ask it to "save this to my tracker" and it will appear here.</p>
      </section>
    );
  }

  return (
    <section className="tracker" aria-label="Application tracker">
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
      <ul className="apps">
        {applications.map((a) => (
          <li key={a.id} className={`app-row status-${a.status}`}>
            <div className="app-main">
              <h3>
                {a.job_url ? (
                  <a href={a.job_url} target="_blank" rel="noreferrer">
                    {a.role}
                  </a>
                ) : (
                  a.role
                )}
              </h3>
              <p className="app-company">{a.company}</p>
              {a.notes ? <p className="app-notes">{a.notes}</p> : null}
              {a.cover_letter ? <CoverLetter text={a.cover_letter} /> : null}
            </div>

            <div className="app-side">
              {a.fit_score != null ? (
                <p className="app-score">
                  <strong>{a.fit_score}</strong> fit
                </p>
              ) : null}
              <label className="visually-hidden" htmlFor={`status-${a.id}`}>
                Status for {a.role} at {a.company}
              </label>
              <select
                id={`status-${a.id}`}
                value={a.status}
                onChange={(e) => act(() => api.updateApplication(a.id, { status: e.target.value }))}
              >
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s] || s}
                  </option>
                ))}
              </select>
              <div className="app-actions">
                {!a.cover_letter ? (
                  <button
                    className="link-button"
                    onClick={() => onAsk(`Draft a cover letter for application #${a.id} (${a.role} at ${a.company}).`)}
                  >
                    Draft cover letter
                  </button>
                ) : null}
                <button
                  className="link-button link-danger"
                  onClick={() => {
                    if (confirm(`Remove ${a.role} at ${a.company} from your tracker?`)) {
                      act(() => api.deleteApplication(a.id));
                    }
                  }}
                >
                  Remove
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
