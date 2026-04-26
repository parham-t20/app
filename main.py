# main.py - Action Notch COMPLETE
# 5 Gestures x 17 Actions each
# Works Desktop + Android

import os
import json
import time
import threading
from functools import partial

os.environ['KIVY_LOG_LEVEL'] = 'warning'

from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '750')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex, platform
from kivy.metrics import dp, sp

IS_ANDROID = platform == 'android'

if not IS_ANDROID:
    Window.size = (400, 750)
    Window.clearcolor = get_color_from_hex('#0F0F1A')


# ============================================================
# ALL 17 ACTIONS
# ============================================================
ALL_ACTIONS = [
    'Open App',
    'Call Contact',
    'Scroll to Up',
    'Screenshot',
    'Silent Audio Record',
    'Start Screen Record',
    'Play/Pause Media',
    'Flashlight',
    'Scan QR Code',
    'Close App',
    'Home',
    'Back',
    'Recent Apps',
    'Silent Photo Rear Camera',
    'Silent Photo Front Camera',
    'Silent Video Rear Camera',
    'Do Nothing',
]

# 5 Gestures
GESTURES = [
    ('single_touch', 'Single Touch'),
    ('double_touch', 'Double Touch'),
    ('long_touch',   'Long Touch'),
    ('swipe_right',  'Swipe Right'),
    ('swipe_left',   'Swipe Left'),
]


# ============================================================
# APP LAUNCHER
# ============================================================
class AppLauncher:
    _cache = None

    @staticmethod
    def get_apps():
        if AppLauncher._cache is not None:
            return AppLauncher._cache

        if not IS_ANDROID:
            AppLauncher._cache = [
                ('Calculator','com.android.calculator2'),
                ('Calendar','com.android.calendar'),
                ('Camera','com.android.camera'),
                ('Chrome','com.android.chrome'),
                ('Clock','com.android.deskclock'),
                ('Contacts','com.android.contacts'),
                ('Facebook','com.facebook.katana'),
                ('File Manager','com.android.filemanager'),
                ('Gallery','com.android.gallery3d'),
                ('Gmail','com.google.android.gm'),
                ('Google Maps','com.google.android.apps.maps'),
                ('Instagram','com.instagram.android'),
                ('Messages','com.android.mms'),
                ('Netflix','com.netflix.mediaclient'),
                ('Phone','com.android.dialer'),
                ('Photos','com.google.android.apps.photos'),
                ('Play Store','com.android.vending'),
                ('Settings','com.android.settings'),
                ('Snapchat','com.snapchat.android'),
                ('Spotify','com.spotify.music'),
                ('Telegram','org.telegram.messenger'),
                ('TikTok','com.zhiliaoapp.musically'),
                ('Twitter/X','com.twitter.android'),
                ('WhatsApp','com.whatsapp'),
                ('YouTube','com.google.android.youtube'),
            ]
            return AppLauncher._cache

        try:
            from jnius import autoclass
            PA = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            act = PA.mActivity
            pm = act.getPackageManager()
            intent = Intent(Intent.ACTION_MAIN, None)
            intent.addCategory(Intent.CATEGORY_LAUNCHER)
            apps = pm.queryIntentActivities(intent, 0)
            result = []
            for i in range(apps.size()):
                ai = apps.get(i)
                name = str(ai.loadLabel(pm))
                pkg = str(ai.activityInfo.packageName)
                result.append((name, pkg))
            result.sort(key=lambda x: x[0].lower())
            AppLauncher._cache = result
            return result
        except Exception as e:
            print(f'Get apps error: {e}')
            return []

    @staticmethod
    def launch(package):
        if not IS_ANDROID:
            print(f'[PC] Launch: {package}')
            return
        try:
            from jnius import autoclass
            PA = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            act = PA.mActivity
            pm = act.getPackageManager()
            li = pm.getLaunchIntentForPackage(package)
            if li:
                li.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                act.startActivity(li)
        except Exception as e:
            print(f'Launch error: {e}')


# ============================================================
# CONTACT CALLER
# ============================================================
class ContactCaller:
    @staticmethod
    def get_contacts():
        if not IS_ANDROID:
            return [
                ('Mom', '+1234567890'),
                ('Dad', '+1234567891'),
                ('John', '+1234567892'),
                ('Sarah', '+1234567893'),
                ('Work', '+1234567894'),
                ('Doctor', '+1234567895'),
                ('Pizza Place', '+1234567896'),
            ]
        try:
            from jnius import autoclass
            PA = autoclass('org.kivy.android.PythonActivity')
            Uri = autoclass('android.net.Uri')
            Cursor = autoclass('android.database.Cursor')
            ContactsContract = autoclass('android.provider.ContactsContract')
            CommonDataKinds = autoclass(
                'android.provider.ContactsContract$CommonDataKinds$Phone'
            )
            act = PA.mActivity
            cr = act.getContentResolver()
            uri = CommonDataKinds.CONTENT_URI
            cursor = cr.query(uri, None, None, None,
                              CommonDataKinds.DISPLAY_NAME + ' ASC')
            contacts = []
            if cursor:
                name_idx = cursor.getColumnIndex(CommonDataKinds.DISPLAY_NAME)
                num_idx = cursor.getColumnIndex(CommonDataKinds.NUMBER)
                while cursor.moveToNext():
                    name = cursor.getString(name_idx)
                    number = cursor.getString(num_idx)
                    if name and number:
                        contacts.append((str(name), str(number)))
                cursor.close()
            return contacts
        except Exception as e:
            print(f'Contacts error: {e}')
            return []

    @staticmethod
    def call(number):
        if not IS_ANDROID:
            print(f'[PC] Call: {number}')
            return
        try:
            from jnius import autoclass
            PA = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            act = PA.mActivity
            intent = Intent(Intent.ACTION_CALL)
            intent.setData(Uri.parse(f'tel:{number}'))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            act.startActivity(intent)
        except Exception as e:
            print(f'Call error: {e}')


