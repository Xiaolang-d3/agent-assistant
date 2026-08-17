const logEl = document.querySelector("#log");
const formEl = document.querySelector("#composer");
const inputEl = document.querySelector("#input");
const sendEl = document.querySelector("#send");
const statusEl = document.querySelector("#status");

const history = [];
let busy = false;

function addBubble(role, text, traces) {
  const article = document.createElement("article");
  article.className = `bubble ${role}`;
  const who = document.createElement("span");
  who.className = "who";
  who.textContent = role === "user" ? "You" : "Assistant";
  const body = document.createElement("p");
  body.textContent = text;
  article.append(who, body);
  if (traces?.length) {
    article.append(renderTraces(traces));
  }
  logEl.append(article);
  logEl.scrollTop = logEl.scrollHeight;
}

function renderTraces(steps) {
  const box = document.createElement("div");
  box.className = "traces";
  for (const step of steps) {
    if (step.type !== "search") continue;
    const line = document.createElement("div");
    line.textContent = `搜索：${step.query}`;
    box.append(line);
    for (const item of (step.results || []).slice(0, 3)) {
      const link = document.createElement("a");
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = item.title || item.url;
      const wrap = document.createElement("div");
      wrap.append(link);
      box.append(wrap);
    }
  }
  return box;
}

function setBusy(next) {
  busy = next;
  sendEl.disabled = next;
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (!data.llm) {
      statusEl.className = "status warn";
      statusEl.textContent = "未配置 OPENAI_API_KEY，先复制 .env.example 为 .env";
      return;
    }
    statusEl.className = "status ok";
    statusEl.textContent = `${data.model} · 搜索 ${data.search}`;
  } catch {
    statusEl.className = "status warn";
    statusEl.textContent = "服务未就绪";
  }
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message || busy) return;
  inputEl.value = "";
  addBubble("user", message);
  setBusy(true);
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "请求失败");
    history.push({ role: "user", content: message });
    history.push({ role: "assistant", content: data.reply });
    addBubble("assistant", data.reply, data.steps);
  } catch (err) {
    addBubble("assistant", err.message || "发送失败");
  } finally {
    setBusy(false);
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(inputEl.value);
});

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(inputEl.value);
  }
});

refreshStatus();
inputEl.focus();
