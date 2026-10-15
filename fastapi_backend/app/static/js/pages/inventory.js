import { badge, escapeHtml, modal, pageHeading, table, toast } from "../ui.js";

export default async function inventoryPage(target, api, user) {
  const [stores, products] = await Promise.all([api.get("/stores"), api.get("/products")]);
  async function render() {
    const params = new URLSearchParams();
    const store = target.querySelector("#store-filter")?.value;
    const status = target.querySelector("#status-filter")?.value;
    if (store) params.set("store_id", store);
    if (status) params.set("status", status);
    const rows = await api.get(`/inventory${params.size ? `?${params}` : ""}`);
    target.innerHTML = `${pageHeading("Inventory", ["admin", "manager"].includes(user.role) ? '<button id="adjust" class="btn">Adjust stock</button>' : "")}<div class="toolbar"><select id="store-filter"><option value="">All stores</option>${stores.map(item => `<option value="${item.store_id}">${escapeHtml(item.store_name)}</option>`).join("")}</select><select id="status-filter"><option value="">All stock statuses</option>${["OK", "REORDER", "CRITICAL", "OUT OF STOCK"].map(item => `<option>${item}</option>`).join("")}</select><button id="filter" class="btn secondary">Filter</button></div>${table([{ key: "store_name", label: "Store" }, { key: "sku", label: "SKU" }, { key: "product_name", label: "Product" }, { key: "quantity_on_hand", label: "On hand" }, { key: "reorder_level", label: "Reorder at" }, { key: "stock_status", label: "Status", badge: true }], rows)}`;
    if (store) target.querySelector("#store-filter").value = store;
    if (status) target.querySelector("#status-filter").value = status;
    target.querySelector("#filter").onclick = render;
    target.querySelector("#adjust")?.addEventListener("click", adjust);
  }
  async function adjust() {
    const data = await modal("Adjust stock", [
      { name: "store_id", label: "Store", options: stores.map(row => ({ value: row.store_id, label: row.store_name })) },
      { name: "product_id", label: "Product", options: products.map(row => ({ value: row.product_id, label: `${row.sku} — ${row.product_name}` })) },
      { name: "delta", label: "Change (+/- units)", type: "number" },
      { name: "reason", label: "Reason" }
    ]);
    if (!data) return;
    await api.post("/inventory/adjust", data);
    toast("Stock adjusted");
    await render();
  }
  await render();
}
