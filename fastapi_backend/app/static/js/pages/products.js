import { confirmAction, modal, pageHeading, table, toast } from "../ui.js";

const fields = [
  { name: "sku", label: "SKU" }, { name: "product_name", label: "Product name" },
  { name: "category_id", label: "Category", type: "number", related: "categories", valueKey: "category_id", labelKey: "category_name" },
  { name: "supplier_id", label: "Supplier", type: "number", related: "suppliers", valueKey: "supplier_id", labelKey: "supplier_name" },
  { name: "unit_cost", label: "Unit cost", type: "number", step: "0.01" },
  { name: "unit_price", label: "Unit price", type: "number", step: "0.01" },
  { name: "reorder_level", label: "Reorder level", type: "number", min: "0" },
  { name: "reorder_quantity", label: "Reorder quantity", type: "number", min: "1" },
  { name: "barcode", label: "Barcode", required: false },
  { name: "is_active", label: "Active (1 = yes)", type: "number", min: "0", max: "1" }
];

export default async function productsPage(target, api, user) {
  let search = "";
  async function render() {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    const products = await api.get(`/products${query}`);
    const rows = Array.isArray(products) ? products : products.items;
    target.innerHTML = `${pageHeading("Product catalogue", ["admin", "manager"].includes(user.role) ? '<button id="add" class="btn">Add product</button>' : "")}<div class="toolbar"><input id="search" type="search" placeholder="Search SKU or product" value="${search.replaceAll('"', "&quot;")}"><button id="search-btn" class="btn secondary">Search</button></div>${table([
      { key: "sku", label: "SKU" }, { key: "product_name", label: "Product" },
      { key: "unit_cost", label: "Cost" }, { key: "unit_price", label: "Price" },
      { key: "reorder_level", label: "Reorder at" }, { key: "barcode", label: "Barcode" }
    ], rows, row => `${["admin", "manager"].includes(user.role) ? `<button class="btn secondary small" data-edit="${row.product_id}">Edit</button> ` : ""}${user.role === "admin" ? `<button class="btn danger small" data-delete="${row.product_id}">Delete</button>` : ""}`)}`;
    target.querySelector("#search-btn").onclick = () => { search = target.querySelector("#search").value; render(); };
    target.querySelector("#search").onkeydown = event => { if (event.key === "Enter") { search = event.target.value; render(); } };
    target.querySelector("#add")?.addEventListener("click", () => edit());
    target.querySelectorAll("[data-edit]").forEach(button => button.onclick = () => edit(rows.find(row => String(row.product_id) === button.dataset.edit)));
    target.querySelectorAll("[data-delete]").forEach(button => button.onclick = async () => {
      if (confirmAction("Delete this product? Related sales can prevent deletion.")) {
        await api.delete(`/products/${button.dataset.delete}`); toast("Product deleted"); await render();
      }
    });
  }
  async function edit(product = {}) {
    const [categories, suppliers] = await Promise.all([api.get("/categories"), api.get("/suppliers")]);
    const formFields = fields.map(field => field.related === "categories"
      ? { ...field, options: categories.map(row => ({ value: row.category_id, label: row.category_name })) }
      : field.related === "suppliers" ? { ...field, options: suppliers.map(row => ({ value: row.supplier_id, label: row.supplier_name })) }
        : field.name === "is_active" ? { ...field, value: product.is_active === false ? 0 : 1 } : field);
    const data = await modal(product.product_id ? "Edit product" : "Add product", formFields, product);
    if (!data) return;
    data.is_active = Boolean(data.is_active);
    if (product.product_id) await api.put(`/products/${product.product_id}`, data);
    else await api.post("/products", data);
    toast("Product saved");
    await render();
  }
  await render();
}
