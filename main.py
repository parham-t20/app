# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import datetime

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.resources import resource_find
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarIconListItem, IconRightWidget
from kivymd.uix.picker import MDDatePicker, MDTimePicker
from kivymd.uix.snackbar import Snackbar

try:
    from plyer import filechooser
except Exception:
    filechooser = None

# فایل‌ها و تنظیمات
REMINDERS_FILE = 'reminders.json'
TRIGGERED_FILE = 'triggered.json'
DEFAULT_SOUND = 'alarm.mp3'

KV = '''
Screen:
    MDBoxLayout:
        orientation: 'vertical'

        MDToolbar:
            title: "برنامه یادآوری حرفه‌ای"
            elevation: 6

        ScrollView:
            MDBoxLayout:
                id: root_box
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(14)
                size_hint_y: None
                height: self.minimum_height

                MDTextField:
                    id: desc
                    hint_text: "توضیحات"
                    helper_text: "یادآوری خود را اینجا بنویسید..."
                    helper_text_mode: "on_focus"
                    halign: "right"

                MDBoxLayout:
                    spacing: dp(10)
                    size_hint_y: None
                    height: self.minimum_height

                    MDTextField:
                        id: date_field
                        hint_text: "تاریخ (YYYY-MM-DD)"
                        readonly: True
                        halign: "center"
                        on_focus: app.open_date_picker() if self.focus else None

                    MDTextField:
                        id: time_field
                        hint_text: "ساعت (HH:MM)"
                        readonly: True
                        halign: "center"
                        on_focus: app.open_time_picker() if self.focus else None

                    MDBoxLayout:
                        size_hint_x: None
                        width: dp(110)
                        MDFlatButton:
                            id: weekday_label
                            text: ""
                            theme_text_color: "Custom"
                            text_color: app.theme_cls.primary_color

                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(10)

                    MDRaisedButton:
                        text: "انتخاب فایل زنگ"
                        on_release: app.choose_sound_file()

                    MDFlatButton:
                        id: sound_label
                        text: app.sound_file or "alarm.mp3"
                        theme_text_color: "Custom"
                        text_color: .1, .3, .9, 1

                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(12)

                    MDRaisedButton:
                        text: "ثبت یادآوری"
                        on_release: app.add_or_edit_reminder()

                    MDFlatButton:
                        text: "پاک کردن فرم"
                        on_release: app.clear_form()

                MDFlatButton:
                    text: "لیست یادآوری‌های فعال"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    halign: "right"

                MDList:
                    id: reminder_list
'''

# -------------------------------
# ابزارهای مشترک (اپ و سرویس)
# -------------------------------

def get_data_dir():
    if platform == 'android':
        try:
            from jnius import autoclass
            # در اپ:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            return PythonActivity.mActivity.getFilesDir().getAbsolutePath()
        except Exception:
            try:
                # در سرویس:
                PythonService = autoclass('org.kivy.android.PythonService')
                return PythonService.mService.getFilesDir().getAbsolutePath()
            except Exception:
                pass
    d = os.path.join(os.getcwd(), 'appdata')
    os.makedirs(d, exist_ok=True)
    return d

def reminders_path():
    return os.path.join(get_data_dir(), REMINDERS_FILE)

def triggered_path():
    return os.path.join(get_data_dir(), TRIGGERED_FILE)

