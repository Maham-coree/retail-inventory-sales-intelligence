import { pageHeading, table } from "../ui.js";
import { csvDownload } from "./common.js";

export default async function reorderPage(target, api) {
  const rows = await api.get("/reorder-alerts");
  target.innerHTML = `${pageHeading("Reorder alerts", '<div class="toolbar"><button id="export-csv" class="btn secondary">Export CSV</button><button id="create-orders" class="btn">Create purchase orders</button></div>')}${table([
    { key: "store_name", label: "Store" }, { key: "sku", label: "SKU" },
    { key: "product_name", label: "Product" }, { key: "supplier_name", label: "Supplier" },
    { key: "quantity_on_hand", label: "On hand" }, { key: "suggested_order_qty", label: "Suggested qty" },
    { key: "estimated_cost", label: "Est. cost" }, { key: "priority", label: "Priority", badge: true }
  ], rows)}`;
  target.querySelector("#export-csv").onclick = () => csvDownload("reorder-alerts.csv", rows);
  target.querySelector("#create-orders").onclick = async () => {
    const result = await api.post("/purchase-orders/from-reorder-alerts");
    window.dispatchEvent(new CustomEvent("app:toast", { detail: { message: `${result.created_po_ids.length} draft order(s) created` } }));
  };
}
