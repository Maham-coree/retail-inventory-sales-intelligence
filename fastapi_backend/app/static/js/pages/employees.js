import { directoryPage } from "./common.js";
export default (target, api, user) => directoryPage(target, api, user, {
  path: "employees", id: "employee_id", title: "Employees", singular: "employee",
  columns: [["employee_id", "ID"], ["full_name", "Employee"], ["role", "Role"], ["email", "Email"], ["store_id", "Store"]],
  related: [{ name: "stores", path: "/stores" }],
  fields: [{ name: "full_name", label: "Full name" }, { name: "role", label: "Role", options: [{ value: "Manager", label: "Manager" }, { value: "Cashier", label: "Cashier" }, { value: "Stock Clerk", label: "Stock Clerk" }] }, { name: "store_id", label: "Store", type: "number", related: "stores", valueKey: "store_id", labelKey: "store_name" }, { name: "email", label: "Email", required: false }]
});
