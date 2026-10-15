import { escapeHtml, modal, pageHeading, table, toast } from "../ui.js";

export default async function purchaseOrdersPage(target, api) {
  async function render() {
    const orders = await api.get("/purchase-orders");
    target.innerHTML = `${pageHeading("Purchase orders", '<div class="toolbar"><button id="from-alerts" class="btn secondary">Create from reorder alerts</button><button id="create-po" class="btn">New purchase order</button></div>')}${table([{ key: "po_id", label: "PO #" }, { key: "supplier_id", label: "Supplier" }, { key: "store_id", label: "Store" }, { key: "order_date", label: "Order date" }, { key: "expected_date", label: "Expected" }, { key: "status", label: "Status", badge: true }], orders, row => `<button class="btn secondary small" data-view="${row.po_id}">View</button> ${row.status === "Ordered" ? `<button class="btn small" data-receive="${row.po_id}">Receive</button>` : ""}${["Draft", "Ordered"].includes(row.status) ? `<button class="btn secondary small" data-status="${row.po_id}" data-next="${row.status === "Draft" ? "Ordered" : "Cancelled"}">Set ${row.status === "Draft" ? "Ordered" : "Cancelled"}</button>` : ""}`)}`;
    target.querySelector("#create-po").onclick = create;
    target.querySelector("#from-alerts").onclick = async () => { const result = await api.post("/purchase-orders/from-reorder-alerts"); toast(`${result.created_po_ids.length} draft order(s) created`); await render(); };
    target.querySelectorAll("[data-view]").forEach(button => button.onclick = () => view(button.dataset.view));
    target.querySelectorAll("[data-receive]").forEach(button => button.onclick = async () => { await api.post(`/purchase-orders/${button.dataset.receive}/receive`); toast("Order received"); await render(); });
    target.querySelectorAll("[data-status]").forEach(button => button.onclick = async () => { await api.patch(`/purchase-orders/${button.dataset.status}/status?new_status=${button.dataset.next}`, {}); toast("Order status updated"); await render(); });
  }
  async function create() {
    const [suppliers, stores, products] = await Promise.all([api.get("/suppliers"), api.get("/stores"), api.get("/products")]);
    const data = await modal("New purchase order", [
      { name: "supplier_id", label: "Supplier", options: suppliers.map(row => ({ value: row.supplier_id, label: row.supplier_name })) },
      { name: "store_id", label: "Store", options: stores.map(row => ({ value: row.store_id, label: row.store_name })) },
      { name: "product_id", label: "Product", type: "number", options: products.map(row => ({ value: row.product_id, label: `${row.sku} — ${row.product_name}` })) },
      { name: "quantity", label: "Quantity", type: "number", min: "1" },
      { name: "unit_cost", label: "Unit cost", type: "number", step: "0.01", min: "0" }
    ]);
    if (!data) return;
    await api.post("/purchase-orders", { supplier_id: data.supplier_id, store_id: data.store_id, items: [{ product_id: data.product_id, quantity: data.quantity, unit_cost: data.unit_cost }] });
    toast("Purchase order created");
    await render();
  }
  async function view(id) {
    const { order, items } = await api.get(`/purchase-orders/${id}`);
    target.innerHTML = `${pageHeading(`Purchase order #${id}`, '<button id="back" class="btn secondary">Back</button>')}<section class="panel"><p>Status: ${escapeHtml(order.status)} · Supplier ${order.supplier_id} · Store ${order.store_id}</p>${table([{ key: "sku", label: "SKU" }, { key: "product_name", label: "Product" }, { key: "quantity", label: "Qty" }, { key: "unit_cost", label: "Unit cost" }, { key: "received_qty", label: "Received" }], items)}</section>`;
    target.querySelector("#back").onclick = render;
  }
  await render();
}
