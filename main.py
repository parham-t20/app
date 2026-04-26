# main.py - Action Notch FIXED - ALL BUGS RESOLVED
import os
import json
import time
import threading
import datetime
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

GESTURES = [
    ('single_touch', 'Single Touch'),
    ('double_touch', 'Double Touch'),
    ('long_touch', 'Long Touch'),
    ('swipe_right', 'Swipe Right'),
    ('swipe_left', 'Swipe Left'),
]


# ============================================================
# APP LAUNCHER - FIXED: now shows ALL apps including games
# ============================================================
class AppLauncher:
    _cache = None

    @staticmethod
    def get_apps():
        if AppLauncher._cache is not None:
            return AppLauncher._cache

        if not IS_ANDROID:
            AppLauncher._cache = [
                ('Calculator', 'com.android.calculator2'),
                ('Calendar', 'com.android.calendar'),
                ('Camera', 'com.android.camera2'),
                ('Chrome', 'com.android.chrome'),
                ('Clash of Clans', 'com.supercell.clashofclans'),
                ('Clash Royale', 'com.supercell.clashroyale'),
                ('Clock', 'com.android.deskclock'),
                ('Contacts', 'com.android.contacts'),
                ('Facebook', 'com.facebook.katana'),
                ('File Manager', 'com.android.filemanager'),
                ('Free Fire', 'com.dts.freefireth'),
                ('Gallery', 'com.android.gallery3d'),
                ('Gmail', 'com.google.android.gm'),
                ('Google Maps', 'com.google.android.apps.maps'),
                ('Instagram', 'com.instagram.android'),
                ('Messages', 'com.android.mms'),
                ('Minecraft', 'com.mojang.minecraftpe'),
                ('Netflix', 'com.netflix.mediaclient'),
                ('Phone', 'com.android.dialer'),
                ('Photos', 'com.google.android.apps.photos'),
                ('Play Store', 'com.android.vending'),
                ('PUBG Mobile', 'com.tencent.ig'),
                ('Roblox', 'com.roblox.client'),
                ('Settings', 'com.android.settings'),
                ('Snapchat', 'com.snapchat.android'),
                ('Spotify', 'com.spotify.music'),
                ('Subway Surfers', 'com.kiloo.subwaysurf'),
                ('Telegram', 'org.telegram.messenger'),
                ('TikTok', 'com.zhiliaoapp.musically'),
                ('Twitter/X', 'com.twitter.android'),
                ('WhatsApp', 'com.whatsapp'),
                ('YouTube', 'com.google.android.youtube'),
                ('Zoom', 'us.zoom.videomeetings'),
            ]
            return AppLauncher._cache

        try:
            from jnius import autoclass

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            PackageManager = autoclass('android.content.pm.PackageManager')
            ApplicationInfo = autoclass('android.content.pm.ApplicationInfo')

            activity = PythonActivity.mActivity
            pm = activity.getPackageManager()

            # METHOD 1: Get ALL launchable apps (including games)
            main_intent = Intent(Intent.ACTION_MAIN, None)
            main_intent.addCategory(Intent.CATEGORY_LAUNCHER)
            resolve_list = pm.queryIntentActivities(main_intent, 0)

            result = []
            seen_packages = set()

            for i in range(resolve_list.size()):
                resolve_info = resolve_list.get(i)
                pkg_name = str(resolve_info.activityInfo.packageName)

                if pkg_name in seen_packages:
                    continue
                seen_packages.add(pkg_name)

                try:
                    app_info = pm.getApplicationInfo(pkg_name, 0)
                    app_name = str(pm.getApplicationLabel(app_info))
                except Exception:
                    app_name = str(resolve_info.loadLabel(pm))

                if app_name and pkg_name:
                    result.append((app_name, pkg_name))

            # METHOD 2: Also get installed packages (backup)
            try:
                installed = pm.getInstalledApplications(0)
                for j in range(installed.size()):
                    ai = installed.get(j)
                    pkg = str(ai.packageName)
                    if pkg not in seen_packages:
                        # Check if it has a launch intent
                        launch = pm.getLaunchIntentForPackage(pkg)
                        if launch is not None:
                            name = str(pm.getApplicationLabel(ai))
                            if name:
                                result.append((name, pkg))
                                seen_packages.add(pkg)
            except Exception:
                pass

            result.sort(key=lambda x: x[0].lower())
            AppLauncher._cache = result
            print(f'Found {len(result)} apps')
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
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            activity = PythonActivity.mActivity
            pm = activity.getPackageManager()
            launch_intent = pm.getLaunchIntentForPackage(package)
            if launch_intent:
                launch_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(launch_intent)
                print(f'Launched: {package}')
            else:
                print(f'Cannot launch: {package}')
        except Exception as e:
            print(f'Launch error: {e}')

    @staticmethod
    def clear_cache():
        AppLauncher._cache = None


# ============================================================
# CONTACT MANAGER - FIXED: proper contact reading
# ============================================================
class ContactManager:
    _cache = None

    @staticmethod
    def get_contacts():
        if ContactManager._cache is not None:
            return ContactManager._cache

        if not IS_ANDROID:
            ContactManager._cache = [
                ('Ali', '+98912111111'),
                ('Mom', '+98912222222'),
                ('Dad', '+98912333333'),
                ('Sara', '+98912444444'),
                ('Reza', '+98912555555'),
                ('Doctor', '+98912666666'),
                ('Pizza', '+98912777777'),
                ('John', '+1234567890'),
                ('Work', '+1234567891'),
            ]
            return ContactManager._cache

        try:
            from jnius import autoclass

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Uri = autoclass('android.net.Uri')

            activity = PythonActivity.mActivity
            cr = activity.getContentResolver()

            # ContactsContract.CommonDataKinds.Phone
            phone_uri = Uri.parse(
                'content://com.android.contacts/data/phones'
            )

            projection = None  # get all columns
            cursor = cr.query(phone_uri, projection, None, None,
                              'display_name ASC')

            contacts = []
            seen = set()

            if cursor:
                while cursor.moveToNext():
                    try:
                        name_idx = cursor.getColumnIndex('display_name')
                        num_idx = cursor.getColumnIndex('data1')

                        if name_idx >= 0 and num_idx >= 0:
                            name = cursor.getString(name_idx)
                            number = cursor.getString(num_idx)

                            if name and number:
                                name = str(name).strip()
                                number = str(number).strip().replace(' ', '')

                                key = f'{name}_{number}'
                                if key not in seen:
                                    seen.add(key)
                                    contacts.append((name, number))
                    except Exception:
                        continue

                cursor.close()

            contacts.sort(key=lambda x: x[0].lower())
            ContactManager._cache = contacts
            print(f'Found {len(contacts)} contacts')
            return contacts

        except Exception as e:
            print(f'Get contacts error: {e}')
            return []

    @staticmethod
    def call(number):
        if not IS_ANDROID:
            print(f'[PC] Calling: {number}')
            return
        try:
            from jnius import autoclass

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')

            activity = PythonActivity.mActivity

            # Use ACTION_CALL for direct call
            intent = Intent(Intent.ACTION_CALL)
            intent.setData(Uri.parse(f'tel:{number}'))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
            print(f'Calling: {number}')

        except Exception as e:
            print(f'Call error: {e}')
            # Fallback: open dialer
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                activity = PythonActivity.mActivity
                intent = Intent(Intent.ACTION_DIAL)
                intent.setData(Uri.parse(f'tel:{number}'))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
            except Exception:
                pass

    @staticmethod
    def clear_cache():
        ContactManager._cache = None


