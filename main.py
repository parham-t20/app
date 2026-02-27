from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform
import threading
import os
import re

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    request_permissions([
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE,
        Permission.INTERNET
    ])

try:
    import yt_dlp
except:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp


class DownloaderApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.download_thread = None
        self.is_downloading = False
        self.current_file = None
        self.ydl = None
        
    def build(self):
        self.title = "دانلودر یوتوب و اینستاگرام"
        
        # Layout اصلی
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # عنوان
        title_label = Label(
            text='دانلودر یوتوب و اینستاگرام',
            size_hint_y=0.1,
            font_size='20sp',
            bold=True
        )
        main_layout.add_widget(title_label)
        
        # ورودی URL
        self.url_input = TextInput(
            hint_text='لینک یوتوب یا اینستاگرام را وارد کنید',
            multiline=False,
            size_hint_y=0.1,
            font_size='16sp'
        )
        main_layout.add_widget(self.url_input)
        
        # برچسب وضعیت
        self.status_label = Label(
            text='آماده دانلود',
            size_hint_y=0.1,
            font_size='14sp'
        )
        main_layout.add_widget(self.status_label)
        
        # نوار پیشرفت
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=0.1
        )
        main_layout.add_widget(self.progress_bar)
        
        # برچسب درصد
        self.percent_label = Label(
            text='0%',
            size_hint_y=0.08,
            font_size='14sp'
        )
        main_layout.add_widget(self.percent_label)
        
        # دکمه‌های کنترل
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15, spacing=10)
        
        self.download_btn = Button(
            text='شروع دانلود',
            background_color=(0.2, 0.6, 0.2, 1),
            font_size='18sp',
            bold=True
        )
        self.download_btn.bind(on_press=self.start_download)
        buttons_layout.add_widget(self.download_btn)
        
        self.cancel_btn = Button(
            text='لغو دانلود',
            background_color=(0.8, 0.2, 0.2, 1),
            font_size='18sp',
            bold=True,
            disabled=True
        )
        self.cancel_btn.bind(on_press=self.cancel_download)
        buttons_layout.add_widget(self.cancel_btn)
        
        main_layout.add_widget(buttons_layout)
        
        return main_layout
    
    def get_download_path(self):
        """مسیر پوشه دانلود را برمی‌گرداند"""
        if platform == 'android':
            try:
                download_path = os.path.join(
                    primary_external_storage_path(),
                    'Download'
                )
            except:
                download_path = '/sdcard/Download'
        else:
            download_path = os.path.expanduser('~/Downloads')
        
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        return download_path
    
    def detect_platform(self, url):
        """تشخیص نوع پلتفرم از URL"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url:
            return 'instagram'
        else:
            return 'unknown'
    
    def progress_hook(self, d):
        """به‌روزرسانی نوار پیشرفت"""
        if not self.is_downloading:
            raise Exception("دانلود لغو شد")
            
        if d['status'] == 'downloading':
            try:
                # محاسبه درصد پیشرفت
                if 'total_bytes' in d:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                elif 'total_bytes_estimate' in d:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                else:
                    percent = 0
                
                # ذخیره نام فایل در حال دانلود
                if 'filename' in d:
                    self.current_file = d['filename']
                
                # به‌روزرسانی UI
                Clock.schedule_once(lambda dt: self.update_progress(percent, d.get('_speed_str', '')))
                
            except Exception as e:
                print(f"خطا در محاسبه پیشرفت: {e}")
        
        elif d['status'] == 'finished':
            Clock.schedule_once(lambda dt: self.download_finished())
    
    def update_progress(self, percent, speed):
        """به‌روزرسانی نوار پیشرفت و برچسب‌ها"""
        self.progress_bar.value = percent
        self.percent_label.text = f'{percent:.1f}% - {speed}'
    
    def download_finished(self):
        """اقدامات پس از اتمام دانلود"""
        self.status_label.text = 'دانلود با موفقیت انجام شد!'
        self.progress_bar.value = 100
        self.percent_label.text = '100%'
        self.reset_ui()
    
    def start_download(self, instance):
        """شروع دانلود"""
        url = self.url_input.text.strip()
        
        if not url:
            self.status_label.text = 'لطفاً لینک را وارد کنید'
            return
        
        platform_type = self.detect_platform(url)
        
        if platform_type == 'unknown':
            self.status_label.text = 'لینک نامعتبر! فقط یوتوب و اینستاگرام'
            return
        
        # تنظیم UI
        self.is_downloading = True
        self.download_btn.disabled = True
        self.cancel_btn.disabled = False
        self.url_input.disabled = True
        self.progress_bar.value = 0
        self.status_label.text = f'در حال دانلود از {platform_type}...'
        
        # شروع دانلود در thread جداگانه
        self.download_thread = threading.Thread(
            target=self.download_video,
            args=(url, platform_type)
        )
        self.download_thread.start()
    
    def download_video(self, url, platform_type):
        """دانلود ویدیو"""
        download_path = self.get_download_path()
        
        try:
            # تنظیمات yt-dlp
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': False,
                'no_warnings': False,
            }
            
            # تنظیمات خاص اینستاگرام
            if platform_type == 'instagram':
                ydl_opts['format'] = 'best'
            
            # شروع دانلود
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.ydl = ydl
                ydl.download([url])
                
        except Exception as e:
            error_msg = str(e)
            if "دانلود لغو شد" not in error_msg:
                Clock.schedule_once(
                    lambda dt: setattr(self.status_label, 'text', f'خطا: {error_msg}')
                )
            Clock.schedule_once(lambda dt: self.reset_ui())
    
    def cancel_download(self, instance):
        """لغو دانلود و حذف فایل ناقص"""
        self.is_downloading = False
        self.status_label.text = 'در حال لغو دانلود...'
        
        # حذف فایل ناقص
        if self.current_file and os.path.exists(self.current_file):
            try:
                os.remove(self.current_file)
                # حذف فایل‌های موقت
                if os.path.exists(self.current_file + '.part'):
                    os.remove(self.current_file + '.part')
            except Exception as e:
                print(f"خطا در حذف فایل: {e}")
        
        self.status_label.text = 'دانلود لغو شد و فایل ناقص حذف شد'
        self.reset_ui()
    
    def reset_ui(self):
        """بازنشانی رابط کاربری"""
        self.is_downloading = False
        self.download_btn.disabled = False
        self.cancel_btn.disabled = True
        self.url_input.disabled = False
        self.current_file = None


if __name__ == '__main__':
    DownloaderApp().run()
