import os
import re
import shutil
import threading
from threading import Event

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    StringProperty,
    NumericProperty,
    BooleanProperty,
    ListProperty,
)
from kivy.metrics import dp
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

    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(10)

        TextInput:
            id: url_input
            hint_text: "Paste Instagram or YouTube URL"
            multiline: False
            write_tab: False
            cursor_color: (1, 1, 1, 1)
            foreground_color: (1, 1, 1, 1)
            background_color: (0.12, 0.14, 0.19, 1)
            padding: [dp(12), dp(14), dp(12), dp(14)]
            disabled: app.is_downloading
            on_text: app.on_url_text(self.text)

        Button:
            text: "Paste"
            size_hint_x: None
            width: dp(88)
            on_release: app.paste_url()
            disabled: app.is_downloading
            background_normal: ""
            background_color: (0.22, 0.26, 0.35, 1)
            color: (1, 1, 1, 1)

    BoxLayout:
        size_hint_y: None
        height: dp(44)
        spacing: dp(10)

        Label:
            text: "Quality"
            size_hint_x: None
            width: dp(70)
            color: (0.85, 0.85, 0.85, 1)
            halign: "left"
            valign: "middle"
            text_size: self.size

        Spinner:
            id: quality_spinner
            text: app.quality_spinner_text
            values: app.quality_labels
            disabled: (not app.is_youtube) or app.is_downloading or app.is_fetching_qualities
            on_text: app.on_quality_selected(self.text)
            background_normal: ""
            background_color: (0.12, 0.14, 0.19, 1)
            color: (1, 1, 1, 1)

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
            text: "Abort"
            disabled: not app.is_downloading
            on_release: app.abort_download()
            background_normal: ""
            background_color: (0.86, 0.22, 0.22, 1)
            color: (1, 1, 1, 1)

        Button:
            text: "Just Audio (M4A)"
            disabled: (not app.is_youtube) or app.is_downloading
            on_release: app.start_audio_download()
            background_normal: ""
            background_color: (0.25, 0.75, 0.45, 1)
            color: (1, 1, 1, 1)

        Button:
            text: "Download"
            disabled: app.is_downloading
            on_release: app.start_video_download()
            background_normal: ""
            background_color: (0.18, 0.62, 0.90, 1)
            color: (1, 1, 1, 1)

    Label:
        text: 
        font_size: "12sp"
        color: (0.62, 0.62, 0.62, 1)
        text_size: self.width, None
        halign: "left"
        valign: "top"