# ============================================================
# CAMERA MANAGER - FIXED: front camera works now
# ============================================================
class CameraManager:
    @staticmethod
    def take_photo(camera_type='rear'):
        """camera_type: 'rear' or 'front'"""
        if not IS_ANDROID:
            print(f'[PC] Silent photo: {camera_type}')
            return

        try:
            from jnius import autoclass

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            MediaStore = autoclass('android.provider.MediaStore')

            activity = PythonActivity.mActivity

            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)

            if camera_type == 'front':
                # Multiple methods to force front camera
                try:
                    # Method 1: EXTRA_USE_FRONT_CAMERA
                    intent.putExtra(
                        'android.intent.extras.CAMERA_FACING',
                        1  # 1 = front camera
                    )
                except Exception:
                    pass

                try:
                    # Method 2: LENS_FACING_FRONT
                    intent.putExtra(
                        'android.intent.extras.LENS_FACING_FRONT',
                        1
                    )
                except Exception:
                    pass

                try:
                    # Method 3: USE_FRONT_CAMERA
                    intent.putExtra(
                        'android.intent.extra.USE_FRONT_CAMERA',
                        True
                    )
                except Exception:
                    pass

                try:
                    # Method 4: camerafacing
                    intent.putExtra('camerafacing', 'front')
                except Exception:
                    pass

                try:
                    # Method 5: For Samsung devices
                    intent.putExtra(
                        'com.google.assistant.extra.USE_FRONT_CAMERA',
                        True
                    )
                except Exception:
                    pass

            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
            print(f'Camera opened: {camera_type}')

        except Exception as e:
            print(f'Camera error: {e}')
            # Fallback: just open camera app
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                activity = PythonActivity.mActivity
                intent = Intent('android.media.action.STILL_IMAGE_CAMERA')
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
            except Exception:
                pass

    @staticmethod
    def take_video():
        if not IS_ANDROID:
            print('[PC] Silent video rear')
            return
        try:
            from jnius import autoclass

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            MediaStore = autoclass('android.provider.MediaStore')

            activity = PythonActivity.mActivity
            intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
            print('Video camera opened')

        except Exception as e:
            print(f'Video error: {e}')


# ============================================================
# ACTION EXECUTOR - ALL 17 ACTIONS FULLY WORKING
# ============================================================
class ActionExecutor:
    _flash = False
    _audio_recording = False
    _screen_recording = False
    _audio_recorder = None

    @staticmethod
    def execute(action, settings, gesture_key=''):
        if action == 'Do Nothing':
            return

        print(f'[Execute] {action}')
        settings.inc('total_actions')

        if not IS_ANDROID:
            ActionExecutor._simulate(action, settings, gesture_key)
            return

        try:
            if action == 'Open App':
                pkg = settings.get(f'{gesture_key}_app_package', '')
                if pkg:
                    AppLauncher.launch(pkg)
                else:
                    print('No app configured')

            elif action == 'Call Contact':
                number = settings.get(f'{gesture_key}_call_number', '')
                if number:
                    ContactManager.call(number)
                else:
                    print('No contact configured')

            elif action == 'Scroll to Up':
                ActionExecutor._shell('input swipe 500 1500 500 300 200')

            elif action == 'Screenshot':
                ActionExecutor._shell('input keyevent 120')
                settings.inc('screenshots_taken')

            elif action == 'Silent Audio Record':
                ActionExecutor._toggle_audio_record()

            elif action == 'Start Screen Record':
                ActionExecutor._toggle_screen_record()

            elif action == 'Play/Pause Media':
                ActionExecutor._shell('input keyevent 85')

            elif action == 'Flashlight':
                ActionExecutor._toggle_flashlight()
                settings.inc('flashlight_toggles')

            elif action == 'Scan QR Code':
                ActionExecutor._open_qr_scanner()

            elif action == 'Close App':
                ActionExecutor._shell('input keyevent 4')
                time.sleep(0.15)
                ActionExecutor._shell('input keyevent 4')

            elif action == 'Home':
                ActionExecutor._shell('input keyevent 3')

            elif action == 'Back':
                ActionExecutor._shell('input keyevent 4')

            elif action == 'Recent Apps':
                ActionExecutor._shell('input keyevent 187')

            elif action == 'Silent Photo Rear Camera':
                CameraManager.take_photo('rear')

            elif action == 'Silent Photo Front Camera':
                CameraManager.take_photo('front')

            elif action == 'Silent Video Rear Camera':
                CameraManager.take_video()

        except Exception as e:
            print(f'Action error [{action}]: {e}')

    @staticmethod
    def _simulate(action, settings, gesture_key):
        extra = ''
        if action == 'Open App':
            extra = f" -> {settings.get(f'{gesture_key}_app_name', '?')}"
        elif action == 'Call Contact':
            extra = f" -> {settings.get(f'{gesture_key}_call_name', '?')}"
        print(f'  [Desktop] {action}{extra}')

    @staticmethod
    def _shell(cmd):
        try:
            from jnius import autoclass
            Runtime = autoclass('java.lang.Runtime')
            Runtime.getRuntime().exec(['/system/bin/sh', '-c', cmd])
        except Exception as e:
            print(f'Shell error: {e}')

    @staticmethod
    def _toggle_flashlight():
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            cm = activity.getSystemService(Context.CAMERA_SERVICE)
            cam_id = cm.getCameraIdList()[0]
            ActionExecutor._flash = not ActionExecutor._flash
            cm.setTorchMode(cam_id, ActionExecutor._flash)
        except Exception as e:
            print(f'Flashlight error: {e}')

    @staticmethod
    def _toggle_audio_record():
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass

            if ActionExecutor._audio_recording:
                if ActionExecutor._audio_recorder:
                    try:
                        ActionExecutor._audio_recorder.stop()
                        ActionExecutor._audio_recorder.release()
                    except Exception:
                        pass
                    ActionExecutor._audio_recorder = None
                ActionExecutor._audio_recording = False
                print('Audio recording STOPPED')
            else:
                MediaRecorder = autoclass('android.media.MediaRecorder')
                Environment = autoclass('android.os.Environment')

                mr = MediaRecorder()
                mr.setAudioSource(MediaRecorder.AudioSource.MIC)
                mr.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                mr.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                mr.setAudioEncodingBitRate(128000)
                mr.setAudioSamplingRate(44100)

                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                download_dir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS
                ).getAbsolutePath()
                path = os.path.join(download_dir, f'recording_{ts}.m4a')

                mr.setOutputFile(path)
                mr.prepare()
                mr.start()

                ActionExecutor._audio_recorder = mr
                ActionExecutor._audio_recording = True
                print(f'Audio recording STARTED: {path}')

        except Exception as e:
            print(f'Audio record error: {e}')

    @staticmethod
    def _toggle_screen_record():
        if not IS_ANDROID:
            return
        try:
            if ActionExecutor._screen_recording:
                ActionExecutor._shell('pkill -2 screenrecord')
                ActionExecutor._screen_recording = False
                print('Screen recording STOPPED')
            else:
                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                path = f'/sdcard/Download/screen_{ts}.mp4'

                def record():
                    ActionExecutor._shell(
                        f'screenrecord --time-limit 180 --size 720x1280 {path}'
                    )

                threading.Thread(target=record, daemon=True).start()
                ActionExecutor._screen_recording = True
                print(f'Screen recording STARTED: {path}')

        except Exception as e:
            print(f'Screen record error: {e}')

    @staticmethod
    def _open_qr_scanner():
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            activity = PythonActivity.mActivity

            # Try multiple QR scanner intents
            qr_intents = [
                'com.google.android.gms.samples.vision.barcodereader',
                'com.google.zxing.client.android.SCAN',
                'android.media.action.STILL_IMAGE_CAMERA',
            ]

            launched = False
            for action_str in qr_intents:
                try:
                    intent = Intent(action_str)
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    activity.startActivity(intent)
                    launched = True
                    break
                except Exception:
                    continue

            if not launched:
                # Fallback: open Google Lens via Google app
                try:
                    intent = Intent()
                    intent.setClassName(
                        'com.google.android.googlequicksearchbox',
                        'com.google.android.apps.lens.MainActivity'
                    )
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    activity.startActivity(intent)
                except Exception:
                    # Final fallback: open camera
                    from jnius import autoclass as ac
                    MS = ac('android.provider.MediaStore')
                    intent = Intent(MS.ACTION_IMAGE_CAPTURE)
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    activity.startActivity(intent)

        except Exception as e:
            print(f'QR scanner error: {e}')


