import { authStore } from "../api.js";
import { escapeHtml } from "../ui.js";

export default async function loginPage(target, api) {
  target.innerHTML = `<div class="login-wrap"><form class="login-card"><h1>Retail IMS</h1><p>Inventory and sales intelligence platform</p><label class="field">Username<input name="username" autocomplete="username" required></label><label class="field">Password<input name="password" type="password" autocomplete="current-password" required></label><button class="btn" type="submit">Sign in</button><div class="form-error" role="alert"></div><p><strong>Demo accounts:</strong><br>admin / Admin@123<br>manager / Manager@123<br>cashier / Cashier@123</p></form></div>`;
  const form = target.querySelector("form");
  form.onsubmit = async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const error = form.querySelector(".form-error");
    error.textContent = "";
    try {
      const result = await api.form("/auth/login", data);
      authStore.save(result.access_token, result.user);
      location.hash = "#dashboard";
      location.reload();
    } catch (cause) {
      error.textContent = escapeHtml(cause.message || "Sign-in failed.");
    }
  };
}