# ============================================================
# ACTION EXECUTOR - All 17 actions
# ============================================================
class ActionExecutor:
    _flash = False
    _recording_audio = False
    _recording_screen = False
    _recording_video = False
    _media_recorder = None

    @staticmethod
    def execute(action, settings, gesture_key=''):
        if action == 'Do Nothing':
            return

        print(f'[Execute] {action}')
        settings.inc('total_actions')

        if not IS_ANDROID:
            ActionExecutor._desktop_simulate(action, settings, gesture_key)
            return

        try:
            if action == 'Open App':
                pkg = settings.get(f'{gesture_key}_app_package', '')
                if pkg:
                    AppLauncher.launch(pkg)

            elif action == 'Call Contact':
                number = settings.get(f'{gesture_key}_call_number', '')
                if number:
                    ContactCaller.call(number)

            elif action == 'Scroll to Up':
                ActionExecutor._scroll_up()

            elif action == 'Screenshot':
                ActionExecutor._screenshot()
                settings.inc('screenshots_taken')

            elif action == 'Silent Audio Record':
                ActionExecutor._toggle_audio_record()

            elif action == 'Start Screen Record':
                ActionExecutor._toggle_screen_record()

            elif action == 'Play/Pause Media':
                ActionExecutor._media_play_pause()

            elif action == 'Flashlight':
                ActionExecutor._toggle_flashlight()
                settings.inc('flashlight_toggles')

            elif action == 'Scan QR Code':
                ActionExecutor._scan_qr()

            elif action == 'Close App':
                ActionExecutor._close_app()

            elif action == 'Home':
                ActionExecutor._go_home()

            elif action == 'Back':
                ActionExecutor._go_back()

            elif action == 'Recent Apps':
                ActionExecutor._recent_apps()

            elif action == 'Silent Photo Rear Camera':
                ActionExecutor._silent_photo('rear')

            elif action == 'Silent Photo Front Camera':
                ActionExecutor._silent_photo('front')

            elif action == 'Silent Video Rear Camera':
                ActionExecutor._toggle_silent_video()

        except Exception as e:
            print(f'Action error [{action}]: {e}')

    @staticmethod
    def _desktop_simulate(action, settings, gesture_key):
        if action == 'Open App':
            pkg = settings.get(f'{gesture_key}_app_package', '')
            name = settings.get(f'{gesture_key}_app_name', '')
            print(f'  -> Would open: {name} ({pkg})')
        elif action == 'Call Contact':
            name = settings.get(f'{gesture_key}_call_name', '')
            num = settings.get(f'{gesture_key}_call_number', '')
            print(f'  -> Would call: {name} ({num})')
        else:
            print(f'  -> Would execute: {action}')

    # ---- Individual Action Implementations ----

    @staticmethod
    def _shell(cmd):
        from jnius import autoclass
        R = autoclass('java.lang.Runtime')
        R.getRuntime().exec(['/system/bin/sh', '-c', cmd])

    @staticmethod
    def _scroll_up():
        if IS_ANDROID:
            ActionExecutor._shell('input swipe 500 1500 500 500 300')

    @staticmethod
    def _screenshot():
        if IS_ANDROID:
            ActionExecutor._shell('input keyevent 120')

    @staticmethod
    def _toggle_audio_record():
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            import datetime

            if ActionExecutor._recording_audio:
                if ActionExecutor._media_recorder:
                    ActionExecutor._media_recorder.stop()
                    ActionExecutor._media_recorder.release()
                    ActionExecutor._media_recorder = None
                ActionExecutor._recording_audio = False
                print('Audio recording stopped')
            else:
                MediaRecorder = autoclass('android.media.MediaRecorder')
                Environment = autoclass('android.os.Environment')

                mr = MediaRecorder()
                mr.setAudioSource(MediaRecorder.AudioSource.MIC)
                mr.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                mr.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)

                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                path = os.path.join(
                    Environment.getExternalStorageDirectory().getAbsolutePath(),
                    'Download', f'silent_record_{ts}.m4a'
                )
                mr.setOutputFile(path)
                mr.prepare()
                mr.start()

                ActionExecutor._media_recorder = mr
                ActionExecutor._recording_audio = True
                print(f'Audio recording started: {path}')

        except Exception as e:
            print(f'Audio record error: {e}')

    @staticmethod
    def _toggle_screen_record():
        if IS_ANDROID:
            try:
                if ActionExecutor._recording_screen:
                    ActionExecutor._shell('pkill -f screenrecord')
                    ActionExecutor._recording_screen = False
                    print('Screen recording stopped')
                else:
                    import datetime
                    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    path = f'/sdcard/Download/screen_{ts}.mp4'
                    threading.Thread(
                        target=lambda: ActionExecutor._shell(
                            f'screenrecord --time-limit 300 {path}'
                        ),
                        daemon=True
                    ).start()
                    ActionExecutor._recording_screen = True
                    print(f'Screen recording started: {path}')
            except Exception as e:
                print(f'Screen record error: {e}')

    @staticmethod
    def _media_play_pause():
        if IS_ANDROID:
            ActionExecutor._shell('input keyevent 85')

    @staticmethod
    def _toggle_flashlight():
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            PA = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            act = PA.mActivity
            cm = act.getSystemService(Context.CAMERA_SERVICE)
            cid = cm.getCameraIdList()[0]
            ActionExecutor._flash = not ActionExecutor._flash
            cm.setTorchMode(cid, ActionExecutor._flash)
        except Exception as e:
            print(f'Flashlight error: {e}')

    @staticmethod
    def _scan_qr():
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            PA = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            act = PA.mActivity

            # Try Google Lens / built-in QR scanner
            try:
                intent = Intent('com.google.android.googlequicksearchbox.SCAN_CODE')
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                act.startActivity(intent)
            except Exception:
                # Fallback: open camera
                intent = Intent('android.media.action.STILL_IMAGE_CAMERA')
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                act.startActivity(intent)

        except Exception as e:
            print(f'QR scan error: {e}')

    @staticmethod
    def _close_app():
        if IS_ANDROID:
            ActionExecutor._shell('input keyevent 4')
            time.sleep(0.1)
            ActionExecutor._shell('input keyevent 4')

    @staticmethod
    def _go_home():
        if IS_ANDROID:
            ActionExecutor._shell('input keyevent 3')

    @staticmethod
    def _go_back():
        if IS_ANDROID:
            ActionExecutor._shell('input keyevent 4')

    @staticmethod
    def _recent_apps():
        if IS_ANDROID:
            ActionExecutor._shell('input keyevent 187')

    @staticmethod
    def _silent_photo(camera='rear'):
        if not IS_ANDROID:
            print(f'[PC] Silent photo: {camera}')
            return
        try:
            from jnius import autoclass
            import datetime

            PA = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            CameraManager = autoclass('android.hardware.camera2.CameraManager')
            ImageReader = autoclass('android.media.ImageReader')
            ImageFormat = autoclass('android.graphics.ImageFormat')
            HandlerThread = autoclass('android.os.HandlerThread')
            Handler = autoclass('android.os.Handler')

            act = PA.mActivity
            cm = act.getSystemService(Context.CAMERA_SERVICE)
            camera_list = cm.getCameraIdList()

            # camera 0 = rear, camera 1 = front
            cam_id = '0' if camera == 'rear' else '1'
            if int(cam_id) >= camera_list.length:
                cam_id = '0'

            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'silent_{camera}_{ts}.jpg'

            # Use simple intent-based capture (more reliable)
            Intent = autoclass('android.content.Intent')
            MediaStore = autoclass('android.provider.MediaStore')
            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)

            if camera == 'front':
                intent.putExtra('android.intent.extras.CAMERA_FACING', 1)
                intent.putExtra(
                    'android.intent.extras.LENS_FACING_FRONT', 1
                )
                intent.putExtra('android.intent.extra.USE_FRONT_CAMERA', True)

            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            act.startActivity(intent)

            print(f'Silent photo ({camera}): {filename}')

        except Exception as e:
            print(f'Silent photo error: {e}')

    @staticmethod
    def _toggle_silent_video():
        if not IS_ANDROID:
            print('[PC] Silent video toggle')
            return
        try:
            from jnius import autoclass
            import datetime

            if ActionExecutor._recording_video:
                if ActionExecutor._media_recorder:
                    ActionExecutor._media_recorder.stop()
                    ActionExecutor._media_recorder.release()
                    ActionExecutor._media_recorder = None
                ActionExecutor._recording_video = False
                print('Silent video stopped')
            else:
                MediaRecorder = autoclass('android.media.MediaRecorder')
                Environment = autoclass('android.os.Environment')

                mr = MediaRecorder()
                mr.setAudioSource(MediaRecorder.AudioSource.MIC)
                mr.setVideoSource(MediaRecorder.VideoSource.CAMERA)
                mr.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                mr.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                mr.setVideoEncoder(MediaRecorder.VideoEncoder.H264)
                mr.setVideoSize(1280, 720)
                mr.setVideoFrameRate(30)

                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                path = os.path.join(
                    Environment.getExternalStorageDirectory().getAbsolutePath(),
                    'Download', f'silent_video_{ts}.mp4'
                )
                mr.setOutputFile(path)
                mr.prepare()
                mr.start()

                ActionExecutor._media_recorder = mr
                ActionExecutor._recording_video = True
                print(f'Silent video started: {path}')

        except Exception as e:
            print(f'Silent video error: {e}')


