import os
import json
import threading
import time
import calendar
from datetime import datetime, timedelta

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, BooleanProperty, StringProperty

from plyer import notification


KV = """
<ReminderItem>:
    orientation: "horizontal"
    size_hint_y: None
    height: "60dp"
    padding: "5dp"
    spacing: "5dp"
    canvas.before:
        Color:
            rgba: (0.2, 0.2, 0.2, 0.15)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8, ]

    CheckBox:
        size_hint_x: None
        width: "40dp"
        active: root.enabled
        on_active: root.on_toggle_active(self.active)

    Label:
        text: root.summary
        halign: "left"
        valign: "middle"
        text_size: self.size

    Button:
        text: "Delete"
        size_hint_x: None
        width: "70dp"
        on_release: root.on_delete()


<RootWidget>:
    orientation: "vertical"
    padding: "10dp"
    spacing: "10dp"

    # Top form
    BoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: self.minimum_height
        spacing: "8dp"

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            Label:
                text: "Reminder message:"
                size_hint_x: 0.35
            TextInput:
                id: message_input
                multiline: False

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            Label:
                text: "Calendar:"
                size_hint_x: 0.35
            Spinner:
                id: calendar_spinner
                text: "Gregorian"
                values: ["Gregorian", "Jalali"]

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            Label:
                text: "Repeat type:"
                size_hint_x: 0.35
            Spinner:
                id: repeat_spinner
                text: "Once"
                values: ["Once", "Daily", "Weekly", "Monthly"]

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            Label:
                text: "Year:"
                size_hint_x: 0.25
            Spinner:
                id: year_spinner
                text: ""
                values: []
                size_hint_x: 0.25
            Label:
                text: "Month:"
                size_hint_x: 0.25
            Spinner:
                id: month_spinner
                text: ""
                values: []
                size_hint_x: 0.25

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            Label:
                text: "Day:"
                size_hint_x: 0.25
            Spinner:
                id: day_spinner
                text: ""
                values: []
                size_hint_x: 0.25
            Label:
                text: "Hour (0-23):"
                size_hint_x: 0.25
            TextInput:
                id: hour_input
                multiline: False
                input_filter: "int"
                size_hint_x: 0.25

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            Label:
                text: "Minute (0-59):"
                size_hint_x: 0.35
            TextInput:
                id: minute_input
                multiline: False
                input_filter: "int"
                size_hint_x: 0.25
            Label:
                text: "Sound path (optional):"
                size_hint_x: 0.35

        TextInput:
            id: sound_input
            multiline: False
            size_hint_y: None
            height: "40dp"

        Button:
            text: "Add reminder"
            size_hint_y: None
            height: "50dp"
            on_release: root.add_reminder()

        Label:
            id: status_label
            size_hint_y: None
            height: "30dp"
            text: ""
            color: (1, 0, 0, 1)

    Label:
        text: "Reminders:"
        size_hint_y: None
        height: "30dp"

    ScrollView:
        id: reminders_scroll
        size_hint_y: 1
        do_scroll_x: False

        BoxLayout:
            id: reminders_container
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            spacing: "5dp"
            padding: 0, 0, 0, 10
"""


class ReminderItem(BoxLayout):
    reminder_id = NumericProperty(0)
    enabled = BooleanProperty(True)
    summary = StringProperty("")

    def on_toggle_active(self, active):
        app = App.get_running_app()
        try:
            app.reminder_manager.set_enabled(self.reminder_id, active)
        except Exception as exc:
            print("Error updating enabled state:", exc)

    def on_delete(self):
        app = App.get_running_app()
        try:
            app.reminder_manager.delete_reminder(self.reminder_id)
        except Exception as exc:
            print("Error deleting reminder:", exc)
        # Remove widget from UI
        if self.parent:
            self.parent.remove_widget(self)