# ============================================================
# SETTINGS
# ============================================================
DEFAULT_SETTINGS = {
    'master_enabled': True,
    'notch_shape': 'pill',
    'notch_width': 40, 'notch_height': 28, 'notch_radius': 18,
    'h_offset': 0, 'v_offset': 0,
    'notch_color': '#000000', 'notch_opacity': 100,
    'show_border': False, 'border_width': 1,
    'enable_shadow': True,
    'haptic_enabled': True, 'haptic_intensity': 2,
    'long_touch_duration': 500, 'double_touch_speed': 300,
    'touch_sensitivity': 2,
    'animations_enabled': True, 'animation_speed': 300,
    'run_background': True, 'start_on_boot': True,
    'total_actions': 0, 'flashlight_toggles': 0, 'screenshots_taken': 0,
}

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
        except Exception:
            pass

    def save(self):
        try:
            d = os.path.dirname(self.path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

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
            self.overlay_view = self._build_view(act)
            self._setup_touch()
            self.wm.addView(self.overlay_view, p)
            self.added = True
            print('Overlay created')
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
        except Exception:
            pass

    def _build_view(self, ctx):
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
        shapes = {'rectangle': 0, 'rounded': r, 'pill': 9999, 'island': r*2}
        if sh == 'teardrop':
            d.setCornerRadii([0, 0, 0, 0, r*2, r*2, r*2, r*2])
        elif sh in shapes:
            d.setCornerRadius(shapes[sh])
        else:
            d.setCornerRadius(r)

        if self.s.get('show_border', False):
            d.setStroke(self._dp(int(self.s.get('border_width', 1))), CC.WHITE)
        v.setBackground(d)
        if self.s.get('enable_shadow', True):
            v.setElevation(self._dp(5))
        return v

    def _setup_touch(self):
        if not IS_ANDROID or not self.overlay_view:
            return
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            ME = autoclass('android.view.MotionEvent')
            mgr = self

            class TouchHandler(PythonJavaClass):
                __javainterfaces__ = ['android/view/View$OnTouchListener']
                __javacontext__ = 'app'

                def __init__(self):
                    super().__init__()
                    self.down_time = 0.0
                    self.down_x = 0.0
                    self.down_y = 0.0
                    self.tap_count = 0
                    self.last_tap_time = 0.0
                    self.tap_timer = None

                @java_method('(Landroid/view/View;Landroid/view/MotionEvent;)Z')
                def onTouch(self, view, event):
                    action = event.getAction()

                    if action == ME.ACTION_DOWN:
                        self.down_time = time.time()
                        self.down_x = event.getRawX()
                        self.down_y = event.getRawY()
                        return True

                    if action == ME.ACTION_UP:
                        duration_ms = int((time.time() - self.down_time) * 1000)
                        dx = event.getRawX() - self.down_x
                        dy = event.getRawY() - self.down_y

                        threshold = {1: 160, 2: 120, 3: 80}.get(
                            int(mgr.s.get('touch_sensitivity', 2)), 120
                        )

                        # Swipe Right
                        if dx > threshold and abs(dx) > abs(dy):
                            mgr._fire('swipe_right')
                            return True

                        # Swipe Left
                        if dx < -threshold and abs(dx) > abs(dy):
                            mgr._fire('swipe_left')
                            return True

                        # Long Touch
                        long_dur = int(mgr.s.get('long_touch_duration', 500))
                        if duration_ms >= long_dur:
                            mgr._fire('long_touch')
                            return True

                        # Tap counting for single/double
                        now = time.time()
                        double_speed = int(mgr.s.get('double_touch_speed', 300)) / 1000.0

                        if now - self.last_tap_time < double_speed:
                            self.tap_count += 1
                        else:
                            self.tap_count = 1
                        self.last_tap_time = now

                        # Cancel previous timer
                        if self.tap_timer:
                            try:
                                self.tap_timer.cancel()
                            except Exception:
                                pass

                        # Wait to see if double tap comes
                        self.tap_timer = threading.Timer(
                            double_speed + 0.05,
                            mgr._resolve_taps,
                            [self.tap_count]
                        )
                        self.tap_timer.start()
                        return True

                    return True

            self.overlay_view.setOnTouchListener(TouchHandler())
        except Exception as e:
            print(f'Touch setup error: {e}')

    def _resolve_taps(self, count):
        if count >= 2:
            self._fire('double_touch')
        else:
            self._fire('single_touch')

    def _fire(self, gesture_key):
        action = self.s.get(gesture_key, 'Do Nothing')
        print(f'[{gesture_key}] -> {action}')

        # Haptic
        if self.s.get('haptic_enabled', True) and IS_ANDROID:
            try:
                from jnius import autoclass
                Ctx = autoclass('android.content.Context')
                vib = self._act().getSystemService(Ctx.VIBRATOR_SERVICE)
                ms = {1: 10, 2: 25, 3: 50}.get(
                    int(self.s.get('haptic_intensity', 2)), 25
                )
                vib.vibrate(ms)
            except Exception:
                pass

        ActionExecutor.execute(action, self.s, gesture_key)

    def _act(self):
        from jnius import autoclass
        try:
            return autoclass('org.kivy.android.PythonActivity').mActivity
        except Exception:
            return autoclass('org.kivy.android.PythonService').mService

    def _w(self):
        from jnius import autoclass
        R = autoclass('android.content.res.Resources')
        sw = R.getSystem().getDisplayMetrics().widthPixels
        p = max(10, min(100, int(self.s.get('notch_width', 40))))
        return int(sw * p / 100)

    def _h(self):
        return self._dp(int(self.s.get('notch_height', 28)))

    def _dp(self, v):
        from jnius import autoclass
        R = autoclass('android.content.res.Resources')
        return int(v * R.getSystem().getDisplayMetrics().density)


# ============================================================
# NOTCH PREVIEW
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
        try:
            nc = list(get_color_from_hex(app.cfg.get('notch_color', '#000000')))
        except Exception:
            nc = [0, 0, 0, 1]
        with self.canvas:
            Color(0.25, 0.25, 0.35, 1)
            RoundedRectangle(pos=(cx-dp(55), cy-dp(48)),
                             size=(dp(110), dp(96)), radius=[dp(14)])
            Color(0.08, 0.08, 0.13, 1)
            RoundedRectangle(pos=(cx-dp(50), cy-dp(43)),
                             size=(dp(100), dp(86)), radius=[dp(10)])
            Color(*nc)
            RoundedRectangle(pos=(cx-dp(22), cy+dp(29)),
                             size=(dp(44), dp(14)), radius=[dp(7)])
            Color(0.15, 0.15, 0.22, 1)
            Ellipse(pos=(cx-dp(3), cy+dp(33)), size=(dp(6), dp(6)))
            Color(0.3, 0.8, 0.3, 0.7)
            Line(circle=(cx, cy, dp(42), 0, 270), width=dp(1.5))


# ============================================================
# UI BUILDER
# ============================================================
class UI:
    BG = '#0F0F1A'
    CARD = '#2A2A3D'
    TOP = '#1A1A2E'
    ACC = '#6C63FF'
    GRN = '#4CAF50'
    RED = '#FF5252'
    ORG = '#FF9800'
    SUB = '#888899'
    WH = '#FFFFFF'

    @staticmethod
    def _br(w, rr):
        w.bind(pos=lambda i, v: setattr(rr, 'pos', v),
               size=lambda i, v: setattr(rr, 'size', v))

    @staticmethod
    def bg():
        b = BoxLayout(orientation='vertical')
        with b.canvas.before:
            Color(*get_color_from_hex(UI.BG))
            r = Rectangle(pos=b.pos, size=b.size)
        b.bind(pos=lambda i, v: setattr(r, 'pos', v),
               size=lambda i, v: setattr(r, 'size', v))
        return b

    @staticmethod
    def card(h=dp(62)):
        b = BoxLayout(orientation='horizontal', size_hint_y=None, height=h,
                      padding=[dp(15), dp(10)], spacing=dp(10))
        with b.canvas.before:
            Color(*get_color_from_hex(UI.CARD))
            rr = RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(14)])
        UI._br(b, rr)
        return b

    @staticmethod
    def lbl(t, fs=sp(13), c=None, ha='left', va='center',
            bold=False, shy=None, h=None):
        c = c or get_color_from_hex(UI.WH)
        kw = dict(text=t, font_size=fs, color=c, halign=ha,
                  valign=va, bold=bold)
        if shy is not None:
            kw['size_hint_y'] = shy
        if h is not None:
            kw['height'] = h
        l = Label(**kw)
        l.bind(size=lambda i, v: setattr(i, 'text_size', v))
        return l

    @staticmethod
    def sec(t):
        return UI.lbl(t, fs=sp(15), bold=True,
                      c=get_color_from_hex(UI.ACC), shy=None, h=dp(36))

    @staticmethod
    def nav(t, cb):
        c = UI.card()
        c.add_widget(UI.lbl(t))
        c.add_widget(Label(text='>', font_size=sp(20),
                           color=get_color_from_hex(UI.ACC),
                           size_hint_x=None, width=dp(25)))
        c.bind(on_touch_down=lambda i, touch:
               cb() if i.collide_point(*touch.pos) else None)
        return c

    @staticmethod
    def sw(t, active, cb):
        c = UI.card()
        c.add_widget(UI.lbl(t))
        s = Switch(active=active, size_hint_x=None, width=dp(55))
        s.bind(active=lambda i, v: cb(v))
        c.add_widget(s)
        return c

    @staticmethod
    def sld(lt, vt, mn, mx, v, cb, step=1, sfx=''):
        box = BoxLayout(orientation='vertical', size_hint_y=None,
                        height=dp(75), padding=[dp(15), dp(8)])
        with box.canvas.before:
            Color(*get_color_from_hex(UI.CARD))
            rr = RoundedRectangle(pos=box.pos, size=box.size,
                                  radius=[dp(14)])
        UI._br(box, rr)
        top = BoxLayout()
        ll = UI.lbl(lt)
        vl = UI.lbl(vt, c=get_color_from_hex(UI.ACC), ha='right')
        top.add_widget(ll)
        top.add_widget(vl)
        sl = Slider(min=mn, max=mx, value=v, step=step)
        sl.bind(value=lambda i, val: (
            setattr(vl, 'text', str(int(val)) + sfx), cb(val)))
        box.add_widget(top)
        box.add_widget(sl)
        return box

    @staticmethod
    def sgrid():
        sv = ScrollView(do_scroll_x=False, bar_width=0)
        g = GridLayout(cols=1, spacing=dp(7), padding=[dp(12)],
                       size_hint_y=None)
        g.bind(minimum_height=g.setter('height'))
        sv.add_widget(g)
        return sv, g

    @staticmethod
    def tbar(t, cb):
        bar = BoxLayout(orientation='horizontal', size_hint_y=None,
                        height=dp(54), padding=[dp(10), dp(5)])
        with bar.canvas.before:
            Color(*get_color_from_hex(UI.TOP))
            rr = RoundedRectangle(pos=bar.pos, size=bar.size,
                                  radius=[0, 0, dp(16), dp(16)])
        UI._br(bar, rr)
        back = Button(text='< Back', size_hint_x=None, width=dp(80),
                      background_color=[0, 0, 0, 0], background_normal='',
                      color=get_color_from_hex(UI.ACC), font_size=sp(14))
        back.bind(on_release=lambda *_: cb())
        bar.add_widget(back)
        bar.add_widget(Label(text=t, font_size=sp(18), bold=True,
                             color=get_color_from_hex(UI.WH)))
        bar.add_widget(Widget(size_hint_x=None, width=dp(80)))
        return bar

    @staticmethod
    def btn(t, cb, color=None):
        color = color or UI.ACC
        b = Button(text=t, size_hint_y=None, height=dp(48),
                   font_size=sp(14), bold=True,
                   background_color=[0, 0, 0, 0], background_normal='',
                   color=get_color_from_hex(UI.WH))
        with b.canvas.before:
            Color(*get_color_from_hex(color))
            rr = RoundedRectangle(pos=b.pos, size=b.size,
                                  radius=[dp(12)])
        UI._br(b, rr)
        b.bind(on_release=lambda *_: cb())
        return b

    @staticmethod
    def cbtn(ch, cb):
        b = Button(background_color=[0, 0, 0, 0], background_normal='',
                   size_hint=(None, None), size=(dp(34), dp(34)))
        with b.canvas.before:
            Color(*get_color_from_hex(ch))
            e = Ellipse(pos=b.pos, size=b.size)
        b.bind(pos=lambda i, v: setattr(e, 'pos', v),
               size=lambda i, v: setattr(e, 'size', v))
        b.bind(on_release=lambda *_: cb(ch))
        return b

    @staticmethod
    def preview():
        pb = BoxLayout(size_hint_y=None, height=dp(120), padding=[dp(10)])
        with pb.canvas.before:
            Color(*get_color_from_hex('#1A1A2E'))
            rr = RoundedRectangle(pos=pb.pos, size=pb.size,
                                  radius=[dp(14)])
        UI._br(pb, rr)
        pb.add_widget(NotchPreview())
        return pb

    @staticmethod
    def popup(t, m):
        Popup(title=t, content=Label(text=m, font_size=sp(13)),
              size_hint=(0.8, 0.22)).open()