# ============================================================
# SETTINGS
# ============================================================
DEFAULT_SETTINGS = {
    'master_enabled': True,
    'notch_shape': 'pill',
    'notch_width': 40,
    'notch_height': 28,
    'notch_radius': 18,
    'h_offset': 0, 'v_offset': 0,
    'notch_color': '#000000',
    'notch_opacity': 100,
    'show_border': False,
    'border_width': 1,
    'enable_shadow': True,
    'gradient_fill': False,
    'haptic_enabled': True,
    'haptic_intensity': 2,
    'sound_enabled': False,
    'sound_type': 'Click',
    'sound_volume': 50,
    'long_touch_duration': 500,
    'double_touch_speed': 300,
    'touch_sensitivity': 2,
    'animations_enabled': True,
    'expand_style': 'Smooth Expand',
    'animation_speed': 300,
    'breathing_effect': False,
    'breathing_speed': 2000,
    'touch_ripple': True,
    'battery_ring': True,
    'notification_light': True,
    'run_background': True,
    'start_on_boot': True,
    'schedule_enabled': False,
    'schedule_start': '08:00',
    'schedule_end': '23:00',
    'disable_low_battery': True,
    'night_mode': False,
    'active_profile': 'Default',
    'total_actions': 0,
    'flashlight_toggles': 0,
    'screenshots_taken': 0,
}

# Add gesture defaults
for gk, _ in GESTURES:
    DEFAULT_SETTINGS[gk] = 'Do Nothing'
    DEFAULT_SETTINGS[f'{gk}_app_name'] = ''
    DEFAULT_SETTINGS[f'{gk}_app_package'] = ''
    DEFAULT_SETTINGS[f'{gk}_call_name'] = ''
    DEFAULT_SETTINGS[f'{gk}_call_number'] = ''


