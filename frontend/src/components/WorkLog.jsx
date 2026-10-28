import { useState } from "react";

const LABELS = {
  get_resume: "Read your resume",
  fetch_job_posting: "Opened the job posting",
  save_job_description: "Saved the job description",
  match_skills: "Scored your fit",
  find_learning_resources: "Looked up learning resources",
  save_application: "Saved to your tracker",
  list_applications: "Checked your tracker",
  update_application: "Updated an application",
  save_cover_letter: "Attached the cover letter",
};

function SkillMatch({ result }) {
  const groups = [
    ["Matched", result.matched_required, "hit"],
    ["Missing", result.missing_required, "gap"],
    ["Bonus matched", result.matched_nice_to_have, "hit"],
    ["Bonus missing", result.missing_nice_to_have, "gap-soft"],
  ].filter(([, list]) => list?.length);

  return (
    <div className="match">
      {result.fit_score != null ? (
        <p className="score" aria-label={`Fit score ${result.fit_score} out of 100`}>
          <span className="score-value">{result.fit_score}</span>
          <span className="score-scale">/100 fit</span>
        </p>
      ) : null}
      {groups.map(([label, list, kind]) => (
        <div key={label} className="match-row">
          <span className="match-label">{label}</span>
          <ul className="chips">
            {list.map((s) => (
              <li key={s} className={`chip chip-${kind}`}>
                {s}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function describe(step) {
  const { tool, args, result } = step;
  if (result.error) return result.error;
  switch (tool) {
    case "fetch_job_posting":
      return result.title || args.url;
    case "save_job_description":
      return [result.title, result.company].filter(Boolean).join(" at ") || "Job saved";
    case "match_skills":
      return result.fit_score != null ? `${result.fit_score}/100` : "No known skills in the job post";
    case "get_resume":
      return `${result.detected_skills?.length ?? 0} skills detected`;
    case "find_learning_resources":
      return Object.keys(result.resources || {}).join(", ");
    case "save_application": {
      const app = result.saved || result.already_tracked;
      return `${app?.role} at ${app?.company}${result.already_tracked ? " (already tracked)" : ""}`;
    }
    case "update_application":
      return `#${result.updated?.id} is now ${result.updated?.status}`;
    case "list_applications":
      return `${result.count} tracked`;
    default:
      return "";
  }
}

export default function WorkLog({ steps }) {
  const [open, setOpen] = useState(false);
  const match = steps.find((s) => s.tool === "match_skills" && s.ok);

  return (
    <div className="worklog">
      {match ? <SkillMatch result={match.result} /> : null}
      <button className="worklog-toggle" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {open ? "Hide" : "Show"} what I did ({steps.length} {steps.length === 1 ? "step" : "steps"})
      </button>
      {open ? (
        <ol className="steps">
          {steps.map((s, i) => (
            <li key={i} className={s.ok ? "step" : "step step-failed"}>
              <span className="step-name">{LABELS[s.tool] || s.tool}</span>
              <span className="step-detail">{describe(s)}</span>
              <details>
                <summary>
                  {s.tool} · {s.duration_ms} ms
                </summary>
                <pre>{JSON.stringify({ args: s.args, result: s.result }, null, 2)}</pre>
              </details>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
