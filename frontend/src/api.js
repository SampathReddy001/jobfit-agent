// Small wrapper around fetch that turns API errors into readable messages.

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, options);
  } catch {
    throw new Error("Can't reach the JobFit server. Check that the backend is running on port 8000.");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join(", ") : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

const json = (method, data) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const api = {
  health: () => request("/health"),
  createSession: () => request("/sessions", { method: "POST" }),
  uploadResume: (sessionId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/sessions/${sessionId}/resume`, { method: "POST", body: form });
  },
  chat: (sessionId, message) => request(`/sessions/${sessionId}/chat`, json("POST", { message })),
  listApplications: () => request("/applications"),
  updateApplication: (id, patch) => request(`/applications/${id}`, json("PATCH", patch)),
  deleteApplication: (id) => request(`/applications/${id}`, { method: "DELETE" }),
};