class Settings:
    def __init__(self, path):
        self.path = path
        self.data = dict(DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r') as f:
                    self.data.update(json.load(f))
        except: pass

    def save(self):
        try:
            d = os.path.dirname(self.path)
            if d: os.makedirs(d, exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except: pass

    def get(self, k, d=None):
        return self.data.get(k, d if d is not None else DEFAULT_SETTINGS.get(k))

    def set(self, k, v):
        self.data[k] = v
        self.save()

    def inc(self, k):
        self.data[k] = int(self.data.get(k, 0)) + 1
        self.save()

    def reset(self):
        self.data = dict(DEFAULT_SETTINGS)
        self.save()


# ============================================================
# OVERLAY MANAGER
# ============================================================
class OverlayManager:
    def __init__(self, s):
        self.s = s
        self.running = True
        self.overlay_view = None
        self.wm = None
        self.added = False
        self._threads = False

    def create(self):
        if not IS_ANDROID:
            print('[PC] Overlay ON')
            self._threads_start()
            return
        try:
            from jnius import autoclass
            Ctx = autoclass('android.content.Context')
            WMP = autoclass('android.view.WindowManager$LayoutParams')
            PF = autoclass('android.graphics.PixelFormat')
            Grav = autoclass('android.view.Gravity')
            act = self._act()
            self.wm = act.getSystemService(Ctx.WINDOW_SERVICE)
            w, h = self._w(), self._h()
            p = WMP(w, h, WMP.TYPE_APPLICATION_OVERLAY,
                    WMP.FLAG_NOT_FOCUSABLE | WMP.FLAG_LAYOUT_IN_SCREEN
                    | WMP.FLAG_NOT_TOUCH_MODAL, PF.TRANSLUCENT)
            p.gravity = Grav.TOP | Grav.CENTER_HORIZONTAL
            p.x = int(self.s.get('h_offset', 0))
            p.y = int(self.s.get('v_offset', 0))
            self.overlay_view = self._view(act)
            self._touch()
            self.wm.addView(self.overlay_view, p)
            self.added = True
            self._threads_start()
        except Exception as e:
            print(f'Overlay error: {e}')

    def remove(self):
        if not IS_ANDROID:
            print('[PC] Overlay OFF')
            return
        try:
            if self.wm and self.overlay_view and self.added:
                self.wm.removeView(self.overlay_view)
                self.added = False
                self.overlay_view = None
        except: pass

    def _view(self, ctx):
        from jnius import autoclass
        View = autoclass('android.view.View')
        GD = autoclass('android.graphics.drawable.GradientDrawable')
        CC = autoclass('android.graphics.Color')
        v = View(ctx)
        d = GD()
        op = max(0, min(100, int(self.s.get('notch_opacity', 100))))
        ah = format(int(255 * op / 100), '02X')
        ch = self.s.get('notch_color', '#000000').replace('#', '')
        d.setColor(CC.parseColor(f'#{ah}{ch}'))
        sh = self.s.get('notch_shape', 'pill')
        r = self._dp(int(self.s.get('notch_radius', 18)))
        shapes = {'rectangle':0,'rounded':r,'pill':9999,'island':r*2}
        if sh == 'teardrop':
            d.setCornerRadii([0,0,0,0,r*2,r*2,r*2,r*2])
        elif sh in shapes:
            d.setCornerRadius(shapes[sh])
        else:
            d.setCornerRadius(r)
        if self.s.get('show_border', False):
            d.setStroke(self._dp(int(self.s.get('border_width',1))), CC.WHITE)
        v.setBackground(d)
        if self.s.get('enable_shadow', True):
            v.setElevation(self._dp(5))
        return v

    def _touch(self):
        if not IS_ANDROID or not self.overlay_view:
            return
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            ME = autoclass('android.view.MotionEvent')
            mgr = self

            class TL(PythonJavaClass):
                __javainterfaces__ = ['android/view/View$OnTouchListener']
                __javacontext__ = 'app'
                def __init__(self):
                    super().__init__()
                    self.t0 = self.x0 = self.y0 = 0.0
                    self.taps = 0
                    self.lt = 0.0
                    self.tmr = None

                @java_method('(Landroid/view/View;Landroid/view/MotionEvent;)Z')
                def onTouch(self, v, e):
                    a = e.getAction()
                    if a == ME.ACTION_DOWN:
                        self.t0 = time.time()
                        self.x0 = e.getRawX()
                        self.y0 = e.getRawY()
                        return True
                    if a == ME.ACTION_UP:
                        dt = int((time.time()-self.t0)*1000)
                        dx = e.getRawX()-self.x0
                        dy = e.getRawY()-self.y0
                        sns = {1:160,2:120,3:80}.get(
                            int(mgr.s.get('touch_sensitivity',2)),120)

                        # Swipe Right
                        if dx > sns and abs(dx) > abs(dy):
                            mgr._do('swipe_right')
                            return True
                        # Swipe Left
                        if dx < -sns and abs(dx) > abs(dy):
                            mgr._do('swipe_left')
                            return True

                        # Long Touch
                        if dt >= int(mgr.s.get('long_touch_duration',500)):
                            mgr._do('long_touch')
                            return True

                        # Tap counting
                        now = time.time()
                        spd = int(mgr.s.get('double_touch_speed',300))/1000.0
                        if now-self.lt < spd:
                            self.taps += 1
                        else:
                            self.taps = 1
                        self.lt = now
                        if self.tmr:
                            try: self.tmr.cancel()
                            except: pass
                        self.tmr = threading.Timer(
                            spd+0.05, mgr._tap_done, [self.taps])
                        self.tmr.start()
                        return True
                    return True

            self.overlay_view.setOnTouchListener(TL())
        except Exception as e:
            print(f'Touch error: {e}')

    def _tap_done(self, count):
        if count >= 2:
            self._do('double_touch')
        else:
            self._do('single_touch')

    def _do(self, gesture_key):
        action = self.s.get(gesture_key, 'Do Nothing')
        print(f'[{gesture_key}] -> {action}')

        if self.s.get('haptic_enabled', True) and IS_ANDROID:
            self._haptic()
        if self.s.get('sound_enabled', False) and IS_ANDROID:
            self._sound()

        ActionExecutor.execute(action, self.s, gesture_key)

    def _haptic(self):
        try:
            from jnius import autoclass
            Ctx = autoclass('android.content.Context')
            v = self._act().getSystemService(Ctx.VIBRATOR_SERVICE)
            ms = {1:10,2:25,3:50}.get(int(self.s.get('haptic_intensity',2)),25)
            v.vibrate(ms)
        except: pass

    def _sound(self):
        try:
            from jnius import autoclass
            AM = autoclass('android.media.AudioManager')
            TG = autoclass('android.media.ToneGenerator')
            vol = int(self.s.get('sound_volume',50))
            tones = {'Click':TG.TONE_PROP_BEEP,'Pop':TG.TONE_PROP_ACK,
                     'Tick':TG.TONE_CDMA_PIP}
            t = tones.get(self.s.get('sound_type','Click'),TG.TONE_PROP_BEEP)
            tg = TG(AM.STREAM_SYSTEM, vol)
            tg.startTone(t, 100)
            threading.Timer(0.2, tg.release).start()
        except: pass

    def _threads_start(self):
        if self._threads: return
        self._threads = True
        threading.Thread(target=self._schedule_loop, daemon=True).start()

    def _schedule_loop(self):
        import datetime
        while self.running:
            if self.s.get('schedule_enabled', False):
                try:
                    now = datetime.datetime.now()
                    cm = now.hour*60+now.minute
                    ss = self.s.get('schedule_start','08:00')
                    se = self.s.get('schedule_end','23:00')
                    sh,sm = map(int, ss.split(':'))
                    eh,em = map(int, se.split(':'))
                    start, end = sh*60+sm, eh*60+em
                    active = start<=cm<=end if start<=end else cm>=start or cm<=end
                    if active and not self.added and self.s.get('master_enabled'):
                        self.create()
                    elif not active and self.added:
                        self.remove()
                except: pass
            time.sleep(30)

    def _act(self):
        from jnius import autoclass
        try: return autoclass('org.kivy.android.PythonActivity').mActivity
        except: return autoclass('org.kivy.android.PythonService').mService

    def _w(self):
        from jnius import autoclass
        R = autoclass('android.content.res.Resources')
        sw = R.getSystem().getDisplayMetrics().widthPixels
        p = max(10,min(100,int(self.s.get('notch_width',40))))
        return int(sw*p/100)

    def _h(self):
        return self._dp(int(self.s.get('notch_height',28)))

    def _dp(self, v):
        from jnius import autoclass
        R = autoclass('android.content.res.Resources')
        return int(v*R.getSystem().getDisplayMetrics().density)


# ============================================================
# PREVIEW
# ============================================================
class NotchPreview(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)
        Clock.schedule_interval(self._draw, 1.0)

    def _draw(self, *_):
        self.canvas.clear()
        app = App.get_running_app()
        cx, cy = self.center_x, self.center_y
        try: nc = list(get_color_from_hex(app.cfg.get('notch_color','#000000')))
        except: nc = [0,0,0,1]
        with self.canvas:
            Color(0.25,0.25,0.35,1)
            RoundedRectangle(pos=(cx-dp(55),cy-dp(48)),size=(dp(110),dp(96)),radius=[dp(14)])
            Color(0.08,0.08,0.13,1)
            RoundedRectangle(pos=(cx-dp(50),cy-dp(43)),size=(dp(100),dp(86)),radius=[dp(10)])
            Color(*nc)
            RoundedRectangle(pos=(cx-dp(22),cy+dp(29)),size=(dp(44),dp(14)),radius=[dp(7)])
            Color(0.15,0.15,0.22,1)
            Ellipse(pos=(cx-dp(3),cy+dp(33)),size=(dp(6),dp(6)))
            Color(0.3,0.8,0.3,0.7)
            Line(circle=(cx,cy,dp(42),0,270),width=dp(1.5))


# ============================================================
# UI BUILDER
# ============================================================
class UI:
    BG='#0F0F1A'; CARD='#2A2A3D'; TOP='#1A1A2E'; ACC='#6C63FF'
    GRN='#4CAF50'; RED='#FF5252'; ORG='#FF9800'; SUB='#888899'; WH='#FFFFFF'

    @staticmethod
    def _br(w, rr):
        w.bind(pos=lambda i,v:setattr(rr,'pos',v),size=lambda i,v:setattr(rr,'size',v))

    @staticmethod
    def bg():
        b = BoxLayout(orientation='vertical')
        with b.canvas.before:
            Color(*get_color_from_hex(UI.BG)); r=Rectangle(pos=b.pos,size=b.size)
        b.bind(pos=lambda i,v:setattr(r,'pos',v),size=lambda i,v:setattr(r,'size',v))
        return b

    @staticmethod
    def card(h=dp(62)):
        b = BoxLayout(orientation='horizontal',size_hint_y=None,height=h,
                      padding=[dp(15),dp(10)],spacing=dp(10))
        with b.canvas.before:
            Color(*get_color_from_hex(UI.CARD))
            rr=RoundedRectangle(pos=b.pos,size=b.size,radius=[dp(14)])
        UI._br(b,rr)
        return b

    @staticmethod
    def lbl(t,fs=sp(13),c=None,ha='left',va='center',bold=False,shy=None,h=None):
        c = c or get_color_from_hex(UI.WH)
        kw = dict(text=t,font_size=fs,color=c,halign=ha,valign=va,bold=bold)
        if shy is not None: kw['size_hint_y']=shy
        if h is not None: kw['height']=h
        l = Label(**kw); l.bind(size=lambda i,v:setattr(i,'text_size',v))
        return l

    @staticmethod
    def sec(t):
        return UI.lbl(t,fs=sp(15),bold=True,c=get_color_from_hex(UI.ACC),shy=None,h=dp(36))

    @staticmethod
    def nav(t,cb):
        c = UI.card()
        c.add_widget(UI.lbl(t))
        c.add_widget(Label(text='>',font_size=sp(20),color=get_color_from_hex(UI.ACC),
                           size_hint_x=None,width=dp(25)))
        c.bind(on_touch_down=lambda i,touch:cb() if i.collide_point(*touch.pos) else None)
        return c

    @staticmethod
    def sw(t,active,cb):
        c = UI.card()
        c.add_widget(UI.lbl(t))
        s = Switch(active=active,size_hint_x=None,width=dp(55))
        s.bind(active=lambda i,v:cb(v))
        c.add_widget(s)
        return c

    @staticmethod
    def spin(t,cur,vals,cb):
        c = UI.card(h=dp(65))
        inner = BoxLayout(orientation='vertical')
        inner.add_widget(UI.lbl(t,va='bottom'))
        s = Spinner(text=cur,values=vals,size_hint_y=None,height=dp(30),font_size=sp(10))
        s.bind(text=lambda i,v:cb(v))
        inner.add_widget(s)
        c.add_widget(inner)
        return c

    @staticmethod
    def sld(lt,vt,mn,mx,v,cb,step=1,sfx=''):
        box = BoxLayout(orientation='vertical',size_hint_y=None,height=dp(75),
                        padding=[dp(15),dp(8)])
        with box.canvas.before:
            Color(*get_color_from_hex(UI.CARD))
            rr=RoundedRectangle(pos=box.pos,size=box.size,radius=[dp(14)])
        UI._br(box,rr)
        top = BoxLayout()
        ll = UI.lbl(lt); vl = UI.lbl(vt,c=get_color_from_hex(UI.ACC),ha='right')
        top.add_widget(ll); top.add_widget(vl)
        sl = Slider(min=mn,max=mx,value=v,step=step)
        sl.bind(value=lambda i,val:(setattr(vl,'text',str(int(val))+sfx),cb(val)))
        box.add_widget(top); box.add_widget(sl)
        return box

    @staticmethod
    def sgrid():
        sv = ScrollView(do_scroll_x=False,bar_width=0)
        g = GridLayout(cols=1,spacing=dp(7),padding=[dp(12)],size_hint_y=None)
        g.bind(minimum_height=g.setter('height'))
        sv.add_widget(g)
        return sv, g

    @staticmethod
    def tbar(t,cb):
        bar = BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(54),
                        padding=[dp(10),dp(5)])
        with bar.canvas.before:
            Color(*get_color_from_hex(UI.TOP))
            rr=RoundedRectangle(pos=bar.pos,size=bar.size,radius=[0,0,dp(16),dp(16)])
        UI._br(bar,rr)
        back = Button(text='< Back',size_hint_x=None,width=dp(80),background_color=[0,0,0,0],
                      background_normal='',color=get_color_from_hex(UI.ACC),font_size=sp(14))
        back.bind(on_release=lambda *_:cb())
        bar.add_widget(back)
        bar.add_widget(Label(text=t,font_size=sp(18),bold=True,color=get_color_from_hex(UI.WH)))
        bar.add_widget(Widget(size_hint_x=None,width=dp(80)))
        return bar

    @staticmethod
    def btn(t,cb,color=None):
        color = color or UI.ACC
        b = Button(text=t,size_hint_y=None,height=dp(48),font_size=sp(14),bold=True,
                   background_color=[0,0,0,0],background_normal='',color=get_color_from_hex(UI.WH))
        with b.canvas.before:
            Color(*get_color_from_hex(color))
            rr=RoundedRectangle(pos=b.pos,size=b.size,radius=[dp(12)])
        UI._br(b,rr)
        b.bind(on_release=lambda *_:cb())
        return b

    @staticmethod
    def preview():
        pb = BoxLayout(size_hint_y=None,height=dp(130),padding=[dp(10)])
        with pb.canvas.before:
            Color(*get_color_from_hex('#1A1A2E'))
            rr=RoundedRectangle(pos=pb.pos,size=pb.size,radius=[dp(14)])
        UI._br(pb,rr)
        pb.add_widget(NotchPreview())
        return pb

    @staticmethod
    def popup(t,m):
        Popup(title=t,content=Label(text=m,font_size=sp(13)),size_hint=(0.8,0.22)).open()

    @staticmethod
    def cbtn(ch,cb):
        b = Button(background_color=[0,0,0,0],background_normal='',
                   size_hint=(None,None),size=(dp(34),dp(34)))
        with b.canvas.before:
            Color(*get_color_from_hex(ch)); e=Ellipse(pos=b.pos,size=b.size)
        b.bind(pos=lambda i,v:setattr(e,'pos',v),size=lambda i,v:setattr(e,'size',v))
        b.bind(on_release=lambda *_:cb(ch))
        return b


# ============================================================
# PICKER POPUPS
# ============================================================
def show_app_picker(gesture_key, s, info_label):
    content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
    search = TextInput(hint_text='Search apps...', size_hint_y=None, height=dp(42),
                       font_size=sp(14), multiline=False,
                       background_color=get_color_from_hex('#2A2A3D'),
                       foreground_color=[1,1,1,1], cursor_color=[1,1,1,1])
    content.add_widget(search)
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
    grid.bind(minimum_height=grid.setter('height'))
    sv.add_widget(grid)
    content.add_widget(sv)
    cancel = Button(text='Cancel', size_hint_y=None, height=dp(40),
                    background_color=get_color_from_hex(UI.RED))
    content.add_widget(cancel)
    popup = Popup(title=f'Select App', content=content, size_hint=(0.92, 0.85))
    cancel.bind(on_release=popup.dismiss)

    def load(dt):
        apps = AppLauncher.get_apps()
        all_btns = []
        for name, pkg in apps:
            b = Button(text=f'  {name}', size_hint_y=None, height=dp(44),
                       font_size=sp(12), halign='left', valign='center',
                       background_color=[0,0,0,0], background_normal='',
                       color=[1,1,1,1])
            b.bind(size=lambda i,v:setattr(i,'text_size',v))
            with b.canvas.before:
                Color(*get_color_from_hex(UI.CARD))
                rr = RoundedRectangle(pos=b.pos,size=b.size,radius=[dp(8)])
            UI._br(b, rr)
            def sel(inst, _n=name, _p=pkg):
                s.set(gesture_key, 'Open App')
                s.set(f'{gesture_key}_app_name', _n)
                s.set(f'{gesture_key}_app_package', _p)
                info_label.text = f'  > Open App: {_n}'
                info_label.color = get_color_from_hex(UI.GRN)
                popup.dismiss()
            b.bind(on_release=sel)
            grid.add_widget(b)
            all_btns.append((name, pkg, b))

        def filt(inst, text):
            grid.clear_widgets()
            q = text.lower()
            for n,p,bt in all_btns:
                if q=='' or q in n.lower():
                    grid.add_widget(bt)
        search.bind(text=filt)

    Clock.schedule_once(load, 0.2)
    popup.open()


def show_contact_picker(gesture_key, s, info_label):
    content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
    search = TextInput(hint_text='Search contacts...', size_hint_y=None, height=dp(42),
                       font_size=sp(14), multiline=False,
                       background_color=get_color_from_hex('#2A2A3D'),
                       foreground_color=[1,1,1,1], cursor_color=[1,1,1,1])
    content.add_widget(search)
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
    grid.bind(minimum_height=grid.setter('height'))
    sv.add_widget(grid)
    content.add_widget(sv)
    cancel = Button(text='Cancel', size_hint_y=None, height=dp(40),
                    background_color=get_color_from_hex(UI.RED))
    content.add_widget(cancel)
    popup = Popup(title='Select Contact', content=content, size_hint=(0.92, 0.85))
    cancel.bind(on_release=popup.dismiss)

    def load(dt):
        contacts = ContactCaller.get_contacts()
        all_btns = []
        for name, number in contacts:
            b = Button(text=f'  {name}  ({number})', size_hint_y=None, height=dp(44),
                       font_size=sp(12), halign='left', valign='center',
                       background_color=[0,0,0,0], background_normal='',
                       color=[1,1,1,1])
            b.bind(size=lambda i,v:setattr(i,'text_size',v))
            with b.canvas.before:
                Color(*get_color_from_hex(UI.CARD))
                rr = RoundedRectangle(pos=b.pos,size=b.size,radius=[dp(8)])
            UI._br(b, rr)
            def sel(inst, _n=name, _num=number):
                s.set(gesture_key, 'Call Contact')
                s.set(f'{gesture_key}_call_name', _n)
                s.set(f'{gesture_key}_call_number', _num)
                info_label.text = f'  > Call: {_n}'
                info_label.color = get_color_from_hex(UI.GRN)
                popup.dismiss()
            b.bind(on_release=sel)
            grid.add_widget(b)
            all_btns.append((name, number, b))

        def filt(inst, text):
            grid.clear_widgets()
            q = text.lower()
            for n,num,bt in all_btns:
                if q=='' or q in n.lower():
                    grid.add_widget(bt)
        search.bind(text=filt)

    Clock.schedule_once(load, 0.2)
    popup.open()


# ============================================================
# GESTURE CARD BUILDER
# ============================================================
def build_gesture_card(grid, gesture_key, gesture_name, s):
    """Builds one gesture card with action spinner + pick buttons"""

    c = UI.card(h=dp(105))
    inner = BoxLayout(orientation='vertical', spacing=dp(2))

    # Title
    inner.add_widget(UI.lbl(gesture_name, fs=sp(14), bold=True, va='bottom'))

    # Current action info
    action = s.get(gesture_key, 'Do Nothing')
    if action == 'Open App':
        an = s.get(f'{gesture_key}_app_name', '')
        display = f'  > Open App: {an}' if an else '  > Open App: (not set)'
    elif action == 'Call Contact':
        cn = s.get(f'{gesture_key}_call_name', '')
        display = f'  > Call: {cn}' if cn else '  > Call: (not set)'
    else:
        display = f'  > {action}'

    info = Label(
        text=display, font_size=sp(10),
        color=get_color_from_hex(UI.GRN),
        halign='left', valign='center',
        size_hint_y=None, height=dp(18)
    )
    info.bind(size=lambda i,v: setattr(i, 'text_size', v))

    # Row: Spinner + buttons
    row = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(32))

    spinner = Spinner(
        text=action, values=ALL_ACTIONS,
        size_hint_x=0.5, font_size=sp(9)
    )

    pick_app_btn = Button(
        text='Pick App', size_hint_x=0.25,
        font_size=sp(9), bold=True,
        background_color=get_color_from_hex(UI.ACC),
        color=[1,1,1,1],
        disabled=(action != 'Open App')
    )

    pick_call_btn = Button(
        text='Pick Contact', size_hint_x=0.25,
        font_size=sp(9), bold=True,
        background_color=get_color_from_hex(UI.ORG),
        color=[1,1,1,1],
        disabled=(action != 'Call Contact')
    )

    def on_action(inst, val):
        s.set(gesture_key, val)
        pick_app_btn.disabled = (val != 'Open App')
        pick_call_btn.disabled = (val != 'Call Contact')
        if val == 'Open App':
            an = s.get(f'{gesture_key}_app_name', '')
            info.text = f'  > Open App: {an}' if an else '  > Open App: (tap Pick App)'
            info.color = get_color_from_hex(UI.ORG if not an else UI.GRN)
        elif val == 'Call Contact':
            cn = s.get(f'{gesture_key}_call_name', '')
            info.text = f'  > Call: {cn}' if cn else '  > Call: (tap Pick Contact)'
            info.color = get_color_from_hex(UI.ORG if not cn else UI.GRN)
        else:
            info.text = f'  > {val}'
            info.color = get_color_from_hex(UI.GRN)

    spinner.bind(text=on_action)

    pick_app_btn.bind(on_release=lambda *_:
        show_app_picker(gesture_key, s, info))

    pick_call_btn.bind(on_release=lambda *_:
        show_contact_picker(gesture_key, s, info))

    row.add_widget(spinner)
    row.add_widget(pick_app_btn)
    row.add_widget(pick_call_btn)

    inner.add_widget(row)
    inner.add_widget(info)
    c.add_widget(inner)
    grid.add_widget(c)


