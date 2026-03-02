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
from kivy.resources import resource_find
from kivy.core.clipboard import Clipboard  # استفاده از کلیپبورد داخلی Kivy


KV_CODE = r"""
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
            text: "Just Audio (MP3)"
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
        text: ""
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
    quality_labels = ListProperty(["Auto"])
    quality_spinner_text = StringProperty("Auto")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.abort_event = Event()
        self._dl_thread = None

        self._current_filename = None
        self._current_tmpfilename = None

        self._quality_map = {"Auto": None}
        self._selected_format_id = None

        self._last_url = ""
        self._fetch_trigger = Clock.create_trigger(self._debounced_fetch_qualities, 0.6)
        self._fetch_thread = None
        self._fetch_cancel_token = 0
        
        # برای ذخیره وضعیت دسترسی‌ها
        self._permissions_granted = False

    def build(self):
        self.title = "Video Downloader"
        self.download_dir = self._get_download_dir()
        os.makedirs(self.download_dir, exist_ok=True)
        return Builder.load_string(KV_CODE)

    def on_start(self):
        """درخواست دسترسی‌ها هنگام شروع برنامه"""
        if platform == "android":
            self._request_android_permissions()
        else:
            self._permissions_granted = True

    def _request_android_permissions(self):
        """درخواست تمام دسترسی‌های لازم در اندروید"""
        try:
            from android.permissions import request_permissions, Permission, check_permission
            
            permissions_list = [
                Permission.INTERNET,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ]
            
            # اضافه کردن دسترسی نوتیفیکیشن برای اندروید 13+
            try:
                if hasattr(Permission, 'POST_NOTIFICATIONS'):
                    permissions_list.append(Permission.POST_NOTIFICATIONS)
            except Exception:
                pass
            
            # اضافه کردن دسترسی‌های مدیا برای اندروید 13+
            try:
                if hasattr(Permission, 'READ_MEDIA_VIDEO'):
                    permissions_list.append(Permission.READ_MEDIA_VIDEO)
                if hasattr(Permission, 'READ_MEDIA_AUDIO'):
                    permissions_list.append(Permission.READ_MEDIA_AUDIO)
            except Exception:
                pass

            def callback(permissions, results):
                """کالبک بعد از دریافت دسترسی‌ها"""
                granted = all(results)
                self._permissions_granted = granted
                if granted:
                    Clock.schedule_once(lambda dt: self._ui_set(status="Ready. Permissions granted."), 0)
                else:
                    Clock.schedule_once(lambda dt: self._ui_set(status="Some permissions denied."), 0)
            
            request_permissions(permissions_list, callback)
            
        except Exception as e:
            print(f"Permission request error: {e}")
            self._permissions_granted = True

    def _get_download_dir(self) -> str:
        """مسیر دانلود را برمی‌گرداند"""
        if platform == "android":
            # روش اول: استفاده از pyjnius
            try:
                from jnius import autoclass
                Environment = autoclass("android.os.Environment")
                downloads = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS
                ).getAbsolutePath()
                if downloads and os.path.exists(downloads):
                    return downloads
            except Exception as e:
                print(f"pyjnius error: {e}")
            
            # روش دوم: استفاده از plyer
            try:
                from plyer import storagepath
                d = storagepath.get_downloads_dir()
                if d and os.path.exists(d):
                    return d
            except Exception as e:
                print(f"plyer storagepath error: {e}")
            
            # روش سوم: مسیر پیش‌فرض
            default_path = "/storage/emulated/0/Download"
            if os.path.exists(default_path):
                return default_path
            
            # روش چهارم: app data directory
            return self.user_data_dir
        
        else:
            # برای ویندوز/لینوکس/مک
            try:
                from plyer import storagepath
                d = storagepath.get_downloads_dir()
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

    # =============== کلیپبورد - با چندین روش ===============
    def paste_url(self):
        """خواندن از کلیپبورد با چندین روش پشتیبان"""
        txt = ""
        
        # روش 1: استفاده از Clipboard داخلی Kivy (بهترین روش)
        try:
            txt = Clipboard.paste()
            if txt:
                txt = txt.strip()
        except Exception as e:
            print(f"Kivy Clipboard error: {e}")
            txt = ""
        
        # روش 2: برای اندروید - استفاده از Android SDK
        if not txt and platform == "android":
            txt = self._get_clipboard_android()
        
        # روش 3: استفاده از plyer
        if not txt:
            try:
                from plyer import clipboard as plyer_clipboard
                txt = plyer_clipboard.paste() or ""
                txt = txt.strip()
            except Exception as e:
                print(f"Plyer clipboard error: {e}")
        
        # نتیجه
        if txt:
            try:
                self.root.ids.url_input.text = txt
                self._ui_set(status="URL pasted successfully.")
            except Exception:
                pass
        else:
            self._ui_set(status="Clipboard is empty or cannot access.")
    
    def _get_clipboard_android(self) -> str:
        """خواندن کلیپبورد در اندروید با استفاده از Java API"""
        try:
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            ClipboardManager = autoclass('android.content.ClipboardManager')
            
            activity = PythonActivity.mActivity
            clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)
            clipboard = cast('android.content.ClipboardManager', clipboard)
            
            if clipboard.hasPrimaryClip():
                clip = clipboard.getPrimaryClip()
                if clip and clip.getItemCount() > 0:
                    item = clip.getItemAt(0)
                    text = item.getText()
                    if text:
                        return str(text).strip()
            return ""
        except Exception as e:
            print(f"Android clipboard error: {e}")
            return ""

    # =============== نوتیفیکیشن - با چندین روش ===============
    def _notify(self, title: str, message: str):
        """ارسال نوتیفیکیشن با چندین روش پشتیبان"""
        if platform == "android":
            self._notify_android(title, message)
        else:
            self._notify_desktop(title, message)
    
    def _notify_android(self, title: str, message: str):
        """نوتیفیکیشن اندروید با استفاده از Java API"""
        try:
            from jnius import autoclass
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            NotificationManager = autoclass('android.app.NotificationManager')
            
            # برای اندروید 8+
            try:
                NotificationChannel = autoclass('android.app.NotificationChannel')
                
                activity = PythonActivity.mActivity
                notification_service = activity.getSystemService(Context.NOTIFICATION_SERVICE)
                
                # ایجاد کانال نوتیفیکیشن
                channel_id = "video_downloader_channel"
                channel_name = "Video Downloader"
                importance = 3  # IMPORTANCE_DEFAULT
                
                channel = NotificationChannel(channel_id, channel_name, importance)
                notification_service.createNotificationChannel(channel)
                
                # ساخت نوتیفیکیشن
                builder = NotificationBuilder(activity, channel_id)
                builder.setContentTitle(title)
                builder.setContentText(message)
                builder.setSmallIcon(activity.getApplicationInfo().icon)
                builder.setAutoCancel(True)
                
                notification = builder.build()
                notification_service.notify(1, notification)
                
            except Exception as e:
                print(f"Notification channel error: {e}")
                # روش قدیمی برای اندروید < 8
                self._notify_android_legacy(title, message)
                
        except Exception as e:
            print(f"Android notification error: {e}")
            # fallback to plyer
            self._notify_plyer(title, message)
    
    def _notify_android_legacy(self, title: str, message: str):
        """نوتیفیکیشن برای اندروید قدیمی"""
        try:
            from jnius import autoclass
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            
            activity = PythonActivity.mActivity
            notification_service = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            
            builder = NotificationBuilder(activity)
            builder.setContentTitle(title)
            builder.setContentText(message)
            builder.setSmallIcon(activity.getApplicationInfo().icon)
            builder.setAutoCancel(True)
            
            notification = builder.build()
            notification_service.notify(1, notification)
            
        except Exception as e:
            print(f"Legacy notification error: {e}")
            self._notify_plyer(title, message)
    
    def _notify_plyer(self, title: str, message: str):
        """نوتیفیکیشن با استفاده از plyer"""
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Video Downloader",
                timeout=6,
            )
        except Exception as e:
            print(f"Plyer notification error: {e}")
    
    def _notify_desktop(self, title: str, message: str):
        """نوتیفیکیشن برای دسکتاپ (ویندوز/لینوکس/مک)"""
        # روش 1: plyer
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Video Downloader",
                timeout=6,
            )
            return
        except Exception as e:
            print(f"Desktop plyer notification error: {e}")
        
        # روش 2: برای ویندوز - win10toast
        if platform == "win":
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=6, threaded=True)
                return
            except Exception:
                pass
        
        # روش 3: print به کنسول
        print(f"[NOTIFICATION] {title}: {message}")

    # =============== URL / Qualities ===============
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
        self._quality_map = {"Auto": None}
        self._selected_format_id = None
        self.quality_labels = ["Auto"]
        self.quality_spinner_text = "Auto"
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

            items = []
            for f in formats:
                if not isinstance(f, dict):
                    continue
                if f.get("vcodec") in (None, "none"):
                    continue
                if f.get("acodec") in (None, "none"):
                    continue

                height = f.get("height") or 0
                ext = (f.get("ext") or "").lower()
                fps = f.get("fps") or ""
                fmt_id = f.get("format_id")
                if not fmt_id:
                    continue

                filesize = f.get("filesize") or f.get("filesize_approx") or 0

                mp4_bonus = 1 if ext == "mp4" else 0

                label = f"{height}p {ext.upper()}"
                if fps:
                    label += f" {int(fps)}fps" if str(fps).isdigit() else f" {fps}fps"
                if filesize:
                    label += f" • {human_bytes(filesize)}"

                items.append((height, mp4_bonus, label, fmt_id))

            items.sort(key=lambda x: (x[0], x[1]), reverse=True)

            new_map = {"Auto": None}
            new_labels = ["Auto"]

            for _h, _b, label, fmt_id in items[:18]:
                if label in new_map:
                    continue
                new_map[label] = fmt_id
                new_labels.append(label)

            def _apply(_dt):
                if not self.is_youtube or (self._last_url.strip() != url.strip()):
                    self.is_fetching_qualities = False
                    return

                self._quality_map = new_map
                self.quality_labels = new_labels
                self.quality_spinner_text = "Auto"
                self._selected_format_id = None
                self.is_fetching_qualities = False
                self._ui_set(status="Ready.")

            Clock.schedule_once(_apply, 0)

        except Exception as e:
            msg = safe_one_line(str(e))
            def _apply(_dt):
                self.is_fetching_qualities = False
                self._reset_qualities()
                self._ui_set(status=f"Could not read qualities. Using Auto. ({msg})")
            Clock.schedule_once(_apply, 0)

    # =============== Download actions ===============
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
            self._ui_set(status="Just Audio (MP3) is enabled only for YouTube URLs.")
            return
        if self.is_downloading:
            self._ui_set(status="A download is already running.")
            return

        self._start_download(url, mode="audio_mp3")

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

    # =============== yt-dlp helpers ===============
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

    def _ensure_ffmpeg_for_mp3(self) -> str | None:
        ffmpeg_src = resource_find("ffmpeg/ffmpeg")
        if not ffmpeg_src:
            return None

        dst_dir = os.path.join(self.user_data_dir, "ffmpeg_bin")
        os.makedirs(dst_dir, exist_ok=True)

        ffmpeg_dst = os.path.join(dst_dir, "ffmpeg")
        ffprobe_src = resource_find("ffmpeg/ffprobe")
        ffprobe_dst = os.path.join(dst_dir, "ffprobe")

        try:
            if not os.path.exists(ffmpeg_dst):
                shutil.copy(ffmpeg_src, ffmpeg_dst)
                os.chmod(ffmpeg_dst, 0o755)

            if ffprobe_src and (not os.path.exists(ffprobe_dst)):
                shutil.copy(ffprobe_src, ffprobe_dst)
                os.chmod(ffprobe_dst, 0o755)

            return dst_dir
        except Exception:
            return None

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
                    ydl_opts["format"] = self._selected_format_id
                else:
                    ydl_opts["format"] = "best[ext=mp4]/best"

            elif mode == "audio_mp3":
                ffmpeg_location = self._ensure_ffmpeg_for_mp3()
                if ffmpeg_location:
                    ydl_opts["ffmpeg_location"] = ffmpeg_location

                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]
                ydl_opts["keepvideo"] = False

            else:
                raise ValueError("Unknown download mode")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            title = safe_one_line((info or {}).get("title") or "Media")

            self._ui_set(
                status=f"Download complete! Saved to: {self.download_dir}",
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
            if "ffmpeg" in msg.lower() or "ffprobe" in msg.lower():
                msg = "FFmpeg not found. MP3 extraction requires FFmpeg."

            self._ui_set(
                status=f"Error: {msg}",
                downloading=False,
            )


if __name__ == "__main__":
    VideoDownloaderApp().run()
