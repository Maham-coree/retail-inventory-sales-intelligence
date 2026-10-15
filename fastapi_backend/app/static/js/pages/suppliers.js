import { directoryPage } from "./common.js";
export default (target, api, user) => directoryPage(target, api, user, {
  path: "suppliers", id: "supplier_id", title: "Suppliers", singular: "supplier",
  columns: [["supplier_id", "ID"], ["supplier_name", "Supplier"], ["contact_person", "Contact"], ["email", "Email"], ["phone", "Phone"], ["city", "City"], ["lead_time_days", "Lead time"]],
  fields: [{ name: "supplier_name", label: "Supplier name" }, { name: "contact_person", label: "Contact person", required: false }, { name: "email", label: "Email", required: false }, { name: "phone", label: "Phone", required: false }, { name: "city", label: "City", required: false }, { name: "lead_time_days", label: "Lead time (days)", type: "number", min: "0" }]
});