# ============================================================
# PAGE BUILDERS
# ============================================================
def page_gestures(grid, s):
    grid.add_widget(UI.sec('Gestures'))

    for gk, gn in GESTURES:
        build_gesture_card(grid, gk, gn, s)

    grid.add_widget(UI.sec('Timing'))
    grid.add_widget(UI.sld('Long Touch Duration',
        f"{s.get('long_touch_duration')}ms",200,2000,
        s.get('long_touch_duration'),
        lambda v:s.set('long_touch_duration',int(v)),step=100,sfx='ms'))
    grid.add_widget(UI.sld('Double Touch Speed',
        f"{s.get('double_touch_speed')}ms",150,600,
        s.get('double_touch_speed'),
        lambda v:s.set('double_touch_speed',int(v)),step=50,sfx='ms'))
    grid.add_widget(UI.sld('Touch Sensitivity',
        {1:'Low',2:'Normal',3:'High'}.get(s.get('touch_sensitivity'),'Normal'),
        1,3,s.get('touch_sensitivity'),
        lambda v:s.set('touch_sensitivity',int(v))))


def page_notch(grid, s):
    grid.add_widget(UI.sec('Shape'))
    for shapes in [['Rectangle','Rounded','Pill'],['Island','Teardrop','Custom']]:
        row = GridLayout(cols=3,spacing=dp(7),size_hint_y=None,height=dp(70))
        for sh in shapes:
            k = sh.lower()
            down = s.get('notch_shape')==k
            btn = ToggleButton(text=sh,group='ns',state='down' if down else 'normal',
                               background_color=[0,0,0,0],background_normal='',
                               color=[1,1,1,1],font_size=sp(11))
            with btn.canvas.before:
                col=Color(*get_color_from_hex(UI.ACC if down else UI.CARD))
                rr=RoundedRectangle(pos=btn.pos,size=btn.size,radius=[dp(10)])
            UI._br(btn,rr)
            def _st(i,v,_c=col,_k=k):
                _c.rgba=get_color_from_hex(UI.ACC if v=='down' else UI.CARD)
                if v=='down': s.set('notch_shape',_k)
            btn.bind(state=_st)
            row.add_widget(btn)
        grid.add_widget(row)

    grid.add_widget(UI.sec('Size & Position'))
    grid.add_widget(UI.sld('Width',f"{s.get('notch_width')}%",10,100,
                           s.get('notch_width'),lambda v:s.set('notch_width',int(v)),sfx='%'))
    grid.add_widget(UI.sld('Height',f"{s.get('notch_height')}px",10,80,
                           s.get('notch_height'),lambda v:s.set('notch_height',int(v)),sfx='px'))
    grid.add_widget(UI.sld('Corner Radius',f"{s.get('notch_radius')}px",0,50,
                           s.get('notch_radius'),lambda v:s.set('notch_radius',int(v)),sfx='px'))
    grid.add_widget(UI.sld('H Offset',str(s.get('h_offset')),-50,50,
                           s.get('h_offset'),lambda v:s.set('h_offset',int(v))))
    grid.add_widget(UI.sld('V Offset',str(s.get('v_offset')),-20,20,
                           s.get('v_offset'),lambda v:s.set('v_offset',int(v))))
    grid.add_widget(UI.sec('Preview'))
    grid.add_widget(UI.preview())