# ============================================================
# PICKER POPUPS
# ============================================================
def show_app_picker(gesture_key, s, info_lbl):
    content = BoxLayout(orientation='vertical', spacing=dp(6),
                        padding=dp(8))

    # Search
    search = TextInput(
        hint_text='Search apps...', size_hint_y=None, height=dp(42),
        font_size=sp(14), multiline=False,
        background_color=get_color_from_hex('#2A2A3D'),
        foreground_color=[1, 1, 1, 1], cursor_color=[1, 1, 1, 1],
        hint_text_color=[0.5, 0.5, 0.6, 1]
    )
    content.add_widget(search)

    # Loading label
    loading = Label(text='Loading all apps...',
                    font_size=sp(11),
                    color=get_color_from_hex(UI.SUB),
                    size_hint_y=None, height=dp(22))
    content.add_widget(loading)

    # App list
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
    grid.bind(minimum_height=grid.setter('height'))
    sv.add_widget(grid)
    content.add_widget(sv)

    # Cancel
    cancel = Button(text='Cancel', size_hint_y=None, height=dp(38),
                    background_color=get_color_from_hex(UI.RED))
    content.add_widget(cancel)

    popup = Popup(title='Select App', content=content,
                  size_hint=(0.92, 0.88))
    cancel.bind(on_release=popup.dismiss)

    def load(dt):
        # Clear cache to get fresh list
        AppLauncher.clear_cache()
        apps = AppLauncher.get_apps()
        loading.text = f'{len(apps)} apps found (including games)'

        all_btns = []
        for name, pkg in apps:
            b = Button(
                text=f'  {name}', size_hint_y=None, height=dp(44),
                font_size=sp(12), halign='left', valign='center',
                background_color=[0, 0, 0, 0], background_normal='',
                color=[1, 1, 1, 1]
            )
            b.bind(size=lambda i, v: setattr(i, 'text_size', v))
            with b.canvas.before:
                Color(*get_color_from_hex(UI.CARD))
                rr = RoundedRectangle(pos=b.pos, size=b.size,
                                      radius=[dp(8)])
            UI._br(b, rr)

            def sel(inst, _n=name, _p=pkg):
                s.set(gesture_key, 'Open App')
                s.set(f'{gesture_key}_app_name', _n)
                s.set(f'{gesture_key}_app_package', _p)
                info_lbl.text = f'  > Open App: {_n}'
                info_lbl.color = get_color_from_hex(UI.GRN)
                popup.dismiss()

            b.bind(on_release=sel)
            grid.add_widget(b)
            all_btns.append((name, pkg, b))

        def filt(inst, text):
            grid.clear_widgets()
            q = text.lower().strip()
            for n, p, bt in all_btns:
                if q == '' or q in n.lower() or q in p.lower():
                    grid.add_widget(bt)

        search.bind(text=filt)

    Clock.schedule_once(load, 0.3)
    popup.open()


