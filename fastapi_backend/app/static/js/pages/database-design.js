import { codeBlock, pageHeading } from "../ui.js";

export default async function databaseDesignPage(target, api) {
  const markdown = await api.get("/database-design");
  target.innerHTML = `${pageHeading("Database design · read only")}<section class="panel">${codeBlock(markdown)}</section>`;
}