"""


def safe_one_line(s: str, max_len: int = 180) -> str:
    s = (s or "").strip().replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s[:max_len]


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


def is_youtube_url(url: str) -> bool:
    u = (url or "").lower()
    return ("youtube.com" in u) or ("youtu.be" in u)


def is_instagram_url(url: str) -> bool:
    u = (url or "").lower()
    return "instagram.com" in u


class VideoDownloaderApp(App):
    status_text = StringProperty("Ready.")
    progress_text = StringProperty("0%")
    progress = NumericProperty(0.0)
    is_downloading = BooleanProperty(False)

    download_dir = StringProperty("")

    # YouTube qualities UI
    is_youtube = BooleanProperty(False)
    is_fetching_qualities = BooleanProperty(False)
    quality_labels = ListProperty(["Best Available"])
    quality_spinner_text = StringProperty("Best Available")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.abort_event = Event()
        self._dl_thread = None

        self._current_filename = None
        self._current_tmpfilename = None

        self._quality_map = {"Best Available": None}
        self._selected_format_id = None

        self._last_url = ""
        self._fetch_trigger = Clock.create_trigger(self._debounced_fetch_qualities, 0.6)
        self._fetch_thread = None
        self._fetch_cancel_token = 0

    def build(self):
        self.title = "Video Downloader"
        self.download_dir = self._get_download_dir()
        os.makedirs(self.download_dir, exist_ok=True)
        return Builder.load_string(KV)

    def on_start(self):
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                perms = [
                    Permission.INTERNET,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
                try:
                    perms.append(Permission.POST_NOTIFICATIONS)
                except Exception:
                    pass
                request_permissions(perms)
            except Exception:
                pass

    def _get_download_dir(self) -> str:
        try:
            from plyer import storagepath
            d = storagepath.get_downloads_dir()
            if d:
                return d
        except Exception:
            pass

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

        return os.path.join(os.path.expanduser("~"), "Downloads")

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

    def _clear_url_input(self):
        def _apply(_dt):
            try:
                self.root.ids.url_input.text = ""
            except Exception:
                pass
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

    def paste_url(self):
        try:
            from plyer import clipboard
            txt = clipboard.paste() or ""
        except Exception:
            txt = ""
        txt = txt.strip()

        if not txt:
            self._ui_set(status="Clipboard is empty.")
            return

        try:
            self.root.ids.url_input.text = txt
        except Exception:
            pass

    # ---------------- URL / Qualities ----------------
    def on_url_text(self, text: str):
        if self.is_downloading:
            return

        url = (text or "").strip()
        if not url:
            self.is_youtube = False
            self._reset_qualities()
            return

        if is_instagram_url(url):
            self.is_youtube = False
            self._reset_qualities()
            return

        if is_youtube_url(url):
            self.is_youtube = True
            if url != self._last_url:
                self._last_url = url
                self._fetch_trigger()
        else:
            self.is_youtube = False
            self._reset_qualities()

    def _reset_qualities(self):
        self._quality_map = {"Best Available": None}
        self._selected_format_id = None
        self.quality_labels = ["Best Available"]
        self.quality_spinner_text = "Best Available"
        self.is_fetching_qualities = False

    def on_quality_selected(self, label: str):
        self._selected_format_id = self._quality_map.get(label)
        self.quality_spinner_text = label

    def _debounced_fetch_qualities(self, _dt):
        url = (self._last_url or "").strip()
        if not (self.is_youtube and url):
            return
        if self.is_fetching_qualities:
            return

        self.is_fetching_qualities = True
        self._ui_set(status="Reading available qualities...")

        self._fetch_cancel_token += 1
        token = self._fetch_cancel_token

        self._fetch_thread = threading.Thread(
            target=self._fetch_qualities_worker, args=(url, token), daemon=True
        )
        self._fetch_thread.start()

    def _fetch_qualities_worker(self, url: str, token: int):
        try:
            import yt_dlp

            if token != self._fetch_cancel_token:
                return

            opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if isinstance(info, dict) and info.get("entries"):
                info = info["entries"][0]

            formats = (info or {}).get("formats") or []

            # ============ فقط فرمت‌های PROGRESSIVE (ویدیو + صدا با هم) ============
            progressive_formats = []
            
            for f in formats:
                if not isinstance(f, dict):
                    continue
                
                # باید هم ویدیو داشته باشد هم صدا
                vcodec = f.get("vcodec")
                acodec = f.get("acodec")
                
                if not vcodec or vcodec == "none":
                    continue
                if not acodec or acodec == "none":
                    continue
                
                height = f.get("height") or 0
                if height < 144:
                    continue
                
                ext = (f.get("ext") or "").lower()
                fps = f.get("fps") or 30
                fmt_id = f.get("format_id")
                if not fmt_id:
                    continue
                
                filesize = f.get("filesize") or f.get("filesize_approx") or 0
                tbr = f.get("tbr") or f.get("vbr") or 0
                
                # ترجیح: MP4 > WEBM
                format_priority = 2 if ext == "mp4" else (1 if ext == "webm" else 0)
                
                progressive_formats.append({
                    "height": height,
                    "ext": ext,
                    "fps": fps,
                    "fmt_id": fmt_id,
                    "filesize": filesize,
                    "tbr": tbr,
                    "format_priority": format_priority,
                })
            
            # گروه‌بندی براساس کیفیت (height)
            quality_groups = {}
            for fmt in progressive_formats:
                h = fmt["height"]
                if h not in quality_groups:
                    quality_groups[h] = []
                quality_groups[h].append(fmt)
            
            # برای هر کیفیت بهترین فرمت را انتخاب کن
            items = []
            for height in sorted(quality_groups.keys(), reverse=True):
                # مرتب‌سازی: MP4 اولویت دارد، سپس بیترت بالاتر
                fmts = sorted(
                    quality_groups[height],
                    key=lambda x: (x["format_priority"], x["tbr"]),
                    reverse=True
                )
                best = fmts[0]
                
                label = f"{best['height']}p"
                
                # افزودن FPS اگر بالای 30 باشد
                if best['fps'] and int(best['fps']) > 30:
                    label += f" {int(best['fps'])}fps"
                
                label += f" {best['ext'].upper()}"
                
                # افزودن حجم فایل
                if best['filesize']:
                    label += f" • {human_bytes(best['filesize'])}"
                elif best['tbr']:
                    # تخمین حجم براساس بیترت (فقط نمایشی)
                    # فرض: ویدیو 3 دقیقه‌ای
                    estimated = (best['tbr'] * 1024 * 180) / 8
                    label += f" • ~{human_bytes(estimated)}"
                
                items.append((best['height'], label, best['fmt_id']))
            
            # محدود کردن به 25 گزینه
            items = items[:25]
            
            new_map = {"Best Available": "best[ext=mp4]/best"}
            new_labels = ["Best Available"]
            
            for _h, label, fmt_id in items:
                # جلوگیری از تکرار
                counter = 1
                original_label = label
                while label in new_map:
                    counter += 1
                    label = f"{original_label} ({counter})"
                
                new_map[label] = fmt_id
                new_labels.append(label)

            def _apply(_dt):
                if not self.is_youtube or (self._last_url.strip() != url.strip()):
                    self.is_fetching_qualities = False
                    return

                self._quality_map = new_map
                self.quality_labels = new_labels
                self.quality_spinner_text = "Best Available"
                self._selected_format_id = None
                self.is_fetching_qualities = False
                
                if len(new_labels) > 1:
                    self._ui_set(status=f"Found {len(new_labels)-1} progressive qualities. Select and download.")
                else:
                    self._ui_set(status="Only auto quality available for this video.")

            Clock.schedule_once(_apply, 0)

        except Exception as e:
            msg = safe_one_line(str(e))
            def _apply(_dt):
                self.is_fetching_qualities = False
                self._reset_qualities()
                self._ui_set(status=f"Could not fetch qualities: {msg}")
            Clock.schedule_once(_apply, 0)

    # ---------------- Download actions ----------------
    def start_video_download(self):
        url = ""
        try:
            url = (self.root.ids.url_input.text or "").strip()
        except Exception:
            pass

        if not url:
            self._ui_set(status="Please paste a URL first.")
            return
        if self.is_downloading:
            self._ui_set(status="A download is already running.")
            return

        self._start_download(url, mode="video")

    def start_audio_download(self):
        url = ""
        try:
            url = (self.root.ids.url_input.text or "").strip()
        except Exception:
            pass

        if not url:
            self._ui_set(status="Please paste a URL first.")
            return
        if not self.is_youtube:
            self._ui_set(status="Audio download is only for YouTube URLs.")
            return
        if self.is_downloading:
            self._ui_set(status="A download is already running.")
            return

        self._start_download(url, mode="audio_m4a")

    def abort_download(self):
        if not self.is_downloading:
            return
        self.abort_event.set()
        self._ui_set(status="Abort requested...")

    def _start_download(self, url: str, mode: str):
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
            target=self._download_worker, args=(url, mode), daemon=True
        )
        self._dl_thread.start()

    # ---------------- yt-dlp helpers ----------------
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

            text = f"{pct:5.1f}%  |  {human_bytes(downloaded)}"
            if total:
                text += f" / {human_bytes(total)}"
            if speed:
                text += f"  |  {human_bytes(speed)}/s"

            self._ui_set(
                status="Downloading...",
                progress=pct if total else self.progress,
                progress_text=text,
            )

        elif status == "finished":
            self._ui_set(status="Finalizing...", progress_text="Processing...")

    def _download_worker(self, url: str, mode: str):
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
            }

            if mode == "video":
                if self.is_youtube and self._selected_format_id:
                    # استفاده از فرمت انتخابی کاربر
                    ydl_opts["format"] = self._selected_format_id
                else:
                    # پیش‌فرض: بهترین فرمت progressive (MP4 در اولویت)
                    ydl_opts["format"] = "best[ext=mp4]/best"

            elif mode == "audio_m4a":
                # دانلود فقط صدا (بدون نیاز به ffmpeg - فرمت M4A)
                ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio"
                ydl_opts["postprocessors"] = []

            else:
                raise ValueError("Unknown download mode")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            title = safe_one_line((info or {}).get("title") or "Media")

            self._ui_set(
                status="Download complete!",
                progress=100,
                progress_text="100%",
                downloading=False,
            )
            self._notify("Download complete", title)
            self._clear_url_input()

        except Exception as e:
            if self.abort_event.is_set():
                self._cleanup_partials()
                self._ui_set(
                    status="Aborted. Partial files removed.",
                    progress=0,
                    progress_text="0%",
                    downloading=False,
                )
                self._clear_url_input()
                return

            msg = safe_one_line(str(e), 220)
            self._ui_set(
                status=f"Error: {msg}",
                downloading=False,
            )


if __name__ == "__main__":
    VideoDownloaderApp().run()
