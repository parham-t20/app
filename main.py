from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window
import threading
import os
import sys

Window.size = (360, 640)


class DownloaderApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.download_thread = None
        self.is_downloading = False
        self.current_file = None
        self.download_path = None

    def build(self):
        self.title = "Video Downloader"

        if platform == 'android':
            self.request_android_permissions()

        main_layout = BoxLayout(orientation='vertical', padding=15, spacing=12)

        title_label = Label(
            text='YouTube & Instagram Downloader',
            size_hint_y=0.12,
            font_size='22sp',
            bold=True,
            color=(0.2, 0.6, 0.9, 1)
        )
        main_layout.add_widget(title_label)

        self.url_input = TextInput(
            hint_text='Paste YouTube or Instagram link here...',
            multiline=False,
            size_hint_y=0.12,
            font_size='15sp',
            padding=[10, 10],
            background_color=(0.95, 0.95, 0.95, 1),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1)
        )
        main_layout.add_widget(self.url_input)

        main_layout.add_widget(Label(size_hint_y=0.05))

        self.status_label = Label(
            text='Ready to download',
            size_hint_y=0.1,
            font_size='16sp',
            color=(0.3, 0.3, 0.3, 1)
        )
        main_layout.add_widget(self.status_label)

        progress_layout = BoxLayout(orientation='vertical', size_hint_y=0.15, spacing=5)

        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=0.6
        )
        progress_layout.add_widget(self.progress_bar)

        self.percent_label = Label(
            text='0%',
            size_hint_y=0.4,
            font_size='14sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        progress_layout.add_widget(self.percent_label)

        main_layout.add_widget(progress_layout)

        main_layout.add_widget(Label(size_hint_y=0.1))

        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=0.18, spacing=10)

        self.download_btn = Button(
            text='Download',
            background_color=(0.2, 0.7, 0.3, 1),
            background_normal='',
            font_size='18sp',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.download_btn.bind(on_press=self.start_download)
        buttons_layout.add_widget(self.download_btn)

        self.cancel_btn = Button(
            text='Cancel',
            background_color=(0.5, 0.5, 0.5, 1),
            background_normal='',
            font_size='18sp',
            bold=True,
            disabled=True,
            color=(1, 1, 1, 1)
        )
        self.cancel_btn.bind(on_press=self.cancel_download)
        buttons_layout.add_widget(self.cancel_btn)

        main_layout.add_widget(buttons_layout)

        main_layout.add_widget(Label(size_hint_y=0.08))

        return main_layout

    def request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission, check_permission

            permissions = [
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET
            ]

            for perm in permissions:
                if not check_permission(perm):
                    request_permissions(permissions)
                    break

        except Exception as e:
            print(f"Permission error: {e}")

    def get_download_path(self):
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                download_path = os.path.join(
                    primary_external_storage_path(),
                    'Download'
                )
            except:
                possible_paths = [
                    '/storage/emulated/0/Download',
                    '/sdcard/Download',
                    '/mnt/sdcard/Download'
                ]
                download_path = None
                for path in possible_paths:
                    if os.path.exists(os.path.dirname(path)):
                        download_path = path
                        break

                if not download_path:
                    download_path = '/sdcard/Download'
        else:
            download_path = os.path.join(os.path.expanduser('~'), 'Downloads')

        try:
            if not os.path.exists(download_path):
                os.makedirs(download_path)
        except Exception as e:
            print(f"Folder creation error: {e}")
            download_path = os.getcwd()

        return download_path

    def detect_platform(self, url):
        url = url.lower()
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url or 'instagr.am' in url:
            return 'instagram'
        else:
            return 'unknown'

    def progress_hook(self, d):
        if not self.is_downloading:
            raise Exception("Download cancelled")

        if d['status'] == 'downloading':
            try:
                percent = 0
                speed_str = ''

                if 'total_bytes' in d and d['total_bytes'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100

                if '_speed_str' in d:
                    speed_str = d.get('_speed_str', '')

                if 'filename' in d:
                    self.current_file = d['filename']

                Clock.schedule_once(
                    lambda dt: self.update_progress(percent, speed_str), 0
                )

            except Exception as e:
                print(f"Progress calculation error: {e}")

        elif d['status'] == 'finished':
            Clock.schedule_once(lambda dt: self.download_finished(), 0)

    def update_progress(self, percent, speed):
        try:
            self.progress_bar.value = min(percent, 100)
            if speed:
                self.percent_label.text = f'{percent:.1f}% - {speed}'
            else:
                self.percent_label.text = f'{percent:.1f}%'
        except Exception as e:
            print(f"UI update error: {e}")

    def download_finished(self):
        self.status_label.text = 'Download completed successfully!'
        self.progress_bar.value = 100
        self.percent_label.text = '100%'
        self.reset_ui()

    def start_download(self, instance):
        url = self.url_input.text.strip()

        if not url:
            self.status_label.text = 'Please enter a link'
            return

        platform_type = self.detect_platform(url)

        if platform_type == 'unknown':
            self.status_label.text = 'Only YouTube and Instagram links!'
            return

        self.is_downloading = True
        self.download_btn.disabled = True
        self.download_btn.background_color = (0.5, 0.5, 0.5, 1)
        self.cancel_btn.disabled = False
        self.cancel_btn.background_color = (0.9, 0.2, 0.2, 1)
        self.url_input.disabled = True
        self.progress_bar.value = 0
        self.percent_label.text = '0%'
        self.status_label.text = f'Downloading from {platform_type}...'

        self.download_thread = threading.Thread(
            target=self.download_video,
            args=(url, platform_type),
            daemon=True
        )
        self.download_thread.start()

    def download_video(self, url, platform_type):
        try:
            import yt_dlp
        except ImportError:
            Clock.schedule_once(
                lambda dt: setattr(
                    self.status_label, 'text',
                    'Error: yt-dlp module not installed'
                ), 0
            )
            Clock.schedule_once(lambda dt: self.reset_ui(), 0)
            return

        download_path = self.get_download_path()
        self.download_path = download_path

        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
            }

            if platform_type == 'instagram':
                ydl_opts['format'] = 'best'
                ydl_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.current_file = ydl.prepare_filename(info)
                ydl.download([url])

        except Exception as e:
            error_msg = str(e)
            if "Download cancelled" not in error_msg:
                Clock.schedule_once(
                    lambda dt: setattr(
                        self.status_label, 'text',
                        'Download error occurred'
                    ), 0
                )
                print(f"Error: {error_msg}")
            Clock.schedule_once(lambda dt: self.reset_ui(), 0)

    def cancel_download(self, instance):
        self.is_downloading = False
        self.status_label.text = 'Cancelling download...'
        Clock.schedule_once(lambda dt: self.cleanup_files(), 0.5)

    def cleanup_files(self):
        try:
            if self.current_file:
                if os.path.exists(self.current_file):
                    os.remove(self.current_file)
                    print(f"File deleted: {self.current_file}")

                temp_extensions = ['.part', '.ytdl', '.temp', '.download']
                for ext in temp_extensions:
                    temp_file = self.current_file + ext
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"Temp file deleted: {temp_file}")

                if self.download_path and os.path.exists(self.download_path):
                    for file in os.listdir(self.download_path):
                        if any(file.endswith(ext) for ext in temp_extensions):
                            try:
                                os.remove(os.path.join(self.download_path, file))
                            except:
                                pass

            self.status_label.text = 'Download cancelled and incomplete file deleted'
        except Exception as e:
            print(f"File deletion error: {e}")
            self.status_label.text = 'Download cancelled'

        self.reset_ui()

    def reset_ui(self):
        self.is_downloading = False
        self.download_btn.disabled = False
        self.download_btn.background_color = (0.2, 0.7, 0.3, 1)
        self.cancel_btn.disabled = True
        self.cancel_btn.background_color = (0.5, 0.5, 0.5, 1)
        self.url_input.disabled = False
        self.current_file = None


if __name__ == '__main__':
    try:
        DownloaderApp().run()
    except Exception as e:
        print(f"Main error: {e}")
        import traceback
        traceback.print_exc()