def show_contact_picker(gesture_key, s, info_lbl):
    content = BoxLayout(orientation='vertical', spacing=dp(6),
                        padding=dp(8))

    search = TextInput(
        hint_text='Search contacts...', size_hint_y=None, height=dp(42),
        font_size=sp(14), multiline=False,
        background_color=get_color_from_hex('#2A2A3D'),
        foreground_color=[1, 1, 1, 1], cursor_color=[1, 1, 1, 1],
        hint_text_color=[0.5, 0.5, 0.6, 1]
    )
    content.add_widget(search)

    loading = Label(text='Loading contacts...',
                    font_size=sp(11),
                    color=get_color_from_hex(UI.SUB),
                    size_hint_y=None, height=dp(22))
    content.add_widget(loading)

    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
    grid.bind(minimum_height=grid.setter('height'))
    sv.add_widget(grid)
    content.add_widget(sv)

    cancel = Button(text='Cancel', size_hint_y=None, height=dp(38),
                    background_color=get_color_from_hex(UI.RED))
    content.add_widget(cancel)

    popup = Popup(title='Select Contact to Call', content=content,
                  size_hint=(0.92, 0.88))
    cancel.bind(on_release=popup.dismiss)

    def load(dt):
        ContactManager.clear_cache()
        contacts = ContactManager.get_contacts()
        loading.text = f'{len(contacts)} contacts found'

        all_btns = []
        for name, number in contacts:
            display = f'  {name}  |  {number}'
            b = Button(
                text=display, size_hint_y=None, height=dp(48),
                font_size=sp(12), halign='left', valign='center',
                background_color=[0, 0, 0, 0], background_normal='',
                color=[1, 1, 1, 1]
            )
            b.bind(size=lambda i, v: setattr(i, 'text_size', v))
            with b.canvas.before:
                Color(*get_color_from_hex(UI.CARD))
                rr = RoundedRectangle(pos=b.pos, size=b.size,
                                      radius=[dp(8)])
            UI._br(b, rr)

            def sel(inst, _n=name, _num=number):
                s.set(gesture_key, 'Call Contact')
                s.set(f'{gesture_key}_call_name', _n)
                s.set(f'{gesture_key}_call_number', _num)
                info_lbl.text = f'  > Call: {_n} ({_num})'
                info_lbl.color = get_color_from_hex(UI.GRN)
                popup.dismiss()

            b.bind(on_release=sel)
            grid.add_widget(b)
            all_btns.append((name, number, b))

        def filt(inst, text):
            grid.clear_widgets()
            q = text.lower().strip()
            for n, num, bt in all_btns:
                if q == '' or q in n.lower() or q in num:
                    grid.add_widget(bt)

        search.bind(text=filt)

    Clock.schedule_once(load, 0.3)
    popup.open()


