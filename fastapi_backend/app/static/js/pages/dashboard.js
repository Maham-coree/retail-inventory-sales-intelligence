import { badge, escapeHtml, pageHeading, table } from "../ui.js";

export default async function dashboardPage(target, api) {
  const data = await api.get("/dashboard/summary");
  const money = value => new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(Number(value || 0));
  const cards = [
    ["Total sales", money(data.total_sales)], ["Invoices", data.invoices],
    ["Stock value", money(data.stock_value)], ["Items to reorder", data.to_reorder],
    ["Out of stock", data.out_of_stock]
  ];
  target.innerHTML = `${pageHeading("Business overview")}<section class="cards">${cards.map(([label, value]) => `<article class="card"><span class="card-label">${label}</span><strong class="card-value">${escapeHtml(value)}</strong></article>`).join("")}</section><section class="chart-grid"><article class="panel"><h3>Sales per day</h3><div class="chart-holder"><canvas id="daily-chart" aria-label="Daily sales line chart"></canvas></div></article><article class="panel"><h3>Top products</h3><div class="chart-holder"><canvas id="top-chart" aria-label="Top products bar chart"></canvas></div></article><article class="panel"><h3>Stock status</h3><div class="chart-holder"><canvas id="status-chart" aria-label="Stock status doughnut chart"></canvas></div></article><article class="panel"><h3>Revenue per store</h3><div class="chart-holder"><canvas id="store-chart" aria-label="Revenue per store chart"></canvas></div></article></section><section class="panel"><h3>Reorder preview</h3><div id="reorder-preview"></div></section>`;
  const Chart = window.Chart;
  if (Chart) {
    const chart = (id, type, labels, values, color) => new Chart(document.getElementById(id), {
      type, data: { labels, datasets: [{ label: "Value", data: values, backgroundColor: color, borderColor: color, tension: .3 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: type === "doughnut" } } }
    });
    chart("daily-chart", "line", data.sales_per_day.map(row => String(row.day)), data.sales_per_day.map(row => Number(row.revenue)), "#315fa8");
    chart("top-chart", "bar", data.top_products.map(row => row.product_name), data.top_products.map(row => Number(row.revenue)), "#4b81c9");
    chart("status-chart", "doughnut", data.stock_status_counts.map(row => row.stock_status), data.stock_status_counts.map(row => Number(row.count)), ["#16845b", "#b7791f", "#c05621", "#c53030"]);
    chart("store-chart", "bar", data.revenue_per_store.map(row => row.store_name), data.revenue_per_store.map(row => Number(row.revenue)), "#5976ad");
  }
  const alerts = await api.get("/reorder-alerts");
  target.querySelector("#reorder-preview").innerHTML = table([
    { key: "store_name", label: "Store" }, { key: "product_name", label: "Product" },
    { key: "quantity_on_hand", label: "On hand" }, { key: "priority", label: "Priority", badge: true }
  ], alerts.slice(0, 6));
}
