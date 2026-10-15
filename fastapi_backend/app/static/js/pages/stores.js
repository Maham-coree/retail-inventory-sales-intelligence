import { directoryPage } from "./common.js";
export default (target, api, user) => directoryPage(target, api, user, {
  path: "stores", id: "store_id", title: "Stores", singular: "store",
  columns: [["store_id", "ID"], ["store_name", "Store"], ["city", "City"], ["address", "Address"], ["phone", "Phone"]],
  fields: [{ name: "store_name", label: "Store name" }, { name: "city", label: "City" }, { name: "address", label: "Address", required: false }, { name: "phone", label: "Phone", required: false }]
});
