import { codeBlock, pageHeading, toast } from "../ui.js";

const scenarios = [
  ["COMMIT", "/labs/transactions/commit"], ["ROLLBACK", "/labs/transactions/rollback"],
  ["SAVEPOINT", "/labs/transactions/savepoint"], ["Isolation levels", "/labs/transactions/isolation"],
  ["Locks / NOWAIT", "/labs/transactions/locks"], ["Deadlock", "/labs/transactions/deadlock"],
  ["Unique violation 23505", "/labs/transactions/unique-violation"]
];

export default async function transactionsLabPage(target, api) {
  target.innerHTML = `${pageHeading("Transactions lab")}<p class="muted">Each scenario uses only the isolated <code>retail.lab_*</code> tables.</p><div class="toolbar">${scenarios.map(([label, path]) => `<button class="btn secondary" data-run="${path}">${label}</button>`).join("")}</div><div id="steps" class="step-log"></div>`;
  target.querySelectorAll("[data-run]").forEach(button => button.onclick = async () => {
    const output = target.querySelector("#steps");
    output.innerHTML = '<div class="panel skeleton">Running database scenario…</div>';
    try {
      const steps = await api.post(button.dataset.run);
      output.innerHTML = steps.map(step => `<article class="step"><h3>${step.step}</h3><p class="muted">SQL</p>${codeBlock(step.sql)}<p class="muted">Result</p>${codeBlock(JSON.stringify(step.result, null, 2))}</article>`).join("");
      toast(`${button.textContent} scenario completed`);
    } catch (error) {
      output.textContent = error.message;
    }
  });
}