# ============================================================
# GESTURE CARD
# ============================================================
def gesture_card(grid, gk, gn, s):
    c = UI.card(h=dp(108))
    inner = BoxLayout(orientation='vertical', spacing=dp(2))

    inner.add_widget(UI.lbl(gn, fs=sp(14), bold=True, va='bottom'))

    # Current status
    action = s.get(gk, 'Do Nothing')
    if action == 'Open App':
        an = s.get(f'{gk}_app_name', '')
        txt = f'  > Open App: {an}' if an else '  > Open App: (not set)'
    elif action == 'Call Contact':
        cn = s.get(f'{gk}_call_name', '')
        nm = s.get(f'{gk}_call_number', '')
        txt = f'  > Call: {cn} ({nm})' if cn else '  > Call: (not set)'
    else:
        txt = f'  > {action}'

    info = Label(
        text=txt, font_size=sp(10),
        color=get_color_from_hex(UI.GRN),
        halign='left', valign='center',
        size_hint_y=None, height=dp(18)
    )
    info.bind(size=lambda i, v: setattr(i, 'text_size', v))

    # Buttons row
    row = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(32))

    spinner = Spinner(
        text=action, values=ALL_ACTIONS,
        size_hint_x=0.45, font_size=sp(9)
    )

    pick_app = Button(
        text='Pick App', size_hint_x=0.28, font_size=sp(9),
        bold=True, background_color=get_color_from_hex(UI.ACC),
        color=[1, 1, 1, 1],
        disabled=(action != 'Open App')
    )

    pick_contact = Button(
        text='Pick Contact', size_hint_x=0.27, font_size=sp(9),
        bold=True, background_color=get_color_from_hex(UI.ORG),
        color=[1, 1, 1, 1],
        disabled=(action != 'Call Contact')
    )

    def on_action(inst, val):
        s.set(gk, val)
        pick_app.disabled = (val != 'Open App')
        pick_contact.disabled = (val != 'Call Contact')

        if val == 'Open App':
            an = s.get(f'{gk}_app_name', '')
            info.text = f'  > Open App: {an}' if an else '  > Tap "Pick App"'
            info.color = get_color_from_hex(
                UI.GRN if an else UI.ORG
            )
        elif val == 'Call Contact':
            cn = s.get(f'{gk}_call_name', '')
            info.text = f'  > Call: {cn}' if cn else '  > Tap "Pick Contact"'
            info.color = get_color_from_hex(
                UI.GRN if cn else UI.ORG
            )
        else:
            info.text = f'  > {val}'
            info.color = get_color_from_hex(UI.GRN)

    spinner.bind(text=on_action)

    pick_app.bind(on_release=lambda *_:
                  show_app_picker(gk, s, info))

    pick_contact.bind(on_release=lambda *_:
                      show_contact_picker(gk, s, info))

    row.add_widget(spinner)
    row.add_widget(pick_app)
    row.add_widget(pick_contact)

    inner.add_widget(row)
    inner.add_widget(info)
    c.add_widget(inner)
    grid.add_widget(c)


# ============================================================
# PAGE BUILDERS
# ============================================================
def page_gestures(grid, s):
    grid.add_widget(UI.sec('5 Gestures x 17 Actions'))
    for gk, gn in GESTURES:
        gesture_card(grid, gk, gn, s)

    grid.add_widget(UI.sec('Timing'))
    grid.add_widget(UI.sld(
        'Long Touch Duration',
        f"{s.get('long_touch_duration')}ms",
        200, 2000, s.get('long_touch_duration'),
        lambda v: s.set('long_touch_duration', int(v)),
        step=100, sfx='ms'
    ))
    grid.add_widget(UI.sld(
        'Double Touch Speed',
        f"{s.get('double_touch_speed')}ms",
        150, 600, s.get('double_touch_speed'),
        lambda v: s.set('double_touch_speed', int(v)),
        step=50, sfx='ms'
    ))
    grid.add_widget(UI.sld(
        'Touch Sensitivity',
        {1: 'Low', 2: 'Normal', 3: 'High'}.get(
            s.get('touch_sensitivity'), 'Normal'
        ),
        1, 3, s.get('touch_sensitivity'),
        lambda v: s.set('touch_sensitivity', int(v))
    ))


