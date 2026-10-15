import { codeBlock, pageHeading, toast } from "../ui.js";

export default async function optimizationLabPage(target, api) {
  target.innerHTML = `${pageHeading("Query optimization lab")}<p class="muted">Seeds 200,000 rows in <code>retail.lab_orders</code> once, then compares plans before and after a temporary B-tree index.</p><div class="toolbar"><button id="seed" class="btn secondary">Seed lab data</button><input id="customer-ref" value="42" aria-label="Customer reference"><button id="run" class="btn">Run comparison</button></div><div id="output"></div>`;
  target.querySelector("#seed").onclick = async () => { const result = await api.post("/labs/optimization/seed"); toast(result.message); };
  target.querySelector("#run").onclick = async () => {
    const output = target.querySelector("#output");
    output.innerHTML = '<div class="panel skeleton">Running EXPLAIN ANALYZE…</div>';
    const result = await api.post(`/labs/optimization/run?customer_ref=${encodeURIComponent(target.querySelector("#customer-ref").value)}`);
    output.innerHTML = `<section class="chart-grid"><article class="panel"><h3>Before index · ${result.before_execution_ms ?? "—"} ms</h3>${codeBlock(result.before_plan.join("\n"))}</article><article class="panel"><h3>After index · ${result.after_execution_ms ?? "—"} ms</h3>${codeBlock(result.after_plan.join("\n"))}</article></section>`;
  };
}
