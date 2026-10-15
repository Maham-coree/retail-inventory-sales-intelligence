import { modal, pageHeading, table, toast } from "../ui.js";

export default async function usersPage(target, api) {
  async function render() {
    const users = await api.get("/users");
    target.innerHTML = `${pageHeading("Application users", '<button id="create" class="btn">Create user</button>')}${table([{ key: "username", label: "Username" }, { key: "role", label: "Role" }, { key: "employee_id", label: "Employee" }, { key: "is_active", label: "Active" }, { key: "created_at", label: "Created" }], users, user => `<button class="btn secondary small" data-reset="${user.user_id}">Reset password</button> ${user.is_active ? `<button class="btn danger small" data-disable="${user.user_id}">Deactivate</button>` : ""}`)}`;
    target.querySelector("#create").onclick = async () => {
      const data = await modal("Create user", [
        { name: "username", label: "Username" }, { name: "password", label: "Initial password", type: "password" },
        { name: "role", label: "Role", options: ["admin", "manager", "cashier"].map(value => ({ value, label: value })) },
        { name: "employee_id", label: "Employee ID (optional)", type: "number", required: false }
      ]);
      if (!data) return;
      if (!data.employee_id) data.employee_id = null;
      await api.post("/users", data); toast("User created"); await render();
    };
    target.querySelectorAll("[data-disable]").forEach(button => button.onclick = async () => {
      if (window.confirm("Deactivate this user?")) { await api.post(`/users/${button.dataset.disable}/deactivate`); toast("User deactivated"); await render(); }
    });
    target.querySelectorAll("[data-reset]").forEach(button => button.onclick = async () => {
      const data = await modal("Reset password", [{ name: "password", label: "New password", type: "password" }]);
      if (data) { await api.post(`/users/${button.dataset.reset}/reset-password`, data); toast("Password reset"); }
    });
  }
  await render();
}