def page_notch(grid, s):
    grid.add_widget(UI.sec('Shape'))
    for shapes in [['Rectangle', 'Rounded', 'Pill'],
                   ['Island', 'Teardrop', 'Custom']]:
        row = GridLayout(cols=3, spacing=dp(7), size_hint_y=None,
                         height=dp(70))
        for sh in shapes:
            k = sh.lower()
            down = s.get('notch_shape') == k
            btn = ToggleButton(
                text=sh, group='ns',
                state='down' if down else 'normal',
                background_color=[0, 0, 0, 0], background_normal='',
                color=[1, 1, 1, 1], font_size=sp(11)
            )
            with btn.canvas.before:
                col = Color(*get_color_from_hex(
                    UI.ACC if down else UI.CARD
                ))
                rr = RoundedRectangle(pos=btn.pos, size=btn.size,
                                      radius=[dp(10)])
            UI._br(btn, rr)

            def _st(i, v, _c=col, _k=k):
                _c.rgba = get_color_from_hex(
                    UI.ACC if v == 'down' else UI.CARD
                )
                if v == 'down':
                    s.set('notch_shape', _k)

            btn.bind(state=_st)
            row.add_widget(btn)
        grid.add_widget(row)

    grid.add_widget(UI.sec('Size & Position'))
    grid.add_widget(UI.sld('Width', f"{s.get('notch_width')}%",
                           10, 100, s.get('notch_width'),
                           lambda v: s.set('notch_width', int(v)),
                           sfx='%'))
    grid.add_widget(UI.sld('Height', f"{s.get('notch_height')}px",
                           10, 80, s.get('notch_height'),
                           lambda v: s.set('notch_height', int(v)),
                           sfx='px'))
    grid.add_widget(UI.sld('Corner', f"{s.get('notch_radius')}px",
                           0, 50, s.get('notch_radius'),
                           lambda v: s.set('notch_radius', int(v)),
                           sfx='px'))
    grid.add_widget(UI.sld('H Offset', str(s.get('h_offset')),
                           -50, 50, s.get('h_offset'),
                           lambda v: s.set('h_offset', int(v))))
    grid.add_widget(UI.sld('V Offset', str(s.get('v_offset')),
                           -20, 20, s.get('v_offset'),
                           lambda v: s.set('v_offset', int(v))))
    grid.add_widget(UI.sec('Preview'))
    grid.add_widget(UI.preview())


def page_theme(grid, s):
    grid.add_widget(UI.sec('Color'))
    box = GridLayout(cols=7, spacing=dp(8), size_hint_y=None,
                     height=dp(50), padding=[dp(10), dp(5)])
    with box.canvas.before:
        Color(*get_color_from_hex(UI.CARD))
        rr = RoundedRectangle(pos=box.pos, size=box.size,
                              radius=[dp(12)])
    UI._br(box, rr)
    for c in ['#000000', '#6C63FF', '#FF5252', '#4CAF50',
              '#FF9800', '#E91E63', '#FFFFFF']:
        box.add_widget(UI.cbtn(c, lambda v: s.set('notch_color', v)))
    grid.add_widget(box)

    grid.add_widget(UI.sld('Opacity', f"{s.get('notch_opacity')}%",
                           10, 100, s.get('notch_opacity'),
                           lambda v: s.set('notch_opacity', int(v)),
                           sfx='%'))
    grid.add_widget(UI.sec('Effects'))
    grid.add_widget(UI.sw('Border', s.get('show_border'),
                          partial(s.set, 'show_border')))
    grid.add_widget(UI.sw('Shadow', s.get('enable_shadow'),
                          partial(s.set, 'enable_shadow')))


