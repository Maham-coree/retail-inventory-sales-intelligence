import { codeBlock, escapeHtml, pageHeading, table, toast } from "../ui.js";

export default async function reportsPage(target, api, user) {
  const reports = await api.get("/reports");
  const grouped = Object.groupBy ? Object.groupBy(reports, row => row.group) : reports.reduce((acc, row) => ((acc[row.group] ||= []).push(row), acc), {});
  target.innerHTML = `${pageHeading("Reports & SQL query portfolio", ["admin", "manager"].includes(user.role) ? '<button id="refresh-view" class="btn secondary">Refresh materialized view</button>' : "")}<div class="toolbar"><label>Report <select id="report-select">${Object.entries(grouped).map(([group, list]) => `<optgroup label="${escapeHtml(group)}">${list.map(row => `<option value="${escapeHtml(row.id)}">${escapeHtml(row.title)}</option>`).join("")}</optgroup>`).join("")}</select></label></div><section id="report-detail"></section>`;
  const load = async id => {
    const report = reports.find(row => row.id === id);
    const detail = target.querySelector("#report-detail");
    detail.innerHTML = `<section class="panel"><h3>Relational algebra</h3>${codeBlock(report.algebra)}<h3>SQL</h3>${codeBlock(report.sql)}<button class="btn secondary" id="explain">Show EXPLAIN</button><div id="plan"></div><h3>Results</h3><div id="results">Loading results…</div></section>`;
    const result = await api.get(`/reports/${encodeURIComponent(id)}`);
    detail.querySelector("#results").innerHTML = table(result.columns.map((label, index) => ({ key: String(index), label })), result.rows.map(row => Object.fromEntries(row.map((value, index) => [String(index), value]))), () => "");
    detail.querySelector("#explain").onclick = async () => {
      const data = await api.get(`/reports/${encodeURIComponent(id)}?explain=true`);
      detail.querySelector("#plan").innerHTML = codeBlock(data.plan.join("\n"));
    };
  };
  target.querySelector("#report-select").onchange = event => load(event.target.value);
  target.querySelector("#refresh-view")?.addEventListener("click", async () => { await api.post("/reports/materialized/refresh"); toast("Materialized view refreshed"); });
  await load(reports[0].id);
}
