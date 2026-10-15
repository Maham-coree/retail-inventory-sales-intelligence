import { escapeHtml, modal, pageHeading, table, toast } from "../ui.js";

export default async function salesPage(target, api, user) {
  async function renderList() {
    const rows = await api.get("/sales");
    target.innerHTML = `${pageHeading("Sales", '<button id="new-sale" class="btn">New sale</button>')}${table([
      { key: "invoice", label: "Invoice" }, { key: "store", label: "Store" },
      { key: "customer", label: "Customer" }, { key: "cashier", label: "Cashier" },
      { key: "date", label: "Date" }, { key: "payment", label: "Payment" }, { key: "total", label: "Total" }
    ], rows, row => `<button class="btn secondary small" data-receipt="${row.invoice}">Receipt</button>`)}`;
    target.querySelector("#new-sale").onclick = newSale;
    target.querySelectorAll("[data-receipt]").forEach(button => button.onclick = () => receipt(Number(button.dataset.receipt)));
  }
  async function newSale() {
    const [stores, customers, products] = await Promise.all([api.get("/stores"), api.get("/customers"), api.get("/products")]);
    const storeOptions = stores.map(row => `<option value="${row.store_id}">${escapeHtml(row.store_name)}</option>`).join("");
    const customerOptions = customers.map(row => `<option value="${row.customer_id}">${escapeHtml(row.full_name)}</option>`).join("");
    target.innerHTML = `${pageHeading("New point-of-sale transaction", '<button id="back" class="btn secondary">Back to sales</button>')}<section class="panel"><div class="toolbar"><label>Store <select id="pos-store">${storeOptions}</select></label><label>Customer <select id="pos-customer"><option value="">Walk-in customer</option>${customerOptions}</select></label><label>Payment <select id="pos-payment"><option>Cash</option><option>Card</option><option>Online</option></select></label></div><div class="toolbar"><input id="product-search" type="search" placeholder="Find a product by SKU or name"><select id="pos-product">${products.map(row => `<option value="${row.product_id}">${escapeHtml(row.sku)} — ${escapeHtml(row.product_name)} (${escapeHtml(row.unit_price)})</option>`).join("")}</select><input id="pos-quantity" type="number" min="1" value="1" aria-label="Quantity"><button id="add-line" class="btn secondary">Add item</button></div><div id="cart"></div><div class="toolbar"><strong id="total">Total: 0.00</strong><button id="submit-sale" class="btn">Complete sale</button></div><div id="pos-error" class="error" role="alert"></div></section>`;
    target.querySelector("#back").onclick = renderList;
    const search = target.querySelector("#product-search");
    search.oninput = () => {
      const query = search.value.toLowerCase();
      [...target.querySelector("#pos-product").options].forEach((option, index) => {
        option.hidden = query && !option.text.toLowerCase().includes(query);
        if (!option.hidden && query) target.querySelector("#pos-product").selectedIndex = index;
      });
    };
    const cart = [];
    const redraw = () => {
      target.querySelector("#cart").innerHTML = cart.length ? `<div class="table-wrap"><table><thead><tr><th>Product</th><th>Quantity</th><th>Unit price</th><th>Discount</th><th>Line total</th><th></th></tr></thead><tbody>${cart.map((line, index) => `<tr><td>${escapeHtml(line.product.product_name)}</td><td>${line.quantity}</td><td>${line.product.unit_price}</td><td><input data-discount="${index}" type="number" min="0" step="0.01" value="${line.discount}" aria-label="Discount"></td><td>${(line.quantity * Number(line.product.unit_price) - Number(line.discount)).toFixed(2)}</td><td><button class="btn danger small" data-remove="${index}">Remove</button></td></tr>`).join("")}</tbody></table></div>` : '<div class="empty">Add at least one product to the sale.</div>';
      const total = cart.reduce((sum, line) => sum + line.quantity * Number(line.product.unit_price) - Number(line.discount), 0);
      target.querySelector("#total").textContent = `Total: ${total.toFixed(2)}`;
      target.querySelectorAll("[data-discount]").forEach(input => input.oninput = () => { cart[Number(input.dataset.discount)].discount = Number(input.value); redraw(); });
      target.querySelectorAll("[data-remove]").forEach(button => button.onclick = () => { cart.splice(Number(button.dataset.remove), 1); redraw(); });
    };
    target.querySelector("#add-line").onclick = () => {
      const product = products.find(row => row.product_id === Number(target.querySelector("#pos-product").value));
      if (!product) return;
      const quantity = Math.max(1, Number(target.querySelector("#pos-quantity").value));
      const current = cart.find(line => line.product.product_id === product.product_id);
      if (current) current.quantity += quantity;
      else cart.push({ product, quantity, discount: 0 });
      redraw();
    };
    target.querySelector("#submit-sale").onclick = async () => {
      const error = target.querySelector("#pos-error");
      error.textContent = "";
      if (!cart.length) { error.textContent = "Add at least one product."; return; }
      try {
        const result = await api.post("/sales", {
          store_id: Number(target.querySelector("#pos-store").value),
          customer_id: target.querySelector("#pos-customer").value || null,
          payment_method: target.querySelector("#pos-payment").value,
          items: cart.map(line => ({ product_id: line.product.product_id, quantity: line.quantity, discount: line.discount }))
        });
        toast("Sale completed");
        await receipt(result.sale.sale_id);
      } catch (cause) {
        error.textContent = cause.message.includes("stock") ? "Insufficient stock. Review quantities and try again." : cause.message;
      }
    };
    redraw();
  }
  async function receipt(id) {
    const result = await api.get(`/sales/${id}`);
    const sale = result.sale;
    target.innerHTML = `<article class="panel receipt"><h2 class="receipt-title">Retail Sales Receipt</h2><p>Invoice #${sale.sale_id} · ${escapeHtml(sale.store_name)}</p><p>${escapeHtml(sale.sale_date)} · ${escapeHtml(sale.payment_method)}</p><p>Customer: ${escapeHtml(sale.customer_name || "Walk-in")} · Served by ${escapeHtml(sale.employee_name)}</p>${table([{ key: "product_name", label: "Product" }, { key: "quantity", label: "Qty" }, { key: "unit_price", label: "Price" }, { key: "discount", label: "Discount" }, { key: "line_total", label: "Line total" }], result.items)}<h3>Total: ${escapeHtml(sale.total_amount)}</h3><div class="toolbar no-print"><button class="btn" onclick="window.print()">Print receipt</button><button id="back-sales" class="btn secondary">Back to sales</button></div></article>`;
    target.querySelector("#back-sales").onclick = renderList;
  }
  void user;
  await renderList();
}
