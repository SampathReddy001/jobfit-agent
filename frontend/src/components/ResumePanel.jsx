import { useRef, useState } from "react";
import { api } from "../api.js";

export default function ResumePanel({ sessionId, resume, onUploaded }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function upload(file) {
    if (!file || !sessionId) return;
    setError("");
    setUploading(true);
    try {
      onUploaded(await api.uploadResume(sessionId, file));
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="panel resume" aria-labelledby="resume-heading">
      <h2 id="resume-heading">Your resume</h2>

      <div
        className={`dropzone${dragging ? " dragging" : ""}${resume ? " filled" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files[0]);
        }}
      >
        {resume ? (
          <p className="dropzone-file">
            <strong>{resume.filename}</strong>
            <span>{resume.characters.toLocaleString()} characters read</span>
          </p>
        ) : (
          <p>Drop a PDF or text resume here. It stays in this session only.</p>
        )}
        <button
          className="button button-quiet"
          onClick={() => input.current?.click()}
          disabled={!sessionId || uploading}
        >
          {uploading ? "Reading…" : resume ? "Replace resume" : "Choose file"}
        </button>
        <input
          ref={input}
          type="file"
          accept=".pdf,.txt,.md"
          hidden
          onChange={(e) => {
            upload(e.target.files[0]);
            e.target.value = "";
          }}
        />
      </div>

      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}

      {resume ? (
        <div className="detected">
          <h3>Skills found ({resume.skills.length})</h3>
          {resume.skills.length ? (
            <ul className="chips">
              {resume.skills.map((s) => (
                <li key={s} className="chip">
                  {s}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              No known skills detected. The agent can still read your resume, but scores will be less useful.
            </p>
          )}
        </div>
      ) : null}

      <div className="howto">
        <h3>How it works</h3>
        <ol>
          <li>Upload your resume.</li>
          <li>Paste a job link or description into the chat.</li>
          <li>Get a fit score, your gaps, and a tailored cover letter.</li>
        </ol>
      </div>
    </section>
  );
}
