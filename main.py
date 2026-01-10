import time
from uuid import uuid4
from threading import Lock

import webview

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.config import Config

# پنجره Kivy را مخفی/خیلی کوچک می‌کنیم چون UI اصلی داخل WebView است
Config.set("graphics", "width", "1")
Config.set("graphics", "height", "1")
Config.set("graphics", "borderless", "1")
Config.set("graphics", "resizable", "0")
Config.set("kivy", "exit_on_escape", "1")


CSS = r"""
:root{
  --bg: #0f172a;
  --panel: #111c36;
  --text: #e5e7eb;
  --muted: #9ca3af;
  --me: #1d4ed8;
  --bot: #1f2937;
  --border: rgba(255,255,255,.10);
}
*{ box-sizing:border-box; }
html, body{
  height:100%;
  margin:0;
  font-family: system-ui, "Segoe UI", Tahoma, sans-serif;
  background: var(--bg);
  color: var(--text);
}
.topbar{
  height:56px;
  padding:0 12px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  border-bottom:1px solid var(--border);
  background: rgba(255,255,255,.02);
}
.title{ font-weight:700; }
.chat{
  height: calc(100% - 56px - 68px);
  overflow-y:auto;
  padding:14px 12px;
  display:flex;
  flex-direction:column;
  gap:10px;
}
.row{ display:flex; }
.row.me{ justify-content:flex-start; }
.row.bot{ justify-content:flex-end; }
.bubble{
  max-width:82%;
  padding:10px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  line-height:1.6;
  white-space:pre-wrap;
  word-break:break-word;
}
.bubble.me{ background: rgba(29,78,216,.55); }
.bubble.bot{ background: var(--bot); }
.meta{
  margin-top:6px;
  font-size:12px;
  color: var(--muted);
}
.composer{
  height:68px;
  padding:10px 12px;
  display:grid;
  grid-template-columns: 1fr auto;
  gap:10px;
  border-top:1px solid var(--border);
  background: rgba(255,255,255,.02);
}
.input{
  border:1px solid var(--border);
  border-radius:12px;
  padding:12px;
  background: var(--panel);
  color: var(--text);
  outline:none;
}
.btn{
  border:1px solid var(--border);
  border-radius:12px;
  padding:10px 14px;
  background:#16a34a;
  color:white;
  cursor:pointer;
  font-weight:700;
}
.btn.secondary{
  background:transparent;
  color:var(--text);
}
"""

JS = r"""
const chat = document.getElementById("chat");
const txtMessage = document.getElementById("txtMessage");
const btnSend = document.getElementById("btnSend");
const btnClear = document.getElementById("btnClear");

function formatTime(ts) {
  try {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
  } catch (_) {
    return "";
  }
}

function appendMessage(m) {
  const row = document.createElement("div");
  row.className = `row ${m.from === "me" ? "me" : "bot"}`;

  const bubble = document.createElement("div");
  bubble.className = `bubble ${m.from === "me" ? "me" : "bot"}`;

  const text = document.createElement("div");
  text.textContent = m.text;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = formatTime(m.ts);

  bubble.appendChild(text);
  bubble.appendChild(meta);
  row.appendChild(bubble);
  chat.appendChild(row);

  chat.scrollTop = chat.scrollHeight;
}

async function loadHistory() {
  const res = await window.pywebview.api.get_history();
  if (res && res.ok) {
    chat.innerHTML = "";
    res.messages.forEach(appendMessage);
  }
}

async function send() {
  const text = (txtMessage.value || "").trim();
  if (!text) return;

  txtMessage.value = "";
  txtMessage.focus();

  const res = await window.pywebview.api.send_message(text);
  if (res && res.ok) {
    res.messages.forEach(appendMessage);
  }
}

btnSend.addEventListener("click", send);
txtMessage.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});

btnClear.addEventListener("click", async () => {
  await window.pywebview.api.clear();
  await loadHistory();
});

document.addEventListener("pywebviewready", async () => {
  await loadHistory();
  txtMessage.focus();
});
"""

HTML = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Messenger</title>
  <style>{CSS}</style>
</head>

<body>
  <header class="topbar">
    <div class="title">پیام‌رسان نمونه</div>
    <button id="btnClear" class="btn secondary">پاک کردن</button>
  </header>

  <main id="chat" class="chat"></main>

  <footer class="composer">
    <input id="txtMessage" class="input" type="text" placeholder="پیام..." autocomplete="off" />
    <button id="btnSend" class="btn">ارسال</button>
  </footer>

  <script>{JS}</script>
</body>
</html>
"""


class MessengerAPI:
    def __init__(self):
        self._lock = Lock()
        self._messages = []

    def get_history(self):
        with self._lock:
            return {"ok": True, "messages": list(self._messages)}

    def clear(self):
        with self._lock:
            self._messages.clear()
        return {"ok": True}

    def send_message(self, text: str):
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "پیام خالی است."}

        now = time.time()
        msg_me = {"id": str(uuid4()), "from": "me", "text": text, "ts": now}
        msg_bot = {"id": str(uuid4()), "from": "bot", "text": f"دریافت شد: {text}", "ts": now + 0.001}

        with self._lock:
            self._messages.append(msg_me)
            self._messages.append(msg_bot)

        return {"ok": True, "messages": [msg_me, msg_bot]}


class KivyWebviewMessenger(App):
    def build(self):
        return Widget()

    def on_start(self):
        api = MessengerAPI()
        webview.create_window(
            title="Messenger",
            html=HTML,     # HTML/CSS/JS همه داخل همین فایل است
            js_api=api,
            width=420,
            height=720,
            resizable=True,
        )
        webview.start(debug=False)
        self.stop()


if __name__ == "__main__":
    KivyWebviewMessenger().run()