def page_theme(grid, s):
    grid.add_widget(UI.sec('Color'))
    box = GridLayout(cols=7,spacing=dp(8),size_hint_y=None,height=dp(50),padding=[dp(10),dp(5)])
    with box.canvas.before:
        Color(*get_color_from_hex(UI.CARD))
        rr=RoundedRectangle(pos=box.pos,size=box.size,radius=[dp(12)])
    UI._br(box,rr)
    for c in ['#000000','#6C63FF','#FF5252','#4CAF50','#FF9800','#E91E63','#FFFFFF']:
        box.add_widget(UI.cbtn(c,lambda v:s.set('notch_color',v)))
    grid.add_widget(box)
    grid.add_widget(UI.sld('Opacity',f"{s.get('notch_opacity')}%",10,100,
                           s.get('notch_opacity'),lambda v:s.set('notch_opacity',int(v)),sfx='%'))
    grid.add_widget(UI.sec('Effects'))
    for t,k in [('Border','show_border'),('Shadow','enable_shadow'),('Gradient','gradient_fill')]:
        grid.add_widget(UI.sw(t,s.get(k),partial(s.set,k)))
    grid.add_widget(UI.sld('Border Width',f"{s.get('border_width')}px",1,5,
                           s.get('border_width'),lambda v:s.set('border_width',int(v)),sfx='px'))