def ensure_files():
    for p in (reminders_path(), triggered_path()):
        if not os.path.exists(p):
            with open(p, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_reminders():
    return load_json(reminders_path())

def save_reminders(reminders):
    save_json(reminders_path(), reminders)

def load_triggered():
    return load_json(triggered_path())

def save_triggered(items):
    save_json(triggered_path(), items)

def is_service_process():
    # اگر به عنوان سرویس اجرا شده باشد، معمولاً این متغیر ست می‌شود
    if os.environ.get('PYTHON_SERVICE_ARGUMENT') is not None:
        return True
    # به صورت کمکی اگر با آرگومان خاصی استارت شده باشد
    return any(a.lower() == 'service' or a.lower().startswith('--service') for a in sys.argv)

# -------------------------------
# اپ اصلی KivyMD
# -------------------------------

class ReminderApp(MDApp):
    persian_weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]

    def build(self):
        self.title = "برنامه یادآوری حرفه‌ای"
        self.editing_id = None
        self.sound_file = DEFAULT_SOUND
        self.is_showing_popup = False
        self.current_sound_obj = None
        self.dialog_delete = None
        return Builder.load_string(KV)

    def on_start(self):
        ensure_files()
        self.set_default_datetime()
        self.populate_list()
        self.start_bg_service()
        self.ask_notification_permission_android13()
        Clock.schedule_interval(self.check_triggered_for_popup, 1.0)

    def set_default_datetime(self):
        now = datetime.datetime.now()
        self.root.ids.date_field.text = now.strftime('%Y-%m-%d')
        self.root.ids.time_field.text = now.strftime('%H:%M')
        self.update_weekday_label()

    def update_weekday_label(self):
        try:
            date_str = self.root.ids.date_field.text.strip()
            dt_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            idx = dt_obj.weekday()
            name = self.persian_weekdays[idx]
            self.root.ids.weekday_label.text = f"({name})"
        except Exception:
            self.root.ids.weekday_label.text = ""

    def open_date_picker(self):
        try:
            current = datetime.datetime.strptime(self.root.ids.date_field.text.strip(), '%Y-%m-%d').date()
        except Exception:
            current = datetime.date.today()
        picker = MDDatePicker(year=current.year, month=current.month, day=current.day)
        picker.bind(on_save=self._on_date_save)
        picker.open()

    def _on_date_save(self, instance, value, date_range):
        self.root.ids.date_field.text = value.strftime('%Y-%m-%d')
        self.update_weekday_label()

    def open_time_picker(self):
        picker = MDTimePicker()
        picker.bind(time=self._on_time_save)
        picker.open()

    def _on_time_save(self, instance, time_value):
        self.root.ids.time_field.text = time_value.strftime('%H:%M')

    def choose_sound_file(self):
        if not filechooser:
            Snackbar(text="Filechooser در این محیط فعال نیست.").open()
            return
        try:
            filechooser.open_file(filters=[("Audio", "*.mp3")], on_selection=self._on_sound_chosen)
        except Exception:
            filechooser.open_file(on_selection=self._on_sound_chosen)

    def _on_sound_chosen(self, selection):
        if selection:
            self.sound_file = selection[0]
            self.root.ids.sound_label.text = self.sound_file

    def add_or_edit_reminder(self):
        desc = self.root.ids.desc.text.strip()
        date_str = self.root.ids.date_field.text.strip()
        time_str = self.root.ids.time_field.text.strip()

        if not desc:
            Snackbar(text="لطفاً توضیحات را وارد کنید.").open()
            return
        if not date_str or not time_str:
            Snackbar(text="لطفاً تاریخ و ساعت را مشخص کنید.").open()
            return

        # بررسی/ثبت فایل زنگ
        sound_to_save = self.sound_file or DEFAULT_SOUND
        if sound_to_save == DEFAULT_SOUND:
            default_res = resource_find(DEFAULT_SOUND) or os.path.join(os.getcwd(), DEFAULT_SOUND)
            if os.path.exists(default_res):
                sound_to_save = default_res
            else:
                sound_to_save = ""  # بدون صدا

        try:
            dt_obj = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            Snackbar(text="فرمت تاریخ/ساعت نامعتبر است.").open()
            return

        reminders = load_reminders()
        item = {"description": desc, "datetime_str": dt_obj.isoformat(), "sound": sound_to_save}

        if self.editing_id:
            for r in reminders:
                if r.get('id') == self.editing_id:
                    r.update(item)
                    break
            Snackbar(text="یادآوری با موفقیت ویرایش شد.").open()
        else:
            item["id"] = int(time.time() * 1000)
            reminders.append(item)
            Snackbar(text="یادآوری با موفقیت اضافه شد.").open()

        save_reminders(reminders)
        self.populate_list()
        self.clear_form()

    def populate_list(self, *_):
        lst = self.root.ids.reminder_list
        lst.clear_widgets()
        reminders = load_reminders()
        reminders.sort(key=lambda r: r['datetime_str'])
        for r in reminders:
            dt_obj = datetime.datetime.fromisoformat(r['datetime_str'])
            txt = f"{r['description']} - [{dt_obj.strftime('%Y-%m-%d %H:%M')}]"
            item = OneLineAvatarIconListItem(text=txt)
            item._rid = r['id']
            delete_icon = IconRightWidget(icon="delete", on_release=lambda w, rid=r['id']: self.confirm_delete(rid))
            item.add_widget(delete_icon)
            item.bind(on_release=lambda it, rid=r['id']: self.load_for_edit(rid))
            lst.add_widget(item)

    def load_for_edit(self, rid):
        reminders = load_reminders()
        rem = next((x for x in reminders if x['id'] == rid), None)
        if not rem:
            return
        dt_obj = datetime.datetime.fromisoformat(rem['datetime_str'])
        self.root.ids.desc.text = rem['description']
        self.root.ids.date_field.text = dt_obj.strftime('%Y-%m-%d')
        self.root.ids.time_field.text = dt_obj.strftime('%H:%M')
        self.sound_file = rem.get('sound') or DEFAULT_SOUND
        self.root.ids.sound_label.text = self.sound_file
        self.editing_id = rid
        self.update_weekday_label()
        Snackbar(text="حالت ویرایش فعال شد. پس از تغییر، روی «ثبت یادآوری» بزنید.").open()

    def confirm_delete(self, rid):
        def do_delete(*_):
            reminders = load_reminders()
            reminders = [r for r in reminders if r['id'] != rid]
            save_reminders(reminders)
            self.populate_list()
            if self.dialog_delete:
                self.dialog_delete.dismiss()
            Snackbar(text="یادآوری حذف شد.").open()

        self.dialog_delete = MDDialog(
            title="تایید حذف",
            text="آیا از حذف این یادآوری مطمئن هستید؟",
            buttons=[
                MDFlatButton(text="لغو", on_release=lambda *_: self.dialog_delete.dismiss()),
                MDRaisedButton(text="حذف", on_release=do_delete)
            ]
        )
        self.dialog_delete.open()

    def clear_form(self):
        self.root.ids.desc.text = ""
        self.set_default_datetime()
        self.sound_file = DEFAULT_SOUND
        self.root.ids.sound_label.text = self.sound_file
        self.editing_id = None

    # نشان دادن پاپ‌آپ‌های ایجادشده توسط سرویس
    def check_triggered_for_popup(self, *_):
        if self.is_showing_popup:
            return
        # لیست را همزمان به‌روز کنیم تا حذف‌های سرویس منعکس شود
        self.populate_list()

        pending = load_triggered()
        candidates = [x for x in pending if not x.get('shown_in_app')]
        if not candidates:
            return
        item = candidates[0]
        # علامت‌گذاری به عنوان نمایش‌داده‌شده تا تکرار نشود
        for i in pending:
            if i.get('id') == item.get('id'):
                i['shown_in_app'] = True
                break
        save_triggered(pending)
        self.show_alarm_popup(item)

    def show_alarm_popup(self, reminder):
        self.is_showing_popup = True
        msg = f"یادآوری: {reminder.get('description','')}\n\n" \
              f"زمان تنظیم شده: {datetime.datetime.fromisoformat(reminder['datetime_str']).strftime('%Y-%m-%d %H:%M')}"
        # پخش صدا
        self.play_sound(reminder.get('sound'))
        btn_ok = MDRaisedButton(text="باشه، فهمیدم!", on_release=lambda *_: self._ack_and_close(reminder))
        self._dialog = MDDialog(title="🔔 وقت یادآوری! 🔔", text=msg, buttons=[btn_ok])
        self._dialog.open()

    def _ack_and_close(self, reminder):
        self.stop_sound()
        # حذف از triggered.json
        pending = load_triggered()
        pending = [x for x in pending if x.get('id') != reminder.get('id')]
        save_triggered(pending)
        if hasattr(self, "_dialog") and self._dialog:
            self._dialog.dismiss()
        self.is_showing_popup = False

    def play_sound(self, sound_path):
        if not sound_path:
            return
        path = sound_path
        if not os.path.exists(path):
            res = resource_find(os.path.basename(sound_path))
            if res:
                path = res
        try:
            snd = SoundLoader.load(path)
            if snd:
                snd.loop = True
                snd.play()
                self.current_sound_obj = snd
        except Exception:
            self.current_sound_obj = None

    def stop_sound(self):
        if self.current_sound_obj:
            try:
                self.current_sound_obj.stop()
            except Exception:
                pass
            self.current_sound_obj = None

    def start_bg_service(self):
        if platform != 'android':
            return
        # شروع سرویس (entrypoint همین main.py است؛ در buildozer.spec مشخص می‌کنیم)
        try:
            from android import AndroidService
            s = AndroidService('سرویس یادآوری', 'در حال اجرا...')
            # آرگومان صرفاً جهت تشخیص فرآیند سرویس
            s.start('service')
        except Exception:
            try:
                from jnius import autoclass
                PythonService = autoclass('org.kivy.android.PythonService')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                PythonService.start(PythonActivity.mActivity, "service")
            except Exception as e:
                print("Service start failed:", e)

    def ask_notification_permission_android13(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            Build = autoclass('android.os.Build')
            if Build.VERSION.SDK_INT < 33:
                return
            ActivityCompat = autoclass('androidx.core.app.ActivityCompat')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Manifest = autoclass('android.Manifest')
            PackageManager = autoclass('android.content.pm.PackageManager')
            activity = PythonActivity.mActivity
            permission = Manifest.permission.POST_NOTIFICATIONS
            if ActivityCompat.checkSelfPermission(activity, permission) != PackageManager.PERMISSION_GRANTED:
                arr = [permission]
                ActivityCompat.requestPermissions(activity, arr, 1001)
        except Exception:
            pass


# -------------------------------
# کد سرویس (در همین فایل)
# -------------------------------

def notify_android(title, message):
    """
    اعلان ساده با plyer. برای کانال پر اهمیت/لاک‌اسکرین قوی‌تر
    می‌توان NotificationChannel با jnius ساخت (در صورت نیاز اضافه کنید).
    """
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=10)
    except Exception as e:
        print("Notification error:", e)

