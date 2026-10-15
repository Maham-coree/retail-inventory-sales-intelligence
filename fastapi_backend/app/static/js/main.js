import { api, authStore } from "./api.js";
import { escapeHtml, toast, skeleton } from "./ui.js";
import loginPage from "./pages/login.js";
import dashboardPage from "./pages/dashboard.js";
import productsPage from "./pages/products.js";
import categoriesPage from "./pages/categories.js";
import suppliersPage from "./pages/suppliers.js";
import storesPage from "./pages/stores.js";
import customersPage from "./pages/customers.js";
import employeesPage from "./pages/employees.js";
import inventoryPage from "./pages/inventory.js";
import salesPage from "./pages/sales.js";
import purchaseOrdersPage from "./pages/purchase-orders.js";
import reorderPage from "./pages/reorder-alerts.js";
import ledgerPage from "./pages/stock-ledger.js";
import reportsPage from "./pages/reports.js";
import transactionsLabPage from "./pages/transactions-lab.js";
import optimizationLabPage from "./pages/optimization-lab.js";
import designPage from "./pages/database-design.js";
import usersPage from "./pages/users.js";

const sections = [
  ["OVERVIEW", [["dashboard", "Dashboard", "admin manager cashier"]]],
  ["MANAGEMENT", [["products", "Products", "admin manager cashier"], ["categories", "Categories", "admin manager cashier"], ["suppliers", "Suppliers", "admin manager cashier"], ["stores", "Stores", "admin manager cashier"], ["customers", "Customers", "admin manager cashier"], ["employees", "Employees", "admin manager"]]],
  ["SALES", [["inventory", "Inventory", "admin manager cashier"], ["sales", "Sales & POS", "admin manager cashier"], ["purchase-orders", "Purchase Orders", "admin manager"], ["reorder-alerts", "Reorder Alerts", "admin manager cashier"], ["stock-ledger", "Stock Ledger", "admin manager"]]],
  ["ANALYTICS", [["reports", "Reports & SQL", "admin manager"]]],
  ["ADMIN", [["users", "Users", "admin"], ["database-design", "Database Design", "admin manager cashier"]]],
  ["DEVELOPER", [["transactions-lab", "Transactions Lab", "admin"], ["optimization-lab", "Optimization Lab", "admin"]]]
];
const pages = {
  login: loginPage, dashboard: dashboardPage, products: productsPage,
  categories: categoriesPage, suppliers: suppliersPage, stores: storesPage,
  customers: customersPage, employees: employeesPage, inventory: inventoryPage,
  sales: salesPage, "purchase-orders": purchaseOrdersPage,
  "reorder-alerts": reorderPage, "stock-ledger": ledgerPage,
  reports: reportsPage, "transactions-lab": transactionsLabPage,
  "optimization-lab": optimizationLabPage, "database-design": designPage,
  users: usersPage
};
const titles = Object.fromEntries(sections.flatMap(([, links]) => links.map(([id, label]) => [id, label])));

function renderShell() {
  const user = authStore.user;
  if (!user) {
    document.querySelector("#app").innerHTML = '<main id="login-view"></main>';
    return;
  }
  const nav = sections.map(([heading, links]) => {
    const visible = links.filter(([, , roles]) => roles.split(" ").includes(user.role));
    return visible.length ? `<div class="nav-group">${heading}</div>${visible.map(([id, label]) => `<a class="nav-link" href="#${id}" data-route="${id}"><svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h6v6H4zM14 5h6v6h-6zM4 15h6v5H4zM14 15h6v5h-6z"/></svg>${escapeHtml(label)}</a>`).join("")}` : "";
  }).join("");
  document.querySelector("#app").innerHTML = `<div class="app-shell"><aside class="sidebar" id="sidebar"><div class="brand">Retail Inventory<br>&amp; Sales Intelligence</div>${nav}<div class="nav-group">DEVELOPER</div><a class="nav-link" href="/docs" target="_blank" rel="noopener">API Documentation</a></aside><div class="main-area"><header class="topbar"><div style="display:flex;align-items:center;gap:12px"><button id="mobile-menu" class="btn secondary mobile-menu" aria-label="Toggle navigation">Menu</button><h1 id="page-title">Dashboard</h1></div><div class="user-tools"><span class="user-name">${escapeHtml(user.username)}</span><span class="role-badge">${escapeHtml(user.role)}</span><button id="logout" class="btn secondary small">Logout</button></div></header><main class="content" id="page-content">${skeleton()}</main></div></div>`;
  document.querySelector("#logout").onclick = () => { authStore.clear(); location.hash = "#login"; renderRoute(); };
  document.querySelector("#mobile-menu").onclick = () => document.querySelector("#sidebar").classList.toggle("open");
}

async function renderRoute() {
  const route = location.hash.slice(1) || (authStore.token ? "dashboard" : "login");
  if (route === "login" || !authStore.token) {
    if (authStore.token && route === "login") { location.hash = "#dashboard"; return; }
    renderShell();
    await loginPage(document.querySelector("#login-view"), api);
    return;
  }
  const user = authStore.user;
  const allowed = sections.some(([, links]) => links.some(([id, , roles]) => id === route && roles.split(" ").includes(user?.role)));
  if (!allowed || !pages[route]) { location.hash = "#dashboard"; return; }
  renderShell();
  document.querySelector("#page-title").textContent = titles[route] || "Database Design";
  document.querySelectorAll("[data-route]").forEach(link => link.classList.toggle("active", link.dataset.route === route));
  const target = document.querySelector("#page-content");
  target.innerHTML = skeleton();
  try { await pages[route](target, api, user); }
  catch (error) {
    target.innerHTML = `<section class="panel error" role="alert">${escapeHtml(error.message || "Unable to load this page.")}</section>`;
  }
}

window.addEventListener("hashchange", renderRoute);
renderRoute().catch(error => toast(error.message, true));
