import os
import re
import threading
from threading import Event

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.utils import platform


KV = r"""
BoxLayout:
    orientation: "vertical"
    padding: dp(16)
    spacing: dp(12)

    canvas.before:
        Color:
            rgba: (0.07, 0.08, 0.11, 1)
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: "Video Downloader"
        font_size: "24sp"
        bold: True
        color: (1, 1, 1, 1)
        size_hint_y: None
        height: dp(40)

    TextInput:
        id: url_input
        hint_text: "Paste Instagram or YouTube URL"
        multiline: False
        write_tab: False
        cursor_color: (1, 1, 1, 1)
        foreground_color: (1, 1, 1, 1)
        background_color: (0.12, 0.14, 0.19, 1)
        padding: [dp(12), dp(14), dp(12), dp(14)]
        size_hint_y: None
        height: dp(52)

    Label:
        text: app.status_text
        color: (0.85, 0.85, 0.85, 1)
        text_size: self.width, None
        halign: "left"
        valign: "middle"
        size_hint_y: None
        height: dp(46)

    ProgressBar:
        max: 100
        value: app.progress
        size_hint_y: None
        height: dp(10)

    Label:
        text: app.progress_text
        color: (0.92, 0.92, 0.92, 1)
        text_size: self.width, None
        halign: "left"
        valign: "middle"
        size_hint_y: None
        height: dp(24)

    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(12)

        Button:
            text: "Download"
            disabled: app.is_downloading
            on_release: app.start_download(url_input.text)
            background_normal: ""
            background_color: (0.18, 0.62, 0.90, 1)
            color: (1, 1, 1, 1)

        Button:
            text: "Abort"
            disabled: not app.is_downloading
            on_release: app.abort_download()
            background_normal: ""
            background_color: (0.86, 0.22, 0.22, 1)
            color: (1, 1, 1, 1)

    Label:
        text: "Saved to: " + app.download_dir
        font_size: "12sp"
        color: (0.62, 0.62, 0.62, 1)
        text_size: self.width, None
        halign: "left"
        valign: "top"
"""


def human_bytes(n: float) -> str:
    try:
        n = float(n)
    except Exception:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.1f} {units[i]}"


def safe_one_line(s: str, max_len: int = 140) -> str:
    s = (s or "").strip().replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s[:max_len]


class VideoDownloaderApp(App):
    status_text = StringProperty("Ready.")
    progress_text = StringProperty("0%")
    progress = NumericProperty(0.0)
    is_downloading = BooleanProperty(False)
    download_dir = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.abort_event = Event()
        self._dl_thread = None

        self._current_filename = None
        self._current_tmpfilename = None

    def build(self):
        self.title = "Video Downloader"
        self.download_dir = self._get_download_dir()
        os.makedirs(self.download_dir, exist_ok=True)
        return Builder.load_string(KV)

    def on_start(self):
        # Runtime permissions (Android)
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission

                perms = [
                    Permission.INTERNET,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
                # Android 13+ notifications
                try:
                    perms.append(Permission.POST_NOTIFICATIONS)
                except Exception:
                    pass

                request_permissions(perms)
            except Exception:
                pass

    def _get_download_dir(self) -> str:
        # 1) plyer (best when it works)
        try:
            from plyer import storagepath
            d = storagepath.get_downloads_dir()
            if d:
                return d
        except Exception:
            pass

        # 2) Android public Downloads folder path
        if platform == "android":
            try:
                from jnius import autoclass
                Environment = autoclass("android.os.Environment")
                d = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS
                ).getAbsolutePath()
                if d:
                    return d
            except Exception:
                pass

        # 3) fallback
        return os.path.join(os.path.expanduser("~"), "Downloads")

    # ---------------- UI helpers ----------------
    def _ui_set(self, *, status=None, progress=None, progress_text=None, downloading=None):
        def _apply(_dt):
            if status is not None:
                self.status_text = status
            if progress is not None:
                self.progress = float(progress)
            if progress_text is not None:
                self.progress_text = progress_text
            if downloading is not None:
                self.is_downloading = bool(downloading)

        Clock.schedule_once(_apply, 0)

    def _notify(self, title: str, message: str):
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Video Downloader",
                timeout=6,
            )
        except Exception:
            pass

    # ---------------- Actions ----------------
    def start_download(self, url: str):
        url = (url or "").strip()
        if not url:
            self._ui_set(status="Please paste a URL first.")
            return

        if self.is_downloading:
            self._ui_set(status="A download is already running.")
            return

        self.abort_event.clear()
        self._current_filename = None
        self._current_tmpfilename = None

        self._ui_set(
            status="Starting download...",
            progress=0,
            progress_text="0%",
            downloading=True,
        )

        self._dl_thread = threading.Thread(
            target=self._download_worker, args=(url,), daemon=True
        )
        self._dl_thread.start()

    def abort_download(self):
        if not self.is_downloading:
            return
        self.abort_event.set()
        self._ui_set(status="Abort requested...")

    # ---------------- Download logic ----------------
    def _cleanup_partials(self):
        candidates = set()

        if self._current_filename:
            candidates.add(self._current_filename)
            candidates.add(self._current_filename + ".part")
            candidates.add(self._current_filename + ".ytdl")

        if self._current_tmpfilename:
            candidates.add(self._current_tmpfilename)
            candidates.add(self._current_tmpfilename + ".part")
            candidates.add(self._current_tmpfilename + ".ytdl")

        for p in candidates:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    def _progress_hook(self, d: dict):
        # Abort as soon as possible
        if self.abort_event.is_set():
            try:
                import yt_dlp
                raise yt_dlp.utils.DownloadCancelled()
            except Exception:
                raise Exception("Download cancelled")

        status = d.get("status")
        self._current_filename = d.get("filename") or self._current_filename
        self._current_tmpfilename = d.get("tmpfilename") or self._current_tmpfilename

        if status == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            speed = d.get("speed") or 0

            pct = (downloaded / total * 100.0) if total else 0.0

            text = f"{pct:5.1f}%  |  {human_bytes(downloaded)} / {human_bytes(total) if total else 'Unknown'}"
            if speed:
                text += f"  |  {human_bytes(speed)}/s"

            self._ui_set(
                status="Downloading...",
                progress=pct if total else self.progress,
                progress_text=text,
            )

        elif status == "finished":
            self._ui_set(status="Finalizing...", progress_text="Processing...")

    def _download_worker(self, url: str):
        try:
            import yt_dlp

            outtmpl = os.path.join(self.download_dir, "%(title).120s.%(ext)s")

            ydl_opts = {
                "outtmpl": outtmpl,
                "noplaylist": True,
                "retries": 3,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self._progress_hook],

                # Try to avoid merge requirements (ffmpeg) by preferring single-file mp4
                "format": "best[ext=mp4]/best",
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            title = safe_one_line(info.get("title") or "Video")
            self._ui_set(
                status="Download complete.",
                progress=100,
                progress_text="100%",
                downloading=False,
            )
            self._notify("Download complete", title)

        except Exception as e:
            # If aborted => clean partials
            if self.abort_event.is_set():
                self._cleanup_partials()
                self._ui_set(
                    status="Aborted. Partial files removed.",
                    progress=0,
                    progress_text="0%",
                    downloading=False,
                )
                return

            # Other errors
            msg = safe_one_line(str(e), 200)
            self._ui_set(
                status=f"Error: {msg}",
                downloading=False,
            )


if __name__ == "__main__":
    VideoDownloaderApp().run()