def start_foreground_service():
    """
    تبدیل به Foreground داخل سرویس (جهت پایداری بیشتر).
    """
    try:
        from android import AndroidService
        service = AndroidService('سرویس یادآوری', 'در حال پایش یادآورها')
        service.start_foreground()
    except Exception as e:
        print("Foreground service error:", e)

def service_main_loop():
    ensure_files()
    # ارتقاء به Foreground
    start_foreground_service()

    while True:
        try:
            now = datetime.datetime.now()
            reminders = load_reminders()
            due = [r for r in reminders if datetime.datetime.fromisoformat(r['datetime_str']) <= now]
            if due:
                r = sorted(due, key=lambda x: x['datetime_str'])[0]
                dt_txt = datetime.datetime.fromisoformat(r['datetime_str']).strftime('%Y-%m-%d %H:%M')
                title = "🔔 وقت یادآوری"
                message = f"{r.get('description','')}\nزمان: {dt_txt}"
                notify_android(title, message)

                # ثبت برای نمایش پاپ‌آپ داخل اپ
                triggered = load_triggered()
                if not any(x.get('id') == r.get('id') for x in triggered):
                    r_copy = dict(r)
                    r_copy['shown_in_app'] = False
                    triggered.append(r_copy)
                    save_triggered(triggered)

                # حذف از reminders.json
                reminders = [x for x in reminders if x.get('id') != r.get('id')]
                save_reminders(reminders)

        except Exception as e:
            print("Service loop error:", e)

        time.sleep(5)  # هر ۵ ثانیه بررسی

# -------------------------------
# ورود برنامه
# -------------------------------

if __name__ == "__main__":
    if is_service_process():
        # اجرای این فایل به عنوان سرویس
        service_main_loop()
    else:
        # اجرای اپلیکیشن
        ReminderApp().run()
