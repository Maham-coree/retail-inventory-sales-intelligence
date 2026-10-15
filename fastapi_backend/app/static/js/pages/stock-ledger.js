import { pageHeading, table } from "../ui.js";

export default async function ledgerPage(target, api) {
  async function render() {
    const product = target.querySelector("#product-id")?.value;
    const store = target.querySelector("#store-id")?.value;
    const type = target.querySelector("#movement-type")?.value;
    const params = new URLSearchParams();
    if (product) params.set("product_id", product);
    if (store) params.set("store_id", store);
    if (type) params.set("movement_type", type);
    const result = await api.get(`/stock-movements?${params}`);
    target.innerHTML = `${pageHeading("Stock ledger")}<div class="toolbar"><input id="product-id" type="number" placeholder="Product ID"><input id="store-id" type="number" placeholder="Store ID"><select id="movement-type"><option value="">All types</option>${["SALE", "PURCHASE", "ADJUSTMENT", "RETURN"].map(value => `<option>${value}</option>`).join("")}</select><button id="filter" class="btn secondary">Filter</button></div>${table([{ key: "created_at", label: "Date" }, { key: "store_name", label: "Store" }, { key: "sku", label: "SKU" }, { key: "product_name", label: "Product" }, { key: "movement_type", label: "Type" }, { key: "quantity", label: "Change" }, { key: "reference", label: "Reference" }], result.items)}`;
    if (product) target.querySelector("#product-id").value = product;
    if (store) target.querySelector("#store-id").value = store;
    if (type) target.querySelector("#movement-type").value = type;
    target.querySelector("#filter").onclick = render;
  }
  await render();
}
