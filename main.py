"""
Mobile App - Downloads and runs your app from server
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex, platform
from kivy.metrics import dp

import json
import threading
import urllib.request
import urllib.error
import ssl
import os
import sys
import socket
import importlib
import importlib.util
import traceback

# ============================================
# PLATFORM
# ============================================
IS_ANDROID = platform == 'android'
IS_MOBILE = IS_ANDROID or platform == 'win'

if IS_ANDROID:
    try:
        from android.storage import app_storage_path
        STORAGE = app_storage_path()
    except:
        STORAGE = os.path.dirname(os.path.abspath(__file__))
else:
    STORAGE = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(STORAGE, 'app_config.json')
APP_FILE = os.path.join(STORAGE, '_loaded_app.py')

DEFAULT_URL = "http://localhost:5000"
FETCH_INTERVAL = 5
TIMEOUT = 15


def hex_c(h, a=1.0):
    """Convert hex color - supports both #RGB and #RRGGBB"""
    try:
        h = h.lstrip('#')
        # Handle short hex like #888 -> #888888
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b, a)
    except:
        return (1, 1, 1, a)


# ============================================
# CONFIG
# ============================================
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"server_url": DEFAULT_URL}

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
        return True
    except:
        return False


# ============================================
# Remove if __name__ block from code
# ============================================
def strip_main_block(code):
    lines = code.split('\n')
    result = []
    skip = False
    for line in lines:
        s = line.strip()
        if s.startswith('if __name__') and '__main__' in s:
            skip = True
            continue
        if skip:
            if s == '' or line.startswith('    ') or line.startswith('\t'):
                continue
            else:
                skip = False
        if not skip:
            result.append(line)
    return '\n'.join(result)


# ============================================
# Find App subclass in module
# ============================================
def find_app_class(module):
    for name in dir(module):
        obj = getattr(module, name, None)
        if obj is None:
            continue
        try:
            if isinstance(obj, type) and issubclass(obj, App) and obj is not App:
                return name, obj
        except:
            continue
    return None, None


