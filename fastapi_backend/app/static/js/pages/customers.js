import { directoryPage } from "./common.js";
export default (target, api, user) => directoryPage(target, api, user, {
  path: "customers", id: "customer_id", title: "Customers", singular: "customer",
  columns: [["customer_id", "ID"], ["full_name", "Customer"], ["email", "Email"], ["phone", "Phone"], ["city", "City"]],
  fields: [{ name: "full_name", label: "Full name" }, { name: "email", label: "Email", required: false }, { name: "phone", label: "Phone", required: false }, { name: "city", label: "City", required: false }]
});
