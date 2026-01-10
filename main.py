# -*- coding: utf-8 -*-
import time
import urllib.parse
from uuid import uuid4
from threading import Lock

from kivy.utils import platform
from kivy.config import Config

# فقط روی دسکتاپ پنجره Kivy را 1x1 می‌کنیم
if platform != "android":
    Config.set("graphics", "width", "1")
    Config.set("graphics", "height", "1")
    Config.set("graphics", "borderless", "1")
    Config.set("graphics", "resizable", "0")

Config.set("kivy", "exit_on_escape", "1")

from kivy.app import App
from kivy.uix.widget import Widget


CSS = r"""
:root{
  --bg:#0f172a; --panel:#111c36; --text:#e5e7eb; --muted:#9ca3af;
  --me:#1d4ed8; --bot:#1f2937; --border:rgba(255,255,255,.10);
}
*{box-sizing:border-box}
html,body{height:100%; margin:0}

body{
  font-family:system-ui,Tahoma,sans-serif;
  background:var(--bg);
  color:var(--text);

  /* فیت واقعی صفحه (بدون calc) */
  height: 100vh;
  height: 100dvh;
  display:flex;
  flex-direction:column;
  overflow:hidden; /* مهم: اسکرول فقط داخل chat باشد */
}

.topbar{
  flex:0 0 auto;
  height:56px;
  padding:0 12px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  border-bottom:1px solid var(--border);
  background:rgba(255,255,255,.02);
}
.title{font-weight:700}

.chat{
  flex:1 1 auto;
  overflow-y:auto;
  -webkit-overflow-scrolling: touch;
  padding:14px 12px;
  display:flex;
  flex-direction:column;
  gap:10px;
}

.row{display:flex}
.row.me{justify-content:flex-start}
.row.bot{justify-content:flex-end}

.bubble{
  max-width:82%;
  padding:10px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  line-height:1.6;
  white-space:pre-wrap;
  word-break:break-word;
}
.bubble.me{background:rgba(29,78,216,.55)}
.bubble.bot{background:var(--bot)}

.meta{
  margin-top:6px;
  font-size:12px;
  color:var(--muted);
}

.composer{
  flex:0 0 auto;
  min-height:68px;
  padding:10px 12px;
  display:grid;
  grid-template-columns:1fr auto;
  gap:10px;
  border-top:1px solid var(--border);
  background:rgba(255,255,255,.02);
}

.input{
  border:1px solid var(--border);
  border-radius:12px;
  padding:12px;
  background:var(--panel);
  color:var(--text);
  outline:none;
}
.btn{
  border:1px solid var(--border);
  border-radius:12px;
  padding:10px 14px;
  background:#16a34a;
  color:#fff;
  cursor:pointer;
  font-weight:700;
}
.btn.secondary{background:transparent; color:var(--text)}
"""

JS = r"""
const chat = document.getElementById("chat");
const txtMessage = document.getElementById("txtMessage");
const btnSend = document.getElementById("btnSend");
const btnClear = document.getElementById("btnClear");

function hasPywebview(){
  return (window.pywebview && window.pywebview.api);
}
function formatTime(tsMs){
  try{
    const d = new Date(tsMs);
    return d.toLocaleTimeString("fa-IR", {hour:"2-digit", minute:"2-digit"});
  }catch(e){ return ""; }
}
function appendMessage(from, text, tsMs){
  const row = document.createElement("div");
  row.className = "row " + (from === "me" ? "me" : "bot");

  const bubble = document.createElement("div");
  bubble.className = "bubble " + (from === "me" ? "me" : "bot");

  const t = document.createElement("div");
  t.textContent = text;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = formatTime(tsMs || Date.now());

  bubble.appendChild(t);
  bubble.appendChild(meta);
  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
}

// اندروید: پایتون این را صدا می‌زند
window.receiveFromPython = function(text){
  appendMessage("bot", text, Date.now());
}

async function loadHistoryDesktop(){
  if(!hasPywebview()) return;
  const res = await window.pywebview.api.get_history();
  if(res && res.ok){
    chat.innerHTML = "";
    res.messages.forEach(m => appendMessage(m.from, m.text, m.ts * 1000));
  }
}

async function send(){
  const text = (txtMessage.value || "").trim();
  if(!text) return;

  if(hasPywebview()){
    txtMessage.value = "";
    txtMessage.focus();

    const res = await window.pywebview.api.send_message(text);
    if(res && res.ok){
      res.messages.forEach(m => appendMessage(m.from, m.text, m.ts * 1000));
    }
  }else{
    // اندروید
    txtMessage.value = "";
    txtMessage.focus();

    appendMessage("me", text, Date.now());
    window.location.href = "app://send?text=" + encodeURIComponent(text);
  }
}

btnSend.addEventListener("click", send);
txtMessage.addEventListener("keydown", (e)=>{ if(e.key === "Enter") send(); });

btnClear.addEventListener("click", async ()=>{
  if(hasPywebview()){
    await window.pywebview.api.clear();
    await loadHistoryDesktop();
  }else{
    chat.innerHTML = "";
    window.location.href = "app://clear";
  }
});

document.addEventListener("pywebviewready", async ()=>{
  await loadHistoryDesktop();
  txtMessage.focus();
});

setTimeout(()=>txtMessage.focus(), 300);
"""