# ============================================
# MAIN LOADER
# ============================================
class AppLoader(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.last_code = ""
        self.loaded_app = None

        cfg = load_config()
        self.server_url = cfg.get("server_url", DEFAULT_URL)

        with self.canvas.before:
            Color(0.07, 0.08, 0.11, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        self._make_header()

        self.content = BoxLayout(orientation='vertical')
        self.add_widget(self.content)

        self._msg('Connecting...', self.server_url)

        Clock.schedule_once(lambda dt: self.fetch(), 1)
        self.schedule = Clock.schedule_interval(
            lambda dt: self.fetch(silent=True), FETCH_INTERVAL
        )

    def _upd_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _make_header(self):
        h = BoxLayout(size_hint=(1, None), height=dp(48),
                      padding=[dp(10), dp(8)], spacing=dp(8))
        with h.canvas.before:
            Color(0.1, 0.11, 0.14, 1)
            self._hbg = Rectangle(pos=h.pos, size=h.size)
        h.bind(
            pos=lambda *a: setattr(self._hbg, 'pos', h.pos),
            size=lambda *a: setattr(self._hbg, 'size', h.size)
        )

        self.title_lbl = Label(
            text='App Loader', font_size='15sp',
            color=hex_c('#e94560'), bold=True, size_hint=(0.5, 1)
        )
        h.add_widget(self.title_lbl)

        self.status_lbl = Label(
            text='...', font_size='12sp',
            color=hex_c('#888888'), size_hint=(0.2, 1)
        )
        h.add_widget(self.status_lbl)

        h.add_widget(Button(
            text='Refresh', font_size='12sp', size_hint=(0.15, 1),
            background_color=hex_c('#0f3460'), background_normal='',
            on_press=lambda x: self.fetch()
        ))

        h.add_widget(Button(
            text='Settings', font_size='12sp', size_hint=(0.15, 1),
            background_color=hex_c('#333333'), background_normal='',
            on_press=lambda x: self._settings()
        ))

        self.add_widget(h)

    def _msg(self, title, detail=''):
        self.content.clear_widgets()
        b = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(15))
        b.add_widget(Label(
            text=title, font_size='20sp',
            color=hex_c('#ffffff'), size_hint_y=None, height=dp(50)
        ))
        if detail:
            b.add_widget(Label(
                text=detail, font_size='12sp',
                color=hex_c('#888888'), size_hint_y=None, height=dp(40)
            ))
        b.add_widget(Label())
        self.content.add_widget(b)

    def _error(self, msg):
        self.content.clear_widgets()
        sv = ScrollView()
        b = BoxLayout(orientation='vertical', padding=dp(20),
                      spacing=dp(10), size_hint_y=None)
        b.bind(minimum_height=b.setter('height'))

        b.add_widget(Label(
            text='Error', font_size='28sp',
            color=hex_c('#e94560'), size_hint_y=None, height=dp(50)
        ))

        el = Label(
            text=msg, font_size='12sp', color=hex_c('#cccccc'),
            size_hint_y=None, text_size=(Window.width - dp(40), None), halign='left'
        )
        el.bind(texture_size=el.setter('size'))
        b.add_widget(el)

        bb = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        bb.add_widget(Button(
            text='Retry', background_color=hex_c('#0f3460'),
            background_normal='', on_press=lambda x: self.fetch()
        ))
        bb.add_widget(Button(
            text='Settings', background_color=hex_c('#e94560'),
            background_normal='', on_press=lambda x: self._settings()
        ))
        b.add_widget(bb)

        sv.add_widget(b)
        self.content.add_widget(sv)

    def fetch(self, silent=False):
        if not silent:
            self.status_lbl.text = 'Loading...'
            self.status_lbl.color = hex_c('#00d9ff')

        def _f():
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(f"{self.server_url}/api/code")
                req.add_header('User-Agent', 'KivyApp/3')

                with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
                    data = json.loads(r.read().decode())

                code = data.get('code', '')
                if not code:
                    if not silent:
                        Clock.schedule_once(lambda dt: self._error(
                            'Server returned empty code.\n\n'
                            'Make sure ui_design.py exists.'
                        ))
                    return

                if code != self.last_code:
                    self.last_code = code
                    Clock.schedule_once(lambda dt: self._run(code))

                Clock.schedule_once(lambda dt: self._status('Connected', '#00ff88'))

            except Exception as e:
                msg = str(e)
                print(f"Fetch error: {msg}")
                if not silent:
                    Clock.schedule_once(lambda dt: self._error(msg))
                Clock.schedule_once(lambda dt: self._status('Error', '#e94560'))

        threading.Thread(target=_f, daemon=True).start()

    def _run(self, code):
        try:
            print("Loading app from server...")

            # Stop previous
            if self.loaded_app:
                try:
                    self.loaded_app.stop()
                except:
                    pass
                self.loaded_app = None

            # Remove if __name__ block
            clean = strip_main_block(code)

            # Save to file
            with open(APP_FILE, 'w', encoding='utf-8') as f:
                f.write(clean)

            # Remove old module
            mod_name = '_loaded_app'
            if mod_name in sys.modules:
                del sys.modules[mod_name]

            # Add path
            if STORAGE not in sys.path:
                sys.path.insert(0, STORAGE)

            # Import
            spec = importlib.util.spec_from_file_location(mod_name, APP_FILE)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)

            # Find App class
            name, cls = find_app_class(mod)
            if cls is None:
                self._error('No App class found in ui_design.py')
                return

            print(f"Found: {name}")

            # Create and build
            app_inst = cls()
            self.loaded_app = app_inst

            root = app_inst.build()
            if root is None:
                self._error(f'{name}.build() returned None')
                return

            # Show it
            self.content.clear_widgets()
            self.content.add_widget(root)

            if hasattr(app_inst, 'title') and app_inst.title:
                self.title_lbl.text = app_inst.title

            try:
                app_inst.on_start()
            except:
                pass

            print(f"App running: {name}")
            self._status('Running', '#00ff88')

        except Exception as e:
            tb = traceback.format_exc()
            print(f"Load error:\n{tb}")
            self._error(f"Load failed:\n\n{tb}")

    def _status(self, t, c):
        self.status_lbl.text = t
        self.status_lbl.color = hex_c(c)

    def _settings(self):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))

        content.add_widget(Label(
            text='Settings', font_size='20sp',
            color=hex_c('#e94560'), bold=True,
            size_hint_y=None, height=dp(35)
        ))

        content.add_widget(Label(
            text=f'Platform: {platform}  |  Storage: {STORAGE}',
            font_size='10sp', color=hex_c('#888888'),
            size_hint_y=None, height=dp(30)
        ))

        content.add_widget(Label(
            text='Server URL:', font_size='13sp',
            size_hint_y=None, height=dp(22), halign='left'
        ))

        url_in = TextInput(
            text=self.server_url, size_hint_y=None, height=dp(42),
            multiline=False, font_size='13sp',
            background_color=hex_c('#111111'),
            foreground_color=hex_c('#ffffff'),
            cursor_color=hex_c('#e94560')
        )
        content.add_widget(url_in)

        # Quick buttons
        qb = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5))

        qb.add_widget(Button(
            text='Localhost', font_size='11sp',
            background_color=hex_c('#333333'), background_normal='',
            on_press=lambda x: setattr(url_in, 'text', 'http://localhost:5000')
        ))

        def set_net(x):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                url_in.text = f"http://{s.getsockname()[0]}:5000"
                s.close()
            except:
                url_in.text = "http://192.168.1.100:5000"

        qb.add_widget(Button(
            text='Network IP', font_size='11sp',
            background_color=hex_c('#333333'), background_normal='',
            on_press=set_net
        ))

        content.add_widget(qb)

        info = Label(
            text='', font_size='12sp', color=hex_c('#666666'),
            size_hint_y=None, height=dp(35)
        )
        content.add_widget(info)

        # Buttons
        bb = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))

        def do_save(x):
            self.server_url = url_in.text.strip().rstrip('/')
            save_config({"server_url": self.server_url})
            self.last_code = ""
            info.text = 'Saved!'
            info.color = hex_c('#00ff88')
            Clock.schedule_once(lambda dt: popup.dismiss(), 0.5)
            Clock.schedule_once(lambda dt: self.fetch(), 1)

        def do_test(x):
            info.text = 'Testing...'
            info.color = hex_c('#00d9ff')
            def _t():
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(
                        f"{url_in.text.strip().rstrip('/')}/api/health"
                    )
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                        d = json.loads(r.read().decode())
                        Clock.schedule_once(lambda dt: setattr(
                            info, 'text', f'OK! ({d.get("code_length", 0)} chars)'
                        ))
                        Clock.schedule_once(lambda dt: setattr(
                            info, 'color', hex_c('#00ff88')
                        ))
                except Exception as e:
                    Clock.schedule_once(lambda dt: setattr(
                        info, 'text', f'Failed: {str(e)[:30]}'
                    ))
                    Clock.schedule_once(lambda dt: setattr(
                        info, 'color', hex_c('#e94560')
                    ))
            threading.Thread(target=_t, daemon=True).start()

        bb.add_widget(Button(
            text='Save', background_color=hex_c('#00cc66'),
            background_normal='', color=hex_c('#000000'), on_press=do_save
        ))
        bb.add_widget(Button(
            text='Test', background_color=hex_c('#0f3460'),
            background_normal='', on_press=do_test
        ))
        bb.add_widget(Button(
            text='Close', background_color=hex_c('#e94560'),
            background_normal='', on_press=lambda x: popup.dismiss()
        ))

        content.add_widget(bb)

        popup = Popup(
            title='Settings', content=content,
            size_hint=(0.95, 0.7) if IS_MOBILE else (0.5, 0.6),
            separator_color=hex_c('#e94560')
        )
        popup.open()


class RunnerApp(App):
    def build(self):
        self.title = 'App Loader'
        Window.clearcolor = hex_c('#0d1117')
        return AppLoader()


if __name__ == '__main__':
    print(f"Platform: {platform}")
    print(f"Storage: {STORAGE}")
    RunnerApp().run()
