const logEl = document.querySelector("#log");
const formEl = document.querySelector("#composer");
const inputEl = document.querySelector("#input");
const sendEl = document.querySelector("#send");
const talkEl = document.querySelector("#talk");
const talkLabel = document.querySelector("#talk-label");
const statusEl = document.querySelector("#status");

const history = [];
let busy = false;
let recorder = null;
let chunks = [];

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
  talkEl.disabled = next;
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

async function transcribeBlob(blob) {
  const body = new FormData();
  body.append("audio", blob, "speech.webm");
  const res = await fetch("/api/transcribe", { method: "POST", body });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "转写失败");
  return data.text;
}

async function startTalk() {
  if (busy || recorder) return;
  chunks = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  recorder = new MediaRecorder(stream);
  recorder.ondataavailable = (event) => {
    if (event.data.size) chunks.push(event.data);
  };
  recorder.start();
  talkEl.classList.add("hot");
  talkEl.setAttribute("aria-pressed", "true");
  talkLabel.textContent = "松手结束";
}

async function stopTalk() {
  if (!recorder) return;
  const current = recorder;
  recorder = null;
  const blob = await new Promise((resolve) => {
    current.onstop = () => resolve(new Blob(chunks, { type: current.mimeType || "audio/webm" }));
    current.stop();
    current.stream.getTracks().forEach((track) => track.stop());
  });
  talkEl.classList.remove("hot");
  talkEl.setAttribute("aria-pressed", "false");
  talkLabel.textContent = "按住说话";
  if (blob.size < 800) return;
  setBusy(true);
  talkLabel.textContent = "转写中…";
  try {
    const text = await transcribeBlob(blob);
    inputEl.value = text;
    inputEl.focus();
  } catch (err) {
    addBubble("assistant", err.message || "语音转写失败");
  } finally {
    setBusy(false);
    talkLabel.textContent = "按住说话";
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

talkEl.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  startTalk().catch((err) => addBubble("assistant", err.message || "无法使用麦克风"));
});

window.addEventListener("pointerup", () => {
  stopTalk().catch((err) => addBubble("assistant", err.message || "录音失败"));
});

refreshStatus();
inputEl.focus();
