import { directoryPage } from "./common.js";
export default (target, api, user) => directoryPage(target, api, user, {
  path: "categories", id: "category_id", title: "Categories", singular: "category",
  columns: [["category_id", "ID"], ["category_name", "Category"], ["description", "Description"]],
  fields: [{ name: "category_name", label: "Category name" }, { name: "description", label: "Description", required: false }]
});