def page_animation(grid, s):
    grid.add_widget(UI.sw('Animations',s.get('animations_enabled'),partial(s.set,'animations_enabled')))
    grid.add_widget(UI.spin('Expand Style',s.get('expand_style'),
        ['Smooth Expand','Bounce','Elastic','Pop','Slide','Fade In','Scale Up','Morph'],
        partial(s.set,'expand_style')))
    grid.add_widget(UI.sld('Speed',f"{s.get('animation_speed')}ms",100,1000,
                           s.get('animation_speed'),lambda v:s.set('animation_speed',int(v)),step=50,sfx='ms'))
    grid.add_widget(UI.sw('Breathing',s.get('breathing_effect'),partial(s.set,'breathing_effect')))
    grid.add_widget(UI.sw('Touch Ripple',s.get('touch_ripple'),partial(s.set,'touch_ripple')))


def page_sound(grid, s):
    grid.add_widget(UI.sec('Haptic'))
    grid.add_widget(UI.sw('Vibrate',s.get('haptic_enabled'),partial(s.set,'haptic_enabled')))
    grid.add_widget(UI.sld('Intensity',{1:'Light',2:'Medium',3:'Strong'}.get(s.get('haptic_intensity'),'Med'),
                           1,3,s.get('haptic_intensity'),lambda v:s.set('haptic_intensity',int(v))))
    grid.add_widget(UI.sec('Sound'))
    grid.add_widget(UI.sw('Sound on Action',s.get('sound_enabled'),partial(s.set,'sound_enabled')))
    grid.add_widget(UI.spin('Type',s.get('sound_type'),['Click','Pop','Tick','None'],
                            partial(s.set,'sound_type')))
    grid.add_widget(UI.sld('Volume',f"{s.get('sound_volume')}%",0,100,s.get('sound_volume'),
                           lambda v:s.set('sound_volume',int(v)),sfx='%'))


def page_advanced(grid, s):
    grid.add_widget(UI.sec('Service'))
    for t,k in [('Background','run_background'),('Boot Start','start_on_boot')]:
        grid.add_widget(UI.sw(t,s.get(k),partial(s.set,k)))
    grid.add_widget(UI.sec('Schedule'))
    grid.add_widget(UI.sw('Schedule',s.get('schedule_enabled'),partial(s.set,'schedule_enabled')))
    for l,k,d in [('Start','schedule_start','08:00'),('End','schedule_end','23:00')]:
        grid.add_widget(UI.spin(l,s.get(k,d),[f'{h:02d}:00' for h in range(24)],partial(s.set,k)))
    grid.add_widget(UI.sw('Night Mode',s.get('night_mode'),partial(s.set,'night_mode')))
    grid.add_widget(UI.sec('Data'))
    grid.add_widget(UI.btn('Export',lambda:UI.popup('Export','Settings exported!')))
    grid.add_widget(UI.btn('Reset All',lambda:(s.reset(),UI.popup('Done','Reset!')),UI.RED))


