from kivy.app import App
from kivy.uix.widget import Widget
from kivy.utils import platform

import time
import urllib.parse


HTML = r"""
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Messenger</title>
  <style>
    :root{
      --bg:#0f172a; --panel:#111c36; --text:#e5e7eb; --muted:#9ca3af;
      --me:#1d4ed8; --bot:#1f2937; --border:rgba(255,255,255,.10);
    }
    *{box-sizing:border-box}
    html,body{height:100%; margin:0; font-family:system-ui,Tahoma,sans-serif; background:var(--bg); color:var(--text)}
    .topbar{height:56px; padding:0 12px; display:flex; align-items:center; justify-content:space-between;
      border-bottom:1px solid var(--border); background:rgba(255,255,255,.02)}
    .title{font-weight:700}
    .chat{height:calc(100% - 56px - 68px); overflow-y:auto; padding:14px 12px; display:flex; flex-direction:column; gap:10px}
    .row{display:flex} .row.me{justify-content:flex-start} .row.bot{justify-content:flex-end}
    .bubble{max-width:82%; padding:10px 12px; border-radius:14px; border:1px solid var(--border); line-height:1.6;
      white-space:pre-wrap; word-break:break-word}
    .bubble.me{background:rgba(29,78,216,.55)} .bubble.bot{background:var(--bot)}
    .meta{margin-top:6px; font-size:12px; color:var(--muted)}
    .composer{height:68px; padding:10px 12px; display:grid; grid-template-columns:1fr auto; gap:10px;
      border-top:1px solid var(--border); background:rgba(255,255,255,.02)}
    .input{border:1px solid var(--border); border-radius:12px; padding:12px; background:var(--panel); color:var(--text); outline:none}
    .btn{border:1px solid var(--border); border-radius:12px; padding:10px 14px; background:#16a34a; color:#fff; cursor:pointer; font-weight:700}
    .btn.secondary{background:transparent; color:var(--text)}
  </style>
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

<script>
  const chat = document.getElementById("chat");
  const txtMessage = document.getElementById("txtMessage");
  const btnSend = document.getElementById("btnSend");
  const btnClear = document.getElementById("btnClear");

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
    meta.textContent = formatTime(tsMs);

    bubble.appendChild(t);
    bubble.appendChild(meta);
    row.appendChild(bubble);
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
  }

  function send(){
    const text = (txtMessage.value || "").trim();
    if(!text) return;

    txtMessage.value = "";
    txtMessage.focus();

    // اول پیام خود کاربر را در UI نشان می‌دهیم
    appendMessage("me", text, Date.now());

    // بعد به پایتون پیام می‌دهیم (بدون فایل JS جدا)
    const url = "app://send?text=" + encodeURIComponent(text);
    window.location.href = url; // WebViewClient در پایتون این را intercept می‌کند
  }

  btnSend.addEventListener("click", send);
  txtMessage.addEventListener("keydown", (e)=>{ if(e.key === "Enter") send(); });

  btnClear.addEventListener("click", ()=>{
    chat.innerHTML = "";
    window.location.href = "app://clear";
  });

  // این تابع را پایتون صدا می‌زند تا پیام بات اضافه شود
  window.receiveFromPython = function(text){
    appendMessage("bot", text, Date.now());
  }

  // فوکوس اولیه
  setTimeout(()=>txtMessage.focus(), 300);
</script>
</body>
</html>
"""


class Root(Widget):
    pass


class MessengerApp(App):
    def build(self):
        return Root()

    def on_start(self):
        if platform != "android":
            raise RuntimeError("این نسخه مخصوص اندروید است (pyjnius + Android WebView).")

        # --- Android / WebView setup ---
        from jnius import autoclass, PythonJavaClass, java_method
        from android.runnable import run_on_ui_thread

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        LayoutParams = autoclass("android.view.ViewGroup$LayoutParams")

        activity = PythonActivity.mActivity

        app_self = self  # برای دسترسی داخل کلاس Java

        @run_on_ui_thread
        def create_webview():
            app_self.webview = WebView(activity)
            settings = app_self.webview.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)

            class Client(PythonJavaClass):
                __javainterfaces__ = ["android/webkit/WebViewClient"]
                __javacontext__ = "app"

                def _handle_url(self, view, url: str):
                    if not url:
                        return False
                    if url.startswith("app://send"):
                        parsed = urllib.parse.urlparse(url)
                        qs = urllib.parse.parse_qs(parsed.query or "")
                        text = (qs.get("text", [""])[0] or "").strip()

                        # پاسخ نمونه بات:
                        reply = f"دریافت شد: {text}"

                        # صدا زدن تابع JS برای افزودن پیام بات
                        js = "window.receiveFromPython(%s);" % (self._js_string(reply))
                        try:
                            view.evaluateJavascript(js, None)  # API 19+
                        except Exception:
                            view.loadUrl("javascript:" + js)
                        return True

                    if url.startswith("app://clear"):
                        return True

                    return False

                def _js_string(self, s: str) -> str:
                    # تبدیل رشته پایتون به string literal امن برای JS
                    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

                # Android قدیمی‌تر:
                @java_method("(Landroid/webkit/WebView;Ljava/lang/String;)Z")
                def shouldOverrideUrlLoading(self, view, url):
                    try:
                        return self._handle_url(view, url)
                    except Exception:
                        return False

                # Android جدیدتر (گاهی این یکی صدا زده می‌شود):
                @java_method("(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)Z")
                def shouldOverrideUrlLoading2(self, view, request):
                    try:
                        u = request.getUrl().toString()
                        return self._handle_url(view, u)
                    except Exception:
                        return False

            app_self.webview.setWebViewClient(Client())

            app_self.webview.loadDataWithBaseURL(
                "https://app.local/",  # baseURL
                HTML,
                "text/html",
                "utf-8",
                None
            )

            activity.addContentView(
                app_self.webview,
                LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
            )

        create_webview()


if __name__ == "__main__":
    MessengerApp().run()