HTML = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
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


class MessengerCore:
    def __init__(self):
        self._lock = Lock()
        self._messages = []

    def history(self):
        with self._lock:
            return list(self._messages)

    def clear(self):
        with self._lock:
            self._messages.clear()

    def send(self, text: str):
        text = (text or "").strip()
        if not text:
            return None, None

        now = time.time()
        msg_me = {"id": str(uuid4()), "from": "me", "text": text, "ts": now}
        msg_bot = {"id": str(uuid4()), "from": "bot", "text": f"دریافت شد: {text}", "ts": now + 0.001}

        with self._lock:
            self._messages.append(msg_me)
            self._messages.append(msg_bot)

        return msg_me, msg_bot


class DesktopAPI:
    def __init__(self, core: MessengerCore):
        self.core = core

    def get_history(self):
        return {"ok": True, "messages": self.core.history()}

    def clear(self):
        self.core.clear()
        return {"ok": True}

    def send_message(self, text: str):
        me, bot = self.core.send(text)
        if me is None:
            return {"ok": False, "error": "پیام خالی است"}
        return {"ok": True, "messages": [me, bot]}


class Root(Widget):
    pass


class MessengerApp(App):
    def build(self):
        self.core = MessengerCore()
        return Root()

    def on_start(self):
        if platform == "android":
            self._start_android_webview()
        else:
            self._start_desktop_pywebview()

    def _start_desktop_pywebview(self):
        import webview

        api = DesktopAPI(self.core)
        webview.create_window(
            title="Messenger",
            html=HTML,
            js_api=api,
            width=420,
            height=720,
            resizable=True,
        )
        webview.start(debug=False)
        self.stop()

    def _start_android_webview(self):
        from jnius import autoclass, PythonJavaClass, java_method
        from android.runnable import run_on_ui_thread

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        WebView = autoclass("android.webkit.WebView")
        ViewGroupLayoutParams = autoclass("android.view.ViewGroup$LayoutParams")
        View = autoclass("android.view.View")
        WindowManagerLayoutParams = autoclass("android.view.WindowManager$LayoutParams")

        activity = PythonActivity.mActivity
        app_self = self

        def js_string(s: str) -> str:
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

        @run_on_ui_thread
        def create_webview():
            # 1) فول‌اسکرین/Immersive (روی سامسونگ خیلی کمک می‌کند)
            try:
                window = activity.getWindow()
                window.addFlags(WindowManagerLayoutParams.FLAG_FULLSCREEN)
                decor = window.getDecorView()
                flags = (
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )
                decor.setSystemUiVisibility(flags)
            except Exception:
                pass

            wv = WebView(activity)
            app_self.webview = wv

            settings = wv.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)

            # 2) مهم: داخل layout خود Kivy اضافه می‌کنیم تا دقیقاً تمام صفحه را بگیرد
            try:
                wv.setLayoutParams(ViewGroupLayoutParams(
                    ViewGroupLayoutParams.MATCH_PARENT,
                    ViewGroupLayoutParams.MATCH_PARENT
                ))
            except Exception:
                pass

            class Client(PythonJavaClass):
                __javainterfaces__ = ["android/webkit/WebViewClient"]
                __javacontext__ = "app"

                @java_method("(Landroid/webkit/WebView;Ljava/lang/String;)Z")
                def shouldOverrideUrlLoading(self, view, url):
                    try:
                        if not url:
                            return False

                        if url.startswith("app://send"):
                            parsed = urllib.parse.urlparse(url)
                            qs = urllib.parse.parse_qs(parsed.query or "")
                            text = (qs.get("text", [""])[0] or "").strip()

                            me, bot = app_self.core.send(text)
                            if bot is not None:
                                js = f"window.receiveFromPython({js_string(bot['text'])});"
                                try:
                                    view.evaluateJavascript(js, None)
                                except Exception:
                                    view.loadUrl("javascript:" + js)
                            return True

                        if url.startswith("app://clear"):
                            app_self.core.clear()
                            return True

                        return False
                    except Exception:
                        return False

            wv.setWebViewClient(Client())
            wv.loadDataWithBaseURL("https://app.local/", HTML, "text/html", "utf-8", None)

            # به جای addContentView:
            # layout اصلی Kivy (mLayout) را می‌گیریم و WebView را اضافه می‌کنیم
            layout = activity.mLayout
            layout.addView(
                wv,
                ViewGroupLayoutParams(
                    ViewGroupLayoutParams.MATCH_PARENT,
                    ViewGroupLayoutParams.MATCH_PARENT
                )
            )

        create_webview()


if __name__ == "__main__":
    MessengerApp().run()
