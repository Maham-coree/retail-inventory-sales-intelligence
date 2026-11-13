import { authStore } from "./api.js";

let mounted = null;

const timeLabel = value => {
  const date = value ? new Date(value) : new Date();
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

function appendText(parent, tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = String(value ?? "");
  parent.append(element);
  return element;
}

function renderData(container, data) {
  if (!data || !Array.isArray(data.rows) || !data.rows.length) return;
  const wrapper = document.createElement("div");
  wrapper.className = "assistant-result";
  if (data.type === "table") {
    const table = document.createElement("table");
    const columns = Array.isArray(data.columns) && data.columns.length
      ? data.columns
      : Object.keys(data.rows[0]);
    const head = document.createElement("thead");
    const headingRow = document.createElement("tr");
    for (const column of columns) {
      appendText(headingRow, "th", "", String(column).replaceAll("_", " "));
    }
    head.append(headingRow);
    table.append(head);
    const body = document.createElement("tbody");
    for (const row of data.rows.slice(0, 10)) {
      const tableRow = document.createElement("tr");
      for (const column of columns) {
        appendText(tableRow, "td", "", row[column]);
      }
      body.append(tableRow);
    }
    table.append(body);
    wrapper.append(table);
  } else {
    for (const row of data.rows.slice(0, 10)) {
      const item = document.createElement("p");
      item.className = "assistant-result-item";
      item.textContent = typeof row === "string"
        ? row
        : Object.entries(row).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value ?? ""}`).join(" · ");
      wrapper.append(item);
    }
  }
  container.append(wrapper);
}

export function mountChatbot(api, user) {
  if (!user || !authStore.token) {
    unmountChatbot();
    return;
  }
  if (mounted?.userId === user.user_id) {
    mounted.bindToggle();
    return;
  }
  unmountChatbot();

  const root = document.createElement("div");
  root.className = "assistant-root";
  root.innerHTML = `
    <button class="assistant-fab" type="button" aria-label="Open Retail Assistant" title="Open Retail Assistant">✦</button>
    <section class="assistant-panel" role="dialog" aria-modal="false" aria-labelledby="assistant-title" hidden>
      <header class="assistant-header">
        <div><h2 id="assistant-title">Retail Assistant</h2><span class="assistant-status"><i aria-hidden="true"></i> Ready to help</span></div>
        <div class="assistant-header-actions">
          <button type="button" class="assistant-new" aria-label="Start a new chat">New chat</button>
          <button type="button" class="assistant-close" aria-label="Close Retail Assistant">×</button>
        </div>
      </header>
      <div class="assistant-conversation" aria-live="polite" aria-relevant="additions text"></div>
      <div class="assistant-error" role="alert" hidden></div>
      <div class="assistant-suggestion-list" aria-label="Suggested questions"></div>
      <form class="assistant-composer">
        <label class="assistant-input-label" for="assistant-input">Ask a question</label>
        <textarea id="assistant-input" rows="2" maxlength="500" placeholder="Ask about stock, sales or how to use the system"></textarea>
        <div class="assistant-compose-footer">
          <span class="assistant-counter">0/500</span>
          <span class="assistant-input-hint">Enter to send · Shift+Enter for a new line</span>
          <button class="btn assistant-send" type="submit">Send</button>
        </div>
      </form>
    </section>`;
  document.body.append(root);

  const panel = root.querySelector(".assistant-panel");
  const fab = root.querySelector(".assistant-fab");
  const conversation = root.querySelector(".assistant-conversation");
  const errorBox = root.querySelector(".assistant-error");
  const suggestionList = root.querySelector(".assistant-suggestion-list");
  const form = root.querySelector(".assistant-composer");
  const input = root.querySelector("#assistant-input");
  const counter = root.querySelector(".assistant-counter");
  const sendButton = root.querySelector(".assistant-send");
  const mediaQuery = window.matchMedia("(max-width: 1099px)");
  const syncModalSemantics = () => panel.setAttribute("aria-modal", String(mediaQuery.matches));
  syncModalSemantics();
  mediaQuery.addEventListener("change", syncModalSemantics);
  const userId = String(user.user_id);
  const contextKey = `retail-assistant-context-${userId}`;
  let context = {};
  let historyLoaded = false;
  let pending = false;

  try {
    context = JSON.parse(localStorage.getItem(contextKey) || "{}");
  } catch {
    context = {};
  }

  const scrollToLatest = () => { conversation.scrollTop = conversation.scrollHeight; };
  const showError = message => {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  };
  const normalizedError = error => {
    const message = error?.message || "";
    if (/failed to fetch|network|load failed/i.test(message)) {
      return "Could not reach the assistant. Check your connection and try again.";
    }
    if (/session|token|sign in|unauthorized/i.test(message)) {
      return "Your session may have expired. Sign in again to continue.";
    }
    return message || "The assistant could not complete that request. Please try again.";
  };
  const addMessage = ({ role, text, data, suggestions, messageId, helpful, createdAt }) => {
    const message = document.createElement("article");
    message.className = `assistant-message assistant-message-${role}`;
    const bubble = document.createElement("div");
    bubble.className = "assistant-bubble";
    appendText(bubble, "p", "", text);
    if (role === "assistant") renderData(bubble, data);
    message.append(bubble);
    appendText(message, "time", "assistant-time", timeLabel(createdAt));
    if (role === "assistant" && Number.isInteger(messageId)) {
      const feedback = document.createElement("div");
      feedback.className = "assistant-feedback";
      appendText(feedback, "span", "", "Helpful?");
      for (const [value, label, icon] of [[true, "Yes, helpful", "👍"], [false, "No, not helpful", "👎"]]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = icon;
        button.setAttribute("aria-label", label);
        button.title = label;
        button.disabled = helpful !== null && helpful !== undefined;
        if (helpful === value) button.classList.add("selected");
        button.onclick = async () => {
          button.disabled = true;
          showError("");
          try {
            await api.post("/chatbot/feedback", { message_id: messageId, helpful: value });
            feedback.querySelectorAll("button").forEach(item => { item.disabled = true; });
            button.classList.add("selected");
          } catch (error) {
            button.disabled = false;
            showError(normalizedError(error));
          }
        };
        feedback.append(button);
      }
      message.append(feedback);
    }
    conversation.append(message);
    scrollToLatest();
    if (suggestions?.length) renderSuggestions(suggestions);
  };
  function renderSuggestions(items) {
    suggestionList.replaceChildren();
    for (const suggestion of items.slice(0, 5)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "assistant-chip";
      button.textContent = suggestion;
      button.onclick = () => sendMessage(suggestion);
      suggestionList.append(button);
    }
  }
  const showTyping = () => {
    const typing = document.createElement("div");
    typing.className = "assistant-typing";
    typing.setAttribute("role", "status");
    typing.textContent = "Retail Assistant is thinking…";
    conversation.append(typing);
    scrollToLatest();
    return typing;
  };
  const loadHistoryAndSuggestions = async () => {
    showError("");
    try {
      const [history, suggestionResponse] = await Promise.all([
        api.get("/chatbot/history?limit=20"),
        api.get("/chatbot/suggestions")
      ]);
      if (!historyLoaded) {
        for (const item of history.messages || []) {
          addMessage({ role: "user", text: item.user_message, createdAt: item.created_at });
          addMessage({
            role: "assistant",
            text: item.bot_reply,
            messageId: item.message_id,
            helpful: item.was_helpful,
            createdAt: item.created_at
          });
        }
        historyLoaded = true;
      }
      renderSuggestions(suggestionResponse.suggestions || []);
    } catch (error) {
      showError(normalizedError(error));
      renderSuggestions(["How do I check stock?", "How do I record a sale?", "What can my role do?"]);
    }
  };
  const open = async focus => {
    panel.hidden = false;
    fab.hidden = true;
    document.querySelector(".app-shell")?.classList.add("assistant-open");
    const toggle = document.querySelector("#assistant-toggle");
    toggle?.setAttribute("aria-expanded", "true");
    localStorage.setItem("retail-assistant-open", "true");
    if (!conversation.childElementCount) {
      appendText(
        conversation,
        "p",
        "assistant-welcome",
        "Hello! Ask me about stock, products, authorized sales information, or how to use the system."
      );
    }
    await loadHistoryAndSuggestions();
    if (focus) input.focus();
  };
  const close = () => {
    panel.hidden = true;
    fab.hidden = false;
    document.querySelector(".app-shell")?.classList.remove("assistant-open");
    document.querySelector("#assistant-toggle")?.setAttribute("aria-expanded", "false");
    localStorage.setItem("retail-assistant-open", "false");
    document.querySelector("#assistant-toggle")?.focus();
  };
  const sendMessage = async suppliedMessage => {
    const message = String(suppliedMessage ?? input.value).trim();
    if (!message || pending) return;
    showError("");
    addMessage({ role: "user", text: message });
    input.value = "";
    counter.textContent = "0/500";
    pending = true;
    sendButton.disabled = true;
    const typing = showTyping();
    try {
      const response = await api.post("/chatbot/message", { message, context });
      typing.remove();
      context = response.context || {};
      localStorage.setItem(contextKey, JSON.stringify(context));
      addMessage({
        role: "assistant",
        text: response.reply,
        data: response.data,
        suggestions: response.suggestions,
        messageId: response.message_id,
        helpful: null
      });
    } catch (error) {
      typing.remove();
      showError(normalizedError(error));
    } finally {
      pending = false;
      sendButton.disabled = false;
      input.focus();
    }
  };

  input.addEventListener("input", () => { counter.textContent = `${input.value.length}/500`; });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  form.addEventListener("submit", event => {
    event.preventDefault();
    void sendMessage();
  });
  root.querySelector(".assistant-close").onclick = close;
  root.querySelector(".assistant-new").onclick = () => {
    conversation.replaceChildren();
    suggestionList.replaceChildren();
    context = {};
    localStorage.removeItem(contextKey);
    showError("");
    appendText(
      conversation,
      "p",
      "assistant-welcome",
      "New chat started. Ask about stock, products, sales, or how to use the system."
    );
    void loadHistoryAndSuggestions();
  };
  fab.onclick = () => { void open(true); };
  const onDocumentKeydown = event => {
    if (event.key === "Escape" && !panel.hidden) {
      close();
    }
  };
  document.addEventListener("keydown", onDocumentKeydown);

  const bindToggle = () => {
    const toggle = document.querySelector("#assistant-toggle");
    if (toggle) {
      toggle.onclick = () => panel.hidden ? void open(true) : close();
      toggle.setAttribute("aria-expanded", String(!panel.hidden));
    }
    document.querySelector(".app-shell")?.classList.toggle("assistant-open", !panel.hidden);
  };
  mounted = {
    userId: user.user_id,
    bindToggle,
    cleanup: () => {
      document.removeEventListener("keydown", onDocumentKeydown);
      mediaQuery.removeEventListener("change", syncModalSemantics);
    }
  };
  bindToggle();
  if (localStorage.getItem("retail-assistant-open") === "true") void open(false);
}

export function unmountChatbot() {
  mounted?.cleanup();
  document.querySelector(".assistant-root")?.remove();
  document.querySelector(".app-shell")?.classList.remove("assistant-open");
  mounted = null;
}
