export const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));

export function toast(message, error = false) {
  const region = document.querySelector("#toast-region");
  const item = document.createElement("div");
  item.className = `toast${error ? " error" : ""}`;
  item.textContent = message;
  region.append(item);
  setTimeout(() => item.remove(), 4200);
}

window.addEventListener("app:toast", event => toast(event.detail.message, event.detail.error));

export function empty(message = "No records found.") {
  return `<div class="empty">${escapeHtml(message)}</div>`;
}

export function skeleton() {
  return '<div class="panel skeleton" role="status" aria-label="Loading">Loading data…</div>';
}

export function badge(value) {
  const key = String(value ?? "").toLowerCase();
  const cls = key === "ok" ? "ok" : key.includes("reorder") ? "reorder"
    : key.includes("critical") ? "critical" : key.includes("out of stock") ? "out"
      : key === "received" ? "ok" : key === "cancelled" ? "out" : "";
  return `<span class="badge ${cls}">${escapeHtml(value)}</span>`;
}

export function table(columns, rows, actions = row => "") {
  if (!rows?.length) return empty();
  return `<div class="table-wrap"><table><thead><tr>${columns.map(c => `<th>${escapeHtml(c.label)}</th>`).join("")}<th>Actions</th></tr></thead><tbody>${rows.map(row => `<tr>${columns.map(c => {
    const value = row[c.key];
    return `<td>${c.badge ? badge(value) : escapeHtml(value)}</td>`;
  }).join("")}<td>${actions(row)}</td></tr>`).join("")}</tbody></table></div>`;
}

export function modal(title, fields, initial = {}) {
  return new Promise(resolve => {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    const inputs = fields.map(field => {
      const value = initial[field.name] ?? field.value ?? "";
      const required = field.required === false ? "" : "required";
      const type = field.type || "text";
      return `<label class="field">${escapeHtml(field.label)}${field.options
        ? `<select name="${escapeHtml(field.name)}" ${required}>${field.options.map(option => `<option value="${escapeHtml(option.value)}" ${String(value) === String(option.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}</select>`
        : `<input name="${escapeHtml(field.name)}" type="${escapeHtml(type)}" value="${escapeHtml(value)}" ${field.step ? `step="${field.step}"` : ""} ${field.min ? `min="${field.min}"` : ""} ${required}>`}</label>`;
    }).join("");
    backdrop.innerHTML = `<form class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><h2 id="modal-title">${escapeHtml(title)}</h2><div class="form-grid">${inputs}</div><div class="modal-actions"><button type="button" class="btn secondary" data-cancel>Cancel</button><button class="btn" type="submit">Save</button></div></form>`;
    document.body.append(backdrop);
    const form = backdrop.querySelector("form");
    form.querySelector("[data-cancel]").onclick = () => { backdrop.remove(); resolve(null); };
    backdrop.onclick = event => { if (event.target === backdrop) { backdrop.remove(); resolve(null); } };
    form.onsubmit = event => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      fields.forEach(field => {
        if (field.type === "number") data[field.name] = Number(data[field.name]);
      });
      backdrop.remove();
      resolve(data);
    };
    form.querySelector("input,select")?.focus();
  });
}

export function confirmAction(message) {
  return window.confirm(message);
}

export function pageHeading(title, action = "") {
  return `<div class="page-heading"><h2>${escapeHtml(title)}</h2>${action}</div>`;
}

export function codeBlock(text) {
  return `<pre class="inline-code">${escapeHtml(text)}</pre>`;
}