class RootWidget(BoxLayout):
    def on_kv_post(self, base_widget):
        """Called after kv language is applied."""
        self._setup_date_spinners()
        # Make sure scroll is at top
        self.ids.reminders_scroll.scroll_y = 1

    def _setup_date_spinners(self):
        now = datetime.now()
        years = [str(y) for y in range(now.year, now.year + 5)]
        months = [f"{m:02d}" for m in range(1, 13)]
        days = [f"{d:02d}" for d in range(1, 32)]

        self.ids.year_spinner.values = years
        self.ids.year_spinner.text = str(now.year)

        self.ids.month_spinner.values = months
        self.ids.month_spinner.text = f"{now.month:02d}"

        self.ids.day_spinner.values = days
        self.ids.day_spinner.text = f"{now.day:02d}"

    def init_ui(self, manager):
        """Called from App.on_start with the ReminderManager."""
        # Load existing reminders into the scroll list
        reminders = list(manager.reminders)
        # Sort by next_run if exists
        def sort_key(r):
            return r.get("next_run", "") or ""
        reminders.sort(key=sort_key)
        container = self.ids.reminders_container
        container.clear_widgets()
        for r in reminders:
            self.add_reminder_widget(r)

    def format_reminder_summary(self, reminder):
        message = reminder.get("message", "")
        calendar_type = reminder.get("calendar", "gregorian").capitalize()
        repeat = reminder.get("repeat", "once").capitalize()

        year = int(reminder.get("year", 0) or 0)
        month = int(reminder.get("month", 0) or 0)
        day = int(reminder.get("day", 0) or 0)
        hour = int(reminder.get("hour", 0) or 0)
        minute = int(reminder.get("minute", 0) or 0)

        state = "ON" if reminder.get("enabled", True) else "OFF"

        date_part = f"{year:04d}-{month:02d}-{day:02d}"
        time_part = f"{hour:02d}:{minute:02d}"

        base = f"{message} | {calendar_type} {date_part} {time_part} | {repeat}"
        return f"[{state}] {base}"

    def add_reminder_widget(self, reminder):
        summary_text = self.format_reminder_summary(reminder)
        item = ReminderItem(
            reminder_id=reminder.get("id", 0),
            enabled=reminder.get("enabled", True),
            summary=summary_text,
        )
        # Add to top of the list
        self.ids.reminders_container.add_widget(item, index=0)

    def set_reminder_enabled(self, reminder_id, enabled):
        container = self.ids.reminders_container
        for child in container.children:
            if isinstance(child, ReminderItem) and child.reminder_id == reminder_id:
                child.enabled = enabled
                # Also refresh summary text to update [ON]/[OFF]
                app = App.get_running_app()
                for r in app.reminder_manager.reminders:
                    if r.get("id") == reminder_id:
                        child.summary = self.format_reminder_summary(r)
                        break
                break

    def add_reminder(self):
        app = App.get_running_app()
        message = self.ids.message_input.text.strip()
        repeat = self.ids.repeat_spinner.text.strip().lower()  # once/daily/weekly/monthly
        calendar_type = self.ids.calendar_spinner.text.strip().lower()  # gregorian/jalali
        year_text = self.ids.year_spinner.text.strip()
        month_text = self.ids.month_spinner.text.strip()
        day_text = self.ids.day_spinner.text.strip()
        hour_text = self.ids.hour_input.text.strip()
        minute_text = self.ids.minute_input.text.strip()
        sound_path = self.ids.sound_input.text.strip()

        if not message:
            self.ids.status_label.text = "Please enter a message."
            return

        if not (year_text and month_text and day_text):
            self.ids.status_label.text = "Please select year, month and day."
            return

        if not hour_text or not minute_text:
            self.ids.status_label.text = "Please enter hour and minute."
            return

        try:
            year = int(year_text)
            month = int(month_text)
            day = int(day_text)
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError:
            self.ids.status_label.text = "Invalid date/time format."
            return

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            self.ids.status_label.text = "Hour/minute out of range."
            return

        # Validate Gregorian date if calendar is Gregorian
        if calendar_type == "gregorian":
            try:
                datetime(year, month, day)
            except ValueError:
                self.ids.status_label.text = "Invalid Gregorian date."
                return

        try:
            reminder = app.reminder_manager.add_reminder(
                message=message,
                repeat=repeat,
                calendar_type=calendar_type,
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                sound_path=sound_path,
            )
        except ValueError as exc:
            self.ids.status_label.text = f"Error: {exc}"
            return
        except Exception as exc:
            self.ids.status_label.text = f"Unexpected error: {exc}"
            return

        # Add to UI list
        self.add_reminder_widget(reminder)

        self.ids.status_label.text = "Reminder saved."

    # Optionally you can add a method to refresh the list entirely
    def refresh_list_from_manager(self, manager):
        reminders = list(manager.reminders)
        def sort_key(r):
            return r.get("next_run", "") or ""
        reminders.sort(key=sort_key)
        container = self.ids.reminders_container
        container.clear_widgets()
        for r in reminders:
            self.add_reminder_widget(r)