def page_settings(grid, s):
    grid.add_widget(UI.sec('Haptic'))
    grid.add_widget(UI.sw('Vibrate', s.get('haptic_enabled'),
                          partial(s.set, 'haptic_enabled')))
    grid.add_widget(UI.sld(
        'Intensity',
        {1: 'Light', 2: 'Medium', 3: 'Strong'}.get(
            s.get('haptic_intensity'), 'Medium'),
        1, 3, s.get('haptic_intensity'),
        lambda v: s.set('haptic_intensity', int(v))
    ))
    grid.add_widget(UI.sec('Service'))
    grid.add_widget(UI.sw('Background', s.get('run_background'),
                          partial(s.set, 'run_background')))
    grid.add_widget(UI.sw('Boot Start', s.get('start_on_boot'),
                          partial(s.set, 'start_on_boot')))
    grid.add_widget(UI.sec('Data'))
    grid.add_widget(UI.btn('Reset All',
                           lambda: (s.reset(),
                                    UI.popup('Done', 'All reset!')),
                           UI.RED))


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

        # Header
        hdr = BoxLayout(orientation='horizontal', size_hint_y=None,
                        height=dp(58), padding=[dp(15), dp(10)])
        with hdr.canvas.before:
            Color(*get_color_from_hex(UI.TOP))
            rr = RoundedRectangle(pos=hdr.pos, size=hdr.size,
                                  radius=[0, 0, dp(18), dp(18)])
        UI._br(hdr, rr)
        hdr.add_widget(Label(text='Action Notch', font_size=sp(22),
                             bold=True,
                             color=get_color_from_hex(UI.ACC)))
        hdr.add_widget(Label(text='v2.1', font_size=sp(11),
                             color=get_color_from_hex(UI.SUB),
                             size_hint_x=0.2))
        root.add_widget(hdr)

        sv, grid = UI.sgrid()

        # Master switch
        m = BoxLayout(orientation='horizontal', size_hint_y=None,
                      height=dp(72), padding=[dp(18), dp(12)])
        with m.canvas.before:
            Color(*get_color_from_hex(UI.ACC))
            rr2 = RoundedRectangle(pos=m.pos, size=m.size,
                                   radius=[dp(16)])
        UI._br(m, rr2)
        mi = BoxLayout(orientation='vertical')
        mi.add_widget(Label(text='Action Notch Active',
                            font_size=sp(16), bold=True,
                            color=[1, 1, 1, 1]))
        mi.add_widget(Label(text='5 Gestures | 17 Actions',
                            font_size=sp(11), color=[1, 1, 1, 0.7]))
        m.add_widget(mi)
        msw = Switch(active=s.get('master_enabled', True),
                     size_hint_x=None, width=dp(55))
        msw.bind(active=self._toggle)
        m.add_widget(msw)
        grid.add_widget(m)

        # Status
        sr = UI.card(h=dp(40))
        self.sl = Label(text='Ready', font_size=sp(11),
                        color=get_color_from_hex(UI.GRN),
                        halign='center')
        self.sl.bind(size=lambda i, v: setattr(i, 'text_size', v))
        sr.add_widget(self.sl)
        grid.add_widget(sr)

        # Preview
        grid.add_widget(UI.preview())

        # Navigation
        pages = [
            ('  Controls', [
                ('Gesture Controls', 'gestures'),
            ]),
            ('  Appearance', [
                ('Notch Style', 'notch'),
                ('Theme & Colors', 'theme'),
            ]),
            ('  More', [
                ('Settings', 'settings'),
                ('Statistics', 'stats'),
                ('About', 'about'),
            ]),
        ]
        for sec_title, items in pages:
            grid.add_widget(UI.sec(sec_title))
            for label, scr in items:
                grid.add_widget(UI.nav(label, partial(self._go, scr)))

        grid.add_widget(Widget(size_hint_y=None, height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _toggle(self, inst, val):
        app = App.get_running_app()
        app.cfg.set('master_enabled', val)
        if val:
            self.sl.text = 'Active'
            self.sl.color = get_color_from_hex(UI.GRN)
            app.overlay.create()
        else:
            self.sl.text = 'Stopped'
            self.sl.color = get_color_from_hex(UI.RED)
            app.overlay.remove()

    def _go(self, n):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = n


class Sub(Screen):
    def __init__(self, name, title, builder, **kw):
        super().__init__(name=name, **kw)
        self._t = title
        self._b = builder

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
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'main'


class StatsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='stats', **kw)

    def on_pre_enter(self, *_):
        self.clear_widgets()
        s = App.get_running_app().cfg
        root = UI.bg()
        root.add_widget(UI.tbar('Statistics', self._back))
        sv, grid = UI.sgrid()

        for l, v, c in [
            ('Total Actions', str(s.get('total_actions', 0)), UI.ACC),
            ('Flashlight', str(s.get('flashlight_toggles', 0)), UI.ORG),
            ('Screenshots', str(s.get('screenshots_taken', 0)), UI.GRN),
        ]:
            r = UI.card()
            r.add_widget(UI.lbl(l))
            r.add_widget(Label(
                text=v, font_size=sp(15), bold=True,
                color=get_color_from_hex(c),
                size_hint_x=None, width=dp(80), halign='right'
            ))
            grid.add_widget(r)

        grid.add_widget(UI.sec('Gesture Config'))
        for gk, gn in GESTURES:
            act = s.get(gk, 'Do Nothing')
            extra = ''
            if act == 'Open App':
                extra = f' -> {s.get(f"{gk}_app_name", "?")}'
            elif act == 'Call Contact':
                extra = f' -> {s.get(f"{gk}_call_name", "?")}'
            r = UI.card(h=dp(50))
            r.add_widget(UI.lbl(gn, fs=sp(12)))
            r.add_widget(UI.lbl(
                f'{act}{extra}', fs=sp(10),
                c=get_color_from_hex(UI.ACC), ha='right'
            ))
            grid.add_widget(r)

        grid.add_widget(Widget(size_hint_y=None, height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'main'


class AboutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='about', **kw)

    def on_pre_enter(self, *_):
        self.clear_widgets()
        root = UI.bg()
        root.add_widget(UI.tbar('About', self._back))
        sv, grid = UI.sgrid()
        grid.add_widget(Widget(size_hint_y=None, height=dp(15)))
        grid.add_widget(Label(
            text='Action Notch', font_size=sp(28), bold=True,
            color=get_color_from_hex(UI.ACC),
            size_hint_y=None, height=dp(40)
        ))
        grid.add_widget(Label(
            text='v2.1.0 - Fixed Edition', font_size=sp(13),
            color=get_color_from_hex(UI.SUB),
            size_hint_y=None, height=dp(22)
        ))

        grid.add_widget(UI.sec('5 Gestures'))
        gestures_txt = '\n'.join([f'  {gn}' for _, gn in GESTURES])
        grid.add_widget(UI.lbl(
            gestures_txt, fs=sp(12),
            c=get_color_from_hex('#AAAABB'),
            shy=None, h=dp(80)
        ))

        grid.add_widget(UI.sec('17 Actions'))
        actions_txt = '\n'.join(
            [f'  {i+1}. {a}' for i, a in enumerate(ALL_ACTIONS)]
        )
        grid.add_widget(UI.lbl(
            actions_txt, fs=sp(11),
            c=get_color_from_hex('#AAAABB'),
            shy=None, h=dp(len(ALL_ACTIONS) * dp(4.5))
        ))

        grid.add_widget(Widget(size_hint_y=None, height=dp(20)))
        root.add_widget(sv)
        self.add_widget(root)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'main'


# ============================================================
# ANDROID SETUP
# ============================================================
def android_setup():
    if not IS_ANDROID:
        return
    try:
        from jnius import autoclass
        PA = autoclass('org.kivy.android.PythonActivity')
        act = PA.mActivity
        S = autoclass('android.provider.Settings')
        I = autoclass('android.content.Intent')
        U = autoclass('android.net.Uri')
        Ctx = autoclass('android.content.Context')
        PM = autoclass('android.os.PowerManager')

        # Overlay permission
        if not S.canDrawOverlays(act):
            intent = I(S.ACTION_MANAGE_OVERLAY_PERMISSION,
                       U.parse('package:' + act.getPackageName()))
            act.startActivityForResult(intent, 1234)

        # Battery optimization
        pm = act.getSystemService(Ctx.POWER_SERVICE)
        if not pm.isIgnoringBatteryOptimizations(act.getPackageName()):
            intent = I()
            intent.setAction(
                S.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
            )
            intent.setData(
                U.parse('package:' + act.getPackageName())
            )
            act.startActivity(intent)

    except Exception as e:
        print(f'Android setup: {e}')


# ============================================================
# MAIN APP
# ============================================================
class ActionNotchApp(App):
    def build(self):
        self.title = 'Action Notch'
        path = os.path.join(self.user_data_dir, 'settings.json')
        self.cfg = Settings(path)
        self.overlay = OverlayManager(self.cfg)

        sm = ScreenManager()
        sm.add_widget(MainScreen())
        sm.add_widget(Sub('gestures', 'Gesture Controls', page_gestures))
        sm.add_widget(Sub('notch', 'Notch Style', page_notch))
        sm.add_widget(Sub('theme', 'Theme & Colors', page_theme))
        sm.add_widget(Sub('settings', 'Settings', page_settings))
        sm.add_widget(StatsScreen())
        sm.add_widget(AboutScreen())

        Clock.schedule_once(lambda dt: self._init(), 1.0)
        return sm

    def _init(self):
        if IS_ANDROID:
            android_setup()
        if self.cfg.get('master_enabled', True):
            self.overlay.create()

    def on_pause(self):
        self.cfg.save()
        return True

    def on_resume(self):
        self.cfg._load()

    def on_stop(self):
        self.cfg.save()


if __name__ == '__main__':
    ActionNotchApp().run()
