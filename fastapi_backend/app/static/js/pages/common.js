import { confirmAction, escapeHtml, modal, pageHeading, table, toast } from "../ui.js";

export async function directoryPage(target, api, user, config) {
  const canWrite = ["admin", "manager"].includes(user.role) || (config.path === "customers" && user.role === "cashier");
  const canDelete = user.role === "admin";
  async function render() {
    const rows = await api.get(`/${config.path}`);
    const data = Array.isArray(rows) ? rows : rows.items || [];
    const columns = config.columns.map(([key, label]) => ({ key, label }));
    const addButton = canWrite ? '<button class="btn" id="add-record">Add record</button>' : "";
    target.innerHTML = `${pageHeading(config.title, addButton)}${table(columns, data, row => {
      const id = row[config.id];
      return `${canWrite ? `<button class="btn secondary small" data-edit="${id}">Edit</button> ` : ""}${canDelete ? `<button class="btn danger small" data-delete="${id}">Delete</button>` : ""}`;
    })}`;
    target.querySelector("#add-record")?.addEventListener("click", () => edit());
    target.querySelectorAll("[data-edit]").forEach(button => button.onclick = () => edit(data.find(row => String(row[config.id]) === button.dataset.edit)));
    target.querySelectorAll("[data-delete]").forEach(button => button.onclick = async () => {
      if (!confirmAction("Delete this record? Related business data may prevent deletion.")) return;
      await api.delete(`/${config.path}/${button.dataset.delete}`);
      toast("Record deleted");
      await render();
    });
  }
  async function edit(row = {}) {
    const values = {};
    if (config.related) await Promise.all(config.related.map(async relation => { values[relation.name] = await api.get(relation.path); }));
    const fields = config.fields.map(field => {
      if (field.related) return { ...field, options: values[field.related].map(item => ({ value: item[field.valueKey], label: item[field.labelKey] })) };
      return field;
    });
    const data = await modal(`${row[config.id] ? "Edit" : "Add"} ${config.singular}`, fields, row);
    if (!data) return;
    if (row[config.id]) await api.put(`/${config.path}/${row[config.id]}`, data);
    else await api.post(`/${config.path}`, data);
    toast("Changes saved");
    await render();
  }
  await render();
}

export function csvDownload(filename, rows) {
  if (!rows.length) { toast("There are no rows to export", true); return; }
  const headers = Object.keys(rows[0]);
  const quote = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [headers, ...rows.map(row => headers.map(key => row[key]))].map(line => line.map(quote).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url; link.download = filename; link.click();
  URL.revokeObjectURL(url);
}

export function safeText(value) {
  return escapeHtml(value);
}