class ReminderManager:
    def __init__(self, data_file_path):
        self.data_file_path = data_file_path
        self.reminders = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.data_file_path):
            try:
                with open(self.data_file_path, "r", encoding="utf-8") as f:
                    self.reminders = json.load(f)
            except Exception:
                self.reminders = []
        else:
            self.reminders = []

        # Ensure "enabled" field exists
        for r in self.reminders:
            if "enabled" not in r:
                r["enabled"] = True

    def _save(self):
        tmp_path = self.data_file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.data_file_path)

    @staticmethod
    def _add_months(dt, months):
        month = dt.month - 1 + months
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    def _advance_from(self, dt, repeat, now):
        while dt <= now:
            if repeat == "daily":
                dt += timedelta(days=1)
            elif repeat == "weekly":
                dt += timedelta(weeks=1)
            elif repeat == "monthly":
                dt = self._add_months(dt, 1)
            else:
                break
        return dt

    def add_reminder(
        self,
        message,
        repeat,
        calendar_type,
        year,
        month,
        day,
        hour,
        minute,
        sound_path,
    ):
        repeat = repeat.lower()
        calendar_type = calendar_type.lower()

        if repeat not in ("once", "daily", "weekly", "monthly"):
            raise ValueError("Invalid repeat type.")
        if calendar_type not in ("gregorian", "jalali"):
            raise ValueError("Invalid calendar type.")

        # For simplicity, we treat the date as Gregorian datetime internally.
        # If you really need Jalali logic, you must convert it using a Jalali library.
        base_dt = datetime(year, month, day, hour, minute, 0)
        now = datetime.now()

        if repeat == "once":
            if base_dt <= now:
                raise ValueError("Selected date/time is in the past for 'Once' reminder.")
            next_run = base_dt
        else:
            # Repeating reminder: schedule next_run in the future
            if base_dt <= now:
                next_run = self._advance_from(base_dt, repeat, now)
            else:
                next_run = base_dt

        with self._lock:
            new_id = max((r.get("id", 0) for r in self.reminders), default=0) + 1
            reminder = {
                "id": new_id,
                "message": message,
                "repeat": repeat,
                "calendar": calendar_type,
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": minute,
                "sound_path": sound_path,
                "enabled": True,
                "next_run": next_run.isoformat(timespec="seconds"),
            }
            self.reminders.append(reminder)
            self._save()
            return reminder

    def _advance_next_run(self, reminder, now=None):
        if now is None:
            now = datetime.now()
        repeat = reminder.get("repeat", "once")
        try:
            next_run = datetime.fromisoformat(reminder["next_run"])
        except Exception:
            next_run = now

        if repeat == "once":
            # Do not schedule again for one-time reminders
            reminder["enabled"] = False
            return

        next_run = self._advance_from(next_run, repeat, now)
        reminder["next_run"] = next_run.isoformat(timespec="seconds")

    def get_due_reminders(self):
        now = datetime.now()
        due = []
        with self._lock:
            for reminder in self.reminders:
                if not reminder.get("enabled", True):
                    continue
                try:
                    next_run = datetime.fromisoformat(reminder["next_run"])
                except Exception:
                    next_run = now
                if next_run <= now:
                    due.append(reminder.copy())
                    self._advance_next_run(reminder, now=now)
            if due:
                self._save()
        return due

    def set_enabled(self, reminder_id, enabled):
        with self._lock:
            for r in self.reminders:
                if r.get("id") == reminder_id:
                    r["enabled"] = bool(enabled)
                    self._save()
                    break

    def delete_reminder(self, reminder_id):
        with self._lock:
            self.reminders = [r for r in self.reminders if r.get("id") != reminder_id]
            self._save()


class ReminderScheduler(threading.Thread):
    def __init__(self, manager, callback, interval_seconds=30):
        super().__init__(daemon=True)
        self.manager = manager
        self.callback = callback
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            due_reminders = self.manager.get_due_reminders()
            if due_reminders:
                for reminder in due_reminders:
                    self.callback(reminder)
            total = 0
            while total < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(1)
                total += 1

    def stop(self):
        self._stop_event.set()


class ReminderApp(App):
    def build(self):
        self.title = "Kivy Reminder"
        Builder.load_string(KV)
        self.reminder_manager = None
        self.scheduler = None
        return RootWidget()

    def on_start(self):
        data_dir = self.user_data_dir
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, "reminders.json")

        self.reminder_manager = ReminderManager(data_path)

        # Initialize UI list from saved reminders
        self.root.init_ui(self.reminder_manager)

        # Start background scheduler
        self.scheduler = ReminderScheduler(
            manager=self.reminder_manager,
            callback=self.on_reminder_due,
            interval_seconds=30,
        )
        self.scheduler.start()

    def on_stop(self):
        if self.scheduler is not None:
            self.scheduler.stop()

    def on_reminder_due(self, reminder):
        # Run on main thread
        Clock.schedule_once(lambda dt: self._handle_due_on_main(reminder))

    def _handle_due_on_main(self, reminder):
        self._show_notification_and_sound(reminder)
        # If it was a one-time reminder, it has been disabled in the manager;
        # update UI checkbox state as well.
        if reminder.get("repeat", "once") == "once":
            try:
                self.root.set_reminder_enabled(reminder["id"], False)
            except Exception as exc:
                print("Error updating UI after one-time reminder:", exc)

    def _show_notification_and_sound(self, reminder):
        message = reminder.get("message", "")
        sound_path = (reminder.get("sound_path") or "").strip()

        try:
            notification.notify(
                title="Reminder",
                message=message,
                timeout=10,
            )
        except Exception as exc:
            print("Notification error:", exc)

        if sound_path:
            try:
                sound = SoundLoader.load(sound_path)
                if sound:
                    sound.play()
            except Exception as exc:
                print("Sound error:", exc)


if __name__ == "__main__":
    ReminderApp().run()
