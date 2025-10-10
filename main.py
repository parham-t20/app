from kivy.app import App
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout

# --- Android check ---
ANDROID = False
try:
    from jnius import autoclass, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission, check_permission
    ANDROID = True
except Exception:
    ANDROID = False

KV = '''
<RootWidget>:
    orientation: 'vertical'
    padding: 20
    spacing: 15

    Label:
        text: root.status_text
        size_hint_y: None
        height: '40dp'

    Label:
        text: "تعداد قدم‌ها: " + str(root.step_count)
        font_size: '26sp'

    Label:
        text: "سلامت: " + str(root.health_points)
        font_size: '30sp'
        bold: True

    BoxLayout:
        size_hint_y: None
        height: '48dp'
        spacing: 10

        Button:
            text: "شروع"
            on_release: root.start_listening()
        Button:
            text: "توقف"
            on_release: root.stop_listening()
        Button:
            text: "ریست"
            on_release: root.reset_data()

    Button:
        text: "شبیه‌سازی قدم (+1)"
        size_hint_y: None
        height: '48dp'
        on_release: root.simulate_step()

    Label:
        text: "هر قدم = +100 سلامت\nاطلاعات در حافظه ذخیره می‌شود."
        font_size: '13sp'
        halign: 'center'
        valign: 'middle'
        text_size: self.width, None
        size_hint_y: None
        height: '70dp'
'''


class RootWidget(BoxLayout):
    step_count = NumericProperty(0)
    health_points = NumericProperty(0)
    status_text = StringProperty("وضعیت: آماده")
    listening = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # محل ذخیره‌سازی محلی
        self.store = JsonStore("health_data.json")
        if self.store.exists("user"):
            data = self.store.get("user")
            self.step_count = data.get("steps", 0)
            self.health_points = data.get("health", 0)
        else:
            self._save_data()

        # آماده‌سازی اندروید
        self.sensor_manager = None
        self.step_listener = None
        if ANDROID:
            self._prepare_android()

    def _save_data(self):
        self.store.put("user", steps=self.step_count, health=self.health_points)

    def _add_health(self, steps=1):
        self.step_count += steps
        self.health_points += steps * 100
        self._save_data()
        self.status_text = f"قدم‌ها: {self.step_count} | سلامت: {self.health_points}"

    def simulate_step(self):
        self._add_health(1)

    def reset_data(self):
        self.step_count = 0
        self.health_points = 0
        self._save_data()
        self.status_text = "ریست شد."

    # ---------------- Android بخش ----------------
    def _prepare_android(self):
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            self.activity = PythonActivity.mActivity
            Context = autoclass('android.content.Context')
            self.SensorManager = autoclass('android.hardware.SensorManager')
            self.sensor_manager = self.activity.getSystemService(Context.SENSOR_SERVICE)
            self.Sensor = autoclass('android.hardware.Sensor')
        except Exception as e:
            self.status_text = f"خطا در آماده‌سازی: {e}"
            self.sensor_manager = None

    def start_listening(self):
        if ANDROID:
            self.status_text = "درخواست مجوز..."
            self._request_permissions_and_start()
        else:
            self.status_text = "در حالت تست: فقط شبیه‌سازی در دسترس است."

    def stop_listening(self):
        if ANDROID and self.sensor_manager and self.step_listener:
            self.sensor_manager.unregisterListener(self.step_listener)
            self.listening = False
            self.status_text = "گوش دادن متوقف شد."

    def _request_permissions_and_start(self):
        def callback(permissions, results):
            if all(results):
                self.status_text = "مجوز داده شد، شروع..."
                self._register_step_listener()
            else:
                self.status_text = "مجوز رد شد."

        try:
            if not check_permission(Permission.ACTIVITY_RECOGNITION):
                request_permissions([Permission.ACTIVITY_RECOGNITION], callback)
            else:
                self._register_step_listener()
        except Exception:
            self._register_step_listener()

    def _register_step_listener(self):
        if not self.sensor_manager:
            self.status_text = "سنسور یافت نشد."
            return

        class StepListener(PythonJavaClass):
            __javainterfaces__ = ['android/hardware/SensorEventListener']
            __javacontext__ = 'app'

            def __init__(inner_self, outer):
                super().__init__()
                inner_self.outer = outer

            @java_method('(Landroid/hardware/SensorEvent;)V')
            def onSensorChanged(inner_self, event):
                try:
                    vals = event.values
                    if vals and len(vals) > 0:
                        v0 = vals[0]
                        steps = 1 if v0 <= 1 else int(round(v0))
                        inner_self.outer._add_health(steps)
                except Exception as e:
                    inner_self.outer.status_text = f"خطا در سنسور: {e}"

            @java_method('(Landroid/hardware/Sensor;I)V')
            def onAccuracyChanged(inner_self, sensor, accuracy):
                pass

        try:
            TYPE_STEP_DETECTOR = getattr(self.Sensor, "TYPE_STEP_DETECTOR", 18)
            sensor = self.sensor_manager.getDefaultSensor(TYPE_STEP_DETECTOR)
            if sensor is None:
                self.status_text = "سنسور قدم‌شمار موجود نیست."
                return

            self.step_listener = StepListener(self)
            delay = self.SensorManager.SENSOR_DELAY_NORMAL
            self.sensor_manager.registerListener(self.step_listener, sensor, delay)
            self.listening = True
            self.status_text = "در حال گوش دادن به قدم‌ها..."
        except Exception as e:
            self.status_text = f"خطا در ثبت سنسور: {e}"


class HealthStepApp(App):
    def build(self):
        return RootWidget()


if __name__ == '__main__':
    HealthStepApp().run()
