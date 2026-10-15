const base = window.RETAIL_API_BASE ?? "";

export const authStore = {
  get token() { return sessionStorage.getItem("retail-token"); },
  get user() {
    try { return JSON.parse(sessionStorage.getItem("retail-user") || "null"); }
    catch { return null; }
  },
  save(token, user) {
    sessionStorage.setItem("retail-token", token);
    sessionStorage.setItem("retail-user", JSON.stringify(user));
  },
  clear() {
    sessionStorage.removeItem("retail-token");
    sessionStorage.removeItem("retail-user");
  }
};

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authStore.token) headers.set("Authorization", `Bearer ${authStore.token}`);
  if (options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${base}${path}`, { ...options, headers });
  if (response.status === 401 && !path.startsWith("/auth/login")) {
    authStore.clear();
    if (location.hash !== "#login") location.hash = "#login";
  }
  const type = response.headers.get("content-type") || "";
  const body = response.status === 204 ? null : type.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const detail = body && typeof body === "object" ? body.detail : body;
    const message = Array.isArray(detail) ? detail.map(item => item.msg).join("; ")
      : typeof detail === "string" ? detail : `Request failed (${response.status})`;
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message, error: true } }));
    throw new Error(message);
  }
  return body;
}

export const api = {
  get: path => request(path),
  post: (path, body) => request(path, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: path => request(path, { method: "DELETE" }),
  form: (path, body) => {
    const form = new URLSearchParams(body);
    return request(path, { method: "POST", body: form });
  }
};