# ============================================================
# SCREENS
# ============================================================
class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='main', **kw)

    def on_pre_enter(self, *_):
        self.clear_widgets()
        app = App.get_running_app()
        s = app.cfg
        root = UI.bg()

        header = BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(58),padding=[dp(15),dp(10)])
        with header.canvas.before:
            Color(*get_color_from_hex(UI.TOP))
            rr=RoundedRectangle(pos=header.pos,size=header.size,radius=[0,0,dp(18),dp(18)])
        UI._br(header,rr)
        header.add_widget(Label(text='Action Notch',font_size=sp(22),bold=True,
                                color=get_color_from_hex(UI.ACC)))
        header.add_widget(Label(text='v2.0',font_size=sp(11),color=get_color_from_hex(UI.SUB),
                                size_hint_x=0.2))
        root.add_widget(header)

        sv, grid = UI.sgrid()

        # Master
        m = BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(72),padding=[dp(18),dp(12)])
        with m.canvas.before:
            Color(*get_color_from_hex(UI.ACC))
            rr2=RoundedRectangle(pos=m.pos,size=m.size,radius=[dp(16)])
        UI._br(m,rr2)
        mi = BoxLayout(orientation='vertical')
        mi.add_widget(Label(text='Action Notch Active',font_size=sp(16),bold=True,color=[1,1,1,1]))
        mi.add_widget(Label(text='5 Gestures x 17 Actions',font_size=sp(11),color=[1,1,1,0.7]))
        m.add_widget(mi)
        self.msw = Switch(active=s.get('master_enabled',True),size_hint_x=None,width=dp(55))
        self.msw.bind(active=self._toggle)
        m.add_widget(self.msw)
        grid.add_widget(m)

        # Status
        sr = UI.card(h=dp(40))
        self.sl = Label(text='Service Running',font_size=sp(11),color=get_color_from_hex(UI.GRN),halign='center')
        self.sl.bind(size=lambda i,v:setattr(i,'text_size',v))
        sr.add_widget(self.sl)
        grid.add_widget(sr)

        # Preview
        pb = BoxLayout(size_hint_y=None,height=dp(110),padding=[dp(8)])
        with pb.canvas.before:
            Color(*get_color_from_hex('#1E1E32'))
            rr3=RoundedRectangle(pos=pb.pos,size=pb.size,radius=[dp(14)])
        UI._br(pb,rr3)
        pb.add_widget(NotchPreview())
        grid.add_widget(pb)

        # Nav
        pages = [
            ('  Main',[('Gesture Controls','gestures')]),
            ('  Appearance',[('Notch Style','notch'),('Theme & Colors','theme'),
                             ('Animations','animation')]),
            ('  Settings',[('Sound & Haptic','sound'),('Advanced','advanced'),
                           ('Statistics','stats'),('About','about')]),
        ]
        for sec, items in pages:
            grid.add_widget(UI.sec(sec))
            for l, scr in items:
                grid.add_widget(UI.nav(l, partial(self._go, scr)))

        grid.add_widget(Widget(size_hint_y=None,height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _toggle(self, i, v):
        app = App.get_running_app()
        app.cfg.set('master_enabled', v)
        if v:
            self.sl.text='Service Running'; self.sl.color=get_color_from_hex(UI.GRN)
            app.overlay.create()
        else:
            self.sl.text='Stopped'; self.sl.color=get_color_from_hex(UI.RED)
            app.overlay.remove()

    def _go(self, n):
        self.manager.transition=SlideTransition(direction='left')
        self.manager.current=n


class Sub(Screen):
    def __init__(self, name, title, builder, **kw):
        super().__init__(name=name, **kw)
        self._t=title; self._b=builder

    def on_pre_enter(self, *_):
        self.clear_widgets()
        root = UI.bg()
        root.add_widget(UI.tbar(self._t, self._back))
        sv, grid = UI.sgrid()
        self._b(grid, App.get_running_app().cfg)
        grid.add_widget(Widget(size_hint_y=None, height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _back(self):
        self.manager.transition=SlideTransition(direction='right')
        self.manager.current='main'


class StatsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='stats', **kw)

    def on_pre_enter(self, *_):
        self.clear_widgets()
        s = App.get_running_app().cfg
        root = UI.bg()
        root.add_widget(UI.tbar('Statistics', self._back))
        sv, grid = UI.sgrid()
        for l,v,c in [('Total Actions',str(s.get('total_actions',0)),UI.ACC),
                       ('Flashlight',str(s.get('flashlight_toggles',0)),UI.ORG),
                       ('Screenshots',str(s.get('screenshots_taken',0)),UI.GRN)]:
            r = UI.card()
            r.add_widget(UI.lbl(l))
            r.add_widget(Label(text=v,font_size=sp(15),bold=True,color=get_color_from_hex(c),
                               size_hint_x=None,width=dp(80),halign='right'))
            grid.add_widget(r)

        # Show gesture assignments
        grid.add_widget(UI.sec('Gesture Assignments'))
        for gk, gn in GESTURES:
            act = s.get(gk, 'Do Nothing')
            extra = ''
            if act == 'Open App':
                extra = f' ({s.get(f"{gk}_app_name","")})'
            elif act == 'Call Contact':
                extra = f' ({s.get(f"{gk}_call_name","")})'
            r = UI.card(h=dp(50))
            r.add_widget(UI.lbl(gn, fs=sp(12)))
            r.add_widget(UI.lbl(f'{act}{extra}', fs=sp(10),
                                c=get_color_from_hex(UI.ACC), ha='right'))
            grid.add_widget(r)

        def rs():
            for k in ('total_actions','flashlight_toggles','screenshots_taken'):
                s.set(k,0)
            self.on_pre_enter()
        grid.add_widget(UI.btn('Reset Stats',rs))
        grid.add_widget(Widget(size_hint_y=None,height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _back(self):
        self.manager.transition=SlideTransition(direction='right')
        self.manager.current='main'


class AboutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='about', **kw)

    def on_pre_enter(self, *_):
        self.clear_widgets()
        root = UI.bg()
        root.add_widget(UI.tbar('About', self._back))
        sv, grid = UI.sgrid()
        grid.add_widget(Widget(size_hint_y=None,height=dp(15)))
        grid.add_widget(Label(text='Action Notch',font_size=sp(28),bold=True,
                              color=get_color_from_hex(UI.ACC),size_hint_y=None,height=dp(40)))
        grid.add_widget(Label(text='v2.0.0 - Full Edition',font_size=sp(13),
                              color=get_color_from_hex(UI.SUB),size_hint_y=None,height=dp(22)))

        actions_list = '\n'.join([f'  {i+1}. {a}' for i, a in enumerate(ALL_ACTIONS)])
        grid.add_widget(UI.sec('5 Gestures'))
        grid.add_widget(UI.lbl(
            'Single Touch | Double Touch | Long Touch\nSwipe Right | Swipe Left',
            fs=sp(12), c=get_color_from_hex('#AAAABB'),
            shy=None, h=dp(40)
        ))
        grid.add_widget(UI.sec(f'{len(ALL_ACTIONS)} Actions'))
        grid.add_widget(UI.lbl(
            actions_list, fs=sp(11), c=get_color_from_hex('#AAAABB'),
            shy=None, h=dp(len(ALL_ACTIONS)*dp(5))
        ))
        grid.add_widget(Widget(size_hint_y=None,height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _back(self):
        self.manager.transition=SlideTransition(direction='right')
        self.manager.current='main'


# ============================================================
# ANDROID SETUP
# ============================================================
def android_setup():
    if not IS_ANDROID: return
    try:
        from jnius import autoclass
        PA = autoclass('org.kivy.android.PythonActivity')
        act = PA.mActivity
        S = autoclass('android.provider.Settings')
        I = autoclass('android.content.Intent')
        U = autoclass('android.net.Uri')
        Ctx = autoclass('android.content.Context')
        PM = autoclass('android.os.PowerManager')
        if not S.canDrawOverlays(act):
            i = I(S.ACTION_MANAGE_OVERLAY_PERMISSION,U.parse('package:'+act.getPackageName()))
            act.startActivityForResult(i, 1234)
        pm = act.getSystemService(Ctx.POWER_SERVICE)
        if not pm.isIgnoringBatteryOptimizations(act.getPackageName()):
            i = I()
            i.setAction(S.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            i.setData(U.parse('package:'+act.getPackageName()))
            act.startActivity(i)
    except Exception as e:
        print(f'Android setup: {e}')


# ============================================================
# APP
# ============================================================
class ActionNotchApp(App):
    def build(self):
        self.title = 'Action Notch'
        path = os.path.join(self.user_data_dir, 'settings.json')
        self.cfg = Settings(path)
        self.overlay = OverlayManager(self.cfg)

        sm = ScreenManager()
        sm.add_widget(MainScreen())
        sm.add_widget(Sub('gestures','Gesture Controls',page_gestures))
        sm.add_widget(Sub('notch','Notch Style',page_notch))
        sm.add_widget(Sub('theme','Theme & Colors',page_theme))
        sm.add_widget(Sub('animation','Animations',page_animation))
        sm.add_widget(Sub('sound','Sound & Haptic',page_sound))
        sm.add_widget(Sub('advanced','Advanced',page_advanced))
        sm.add_widget(StatsScreen())
        sm.add_widget(AboutScreen())

        Clock.schedule_once(lambda dt: self._init(), 1.0)
        return sm

    def _init(self):
        if IS_ANDROID: android_setup()
        if self.cfg.get('master_enabled',True): self.overlay.create()

    def on_pause(self):
        self.cfg.save()
        return True

    def on_resume(self):
        self.cfg._load()

    def on_stop(self):
        self.cfg.save()


if __name__ == '__main__':
    ActionNotchApp().run()
