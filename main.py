"""
Mobile App File - Smart app with persistent settings
Automatically detects platform and saves server URL
Run: python mobile_app.py
"""

from kivy.app import App
from kivy.lang import Builder
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
import ssl
import os

# ============================================
# PLATFORM DETECTION
# ============================================
IS_ANDROID = platform == 'android'
IS_IOS = platform == 'ios'
IS_MOBILE = IS_ANDROID or IS_IOS
IS_DESKTOP = not IS_MOBILE

print(f"Platform: {platform}")
print(f"Is Mobile: {IS_MOBILE}")
print(f"Is Desktop: {IS_DESKTOP}")

# ============================================
# STORAGE CONFIGURATION
# ============================================
if IS_ANDROID:
    from android.storage import app_storage_path
    STORAGE_PATH = app_storage_path()
elif IS_IOS:
    from kivy.utils import platform
    import os
    STORAGE_PATH = os.path.expanduser('~/Documents')
else:
    # Desktop (Windows, Linux, Mac)
    STORAGE_PATH = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(STORAGE_PATH, 'app_config.json')

print(f"Storage path: {STORAGE_PATH}")
print(f"Config file: {CONFIG_FILE}")

# ============================================
# DEFAULT SERVER URL
# ============================================
DEFAULT_SERVER_URL = "https://689vk46r-5000.euw.devtunnels.ms"
FETCH_INTERVAL = 5  # seconds

# ============================================


def hex_to_kivy(hex_color, alpha=1.0):
    """Convert hex to Kivy color"""
    try:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b, alpha)
    except:
        return (1, 1, 1, alpha)


class ConfigManager:
    """Manages app configuration"""
    
    @staticmethod
    def load_config():
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"Config loaded from: {CONFIG_FILE}")
                    return config
        except Exception as e:
            print(f"Error loading config: {e}")
        
        # Return default config
        return {
            "server_url": DEFAULT_SERVER_URL,
            "fetch_interval": FETCH_INTERVAL
        }
    
    @staticmethod
    def save_config(config):
        """Save configuration to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            print(f"Config saved to: {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False


class AppLoader(BoxLayout):
    """Loads and manages the dynamic app"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.last_python_code = ""
        self.current_app = None
        
        # Load config
        self.config = ConfigManager.load_config()
        self.server_url = self.config.get("server_url", DEFAULT_SERVER_URL)
        self.fetch_interval = self.config.get("fetch_interval", FETCH_INTERVAL)
        
        print(f"Server URL: {self.server_url}")
        print(f"Fetch interval: {self.fetch_interval}s")
        
        # Background
        with self.canvas.before:
            Color(0.07, 0.08, 0.11, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Create header
        self._create_header()
        
        # App container
        self.app_container = BoxLayout(orientation='vertical')
        self.add_widget(self.app_container)
        
        # Show loading
        self._show_loading()
        
        # Start fetching
        Clock.schedule_once(lambda dt: self.fetch_app(), 1)
        self.fetch_schedule = Clock.schedule_interval(
            lambda dt: self.fetch_app(silent=True), 
            self.fetch_interval
        )
    
    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size
    
    def _create_header(self):
        """Create header"""
        header = BoxLayout(
            size_hint=(1, None),
            height=dp(55),
            padding=[dp(15), dp(10)],
            spacing=dp(10)
        )
        
        with header.canvas.before:
            Color(0.1, 0.11, 0.14, 1)
            self._header_bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(
            pos=lambda *a: setattr(self._header_bg, 'pos', header.pos),
            size=lambda *a: setattr(self._header_bg, 'size', header.size)
        )
        
        # Title
        self.title_label = Label(
            text='Dynamic App',
            font_size='16sp',
            color=get_color_from_hex('#e94560'),
            bold=True,
            size_hint=(0.5, 1),
            halign='left'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        header.add_widget(self.title_label)
        
        # Status indicator
        self.status_label = Label(
            text='...',
            font_size='14sp',
            color=get_color_from_hex('#888888'),
            size_hint=(0.2, 1)
        )
        header.add_widget(self.status_label)
        
        # Refresh button
        refresh_btn = Button(
            text='Refresh',
            font_size='14sp',
            size_hint=(0.15, 1),
            background_color=hex_to_kivy('#0f3460'),
            background_normal='',
            on_press=lambda x: self.fetch_app()
        )
        header.add_widget(refresh_btn)
        
        # Settings button
        settings_btn = Button(
            text='Settings',
            font_size='14sp',
            size_hint=(0.15, 1),
            background_color=hex_to_kivy('#e94560'),
            background_normal='',
            on_press=lambda x: self._show_settings()
        )
        header.add_widget(settings_btn)
        
        self.add_widget(header)
    
    def _show_loading(self):
        """Show loading screen"""
        self.app_container.clear_widgets()
        
        box = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(20))
        
        box.add_widget(Label(
            text='Loading',
            font_size='60sp',
            size_hint_y=None,
            height=dp(100),
            color=get_color_from_hex('#00d9ff')
        ))
        
        box.add_widget(Label(
            text='Connecting to server...',
            font_size='18sp',
            color=get_color_from_hex('#888888')
        ))
        
        box.add_widget(Label(
            text=f'Server: {self.server_url}',
            font_size='12sp',
            color=get_color_from_hex('#555555')
        ))
        
        box.add_widget(Label(
            text=f'Platform: {platform}',
            font_size='12sp',
            color=get_color_from_hex('#555555')
        ))
        
        self.app_container.add_widget(box)
    
    def _show_error(self, error_msg):
        """Show error"""
        self.app_container.clear_widgets()
        
        scroll = ScrollView()
        box = BoxLayout(
            orientation='vertical', 
            padding=dp(30), 
            spacing=dp(15),
            size_hint_y=None
        )
        box.bind(minimum_height=box.setter('height'))
        
        box.add_widget(Label(
            text='ERROR',
            font_size='50sp',
            size_hint_y=None,
            height=dp(80),
            color=get_color_from_hex('#e94560')
        ))
        
        box.add_widget(Label(
            text='Failed to Load App',
            font_size='20sp',
            color=get_color_from_hex('#ff6b81'),
            size_hint_y=None,
            height=dp(40)
        ))
        
        error_label = Label(
            text=error_msg,
            font_size='13sp',
            color=get_color_from_hex('#cccccc'),
            size_hint_y=None,
            text_size=(Window.width - dp(60), None),
            halign='left'
        )
        error_label.bind(texture_size=error_label.setter('size'))
        box.add_widget(error_label)
        
        tips = Label(
            text='Tips:\n• Check if server is running\n• Verify server URL in settings\n• Check network connection\n• Server must be accessible from this device',
            font_size='12sp',
            color=get_color_from_hex('#888888'),
            size_hint_y=None,
            height=dp(120),
            halign='left',
            text_size=(Window.width - dp(60), None)
        )
        box.add_widget(tips)
        
        retry_btn = Button(
            text='Retry Connection',
            size_hint=(0.7, None),
            height=dp(50),
            pos_hint={'center_x': 0.5},
            background_color=hex_to_kivy('#0f3460'),
            background_normal='',
            on_press=lambda x: self.fetch_app()
        )
        box.add_widget(retry_btn)
        
        settings_btn = Button(
            text='Open Settings',
            size_hint=(0.7, None),
            height=dp(50),
            pos_hint={'center_x': 0.5},
            background_color=hex_to_kivy('#e94560'),
            background_normal='',
            on_press=lambda x: self._show_settings()
        )
        box.add_widget(settings_btn)
        
        scroll.add_widget(box)
        self.app_container.add_widget(scroll)
    
    def fetch_app(self, silent=False):
        """Fetch app from server"""
        if not silent:
            self.status_label.text = 'Loading...'
            self.status_label.color = get_color_from_hex('#00d9ff')
        
        def _fetch():
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                url = f"{self.server_url}/api/app"
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'KivyMobileApp/3.0')
                
                with urllib.request.urlopen(req, timeout=10, context=context) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                kv_code = data.get('kv_code', '')
                python_code = data.get('python_code', '')
                app_class_name = data.get('app_class_name', '')
                
                # Check if Python code changed
                if python_code != self.last_python_code:
                    self.last_python_code = python_code
                    Clock.schedule_once(
                        lambda dt: self._load_app(kv_code, python_code, app_class_name)
                    )
                    print(f"App updated from server")
                
                Clock.schedule_once(lambda dt: self._set_status('Connected', '#00ff88'))
                
            except Exception as e:
                error_msg = str(e)
                print(f"Fetch error: {error_msg}")
                
                if not silent:
                    Clock.schedule_once(lambda dt: self._show_error(error_msg))
                
                Clock.schedule_once(lambda dt: self._set_status('Error', '#e94560'))
        
        thread = threading.Thread(target=_fetch, daemon=True)
        thread.start()
    
    def _load_app(self, kv_code, python_code, app_class_name):
        """Load and execute the app"""
        try:
            print(f"Loading app: {app_class_name}")
            
            # Clear container
            self.app_container.clear_widgets()
            
            # Stop previous app if exists
            if self.current_app:
                try:
                    self.current_app.stop()
                except:
                    pass
            
            # Execute Python code
            namespace = {
                'App': App,
                'StringProperty': __import__('kivy.properties', fromlist=['StringProperty']).StringProperty,
                'NumericProperty': __import__('kivy.properties', fromlist=['NumericProperty']).NumericProperty,
                'BooleanProperty': __import__('kivy.properties', fromlist=['BooleanProperty']).BooleanProperty,
                'ListProperty': __import__('kivy.properties', fromlist=['ListProperty']).ListProperty,
                'ObjectProperty': __import__('kivy.properties', fromlist=['ObjectProperty']).ObjectProperty,
                'Clock': Clock,
                'Clipboard': __import__('kivy.core.clipboard', fromlist=['Clipboard']).Clipboard,
            }
            
            exec(python_code, namespace)
            
            # Get app class
            if app_class_name and app_class_name in namespace:
                AppClass = namespace[app_class_name]
            else:
                raise Exception(f"App class '{app_class_name}' not found")
            
            # Create app instance
            self.current_app = AppClass()
            
            # Build UI from KV code
            if kv_code:
                root_widget = Builder.load_string(kv_code)
                self.current_app.root = root_widget
            else:
                raise Exception("No KV code provided")
            
            # Add to container
            self.app_container.add_widget(root_widget)
            
            # Start the app
            try:
                self.current_app.on_start()
            except:
                pass
            
            print(f"App loaded successfully")
            
        except Exception as e:
            error_msg = str(e)
            print(f"Load error: {error_msg}")
            self._show_error(f"Failed to load app:\n\n{error_msg}")
    
    def _set_status(self, text, color):
        """Set status"""
        self.status_label.text = text
        self.status_label.color = get_color_from_hex(color)
    
    def _show_settings(self):
        """Show settings popup"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Title
        content.add_widget(Label(
            text='App Settings',
            font_size='20sp',
            color=get_color_from_hex('#e94560'),
            bold=True,
            size_hint_y=None,
            height=dp(40)
        ))
        
        # Platform info
        platform_info = f"Platform: {platform}\n"
        platform_info += f"Mobile: {'Yes' if IS_MOBILE else 'No'}\n"
        platform_info += f"Storage: {STORAGE_PATH}"
        
        content.add_widget(Label(
            text=platform_info,
            font_size='12sp',
            color=get_color_from_hex('#888888'),
            size_hint_y=None,
            height=dp(80)
        ))
        
        # Server URL
        content.add_widget(Label(
            text='Server URL:',
            size_hint_y=None,
            height=dp(30),
            font_size='14sp',
            halign='left'
        ))
        
        url_input = TextInput(
            text=self.server_url,
            size_hint_y=None,
            height=dp(50),
            multiline=False,
            font_size='13sp',
            background_color=hex_to_kivy('#0f0f23'),
            foreground_color=hex_to_kivy('#ffffff'),
            cursor_color=hex_to_kivy('#e94560')
        )
        content.add_widget(url_input)
        
        # Fetch interval
        content.add_widget(Label(
            text='Auto-refresh interval (seconds):',
            size_hint_y=None,
            height=dp(30),
            font_size='14sp',
            halign='left'
        ))
        
        interval_input = TextInput(
            text=str(self.fetch_interval),
            size_hint_y=None,
            height=dp(50),
            multiline=False,
            font_size='13sp',
            input_filter='int',
            background_color=hex_to_kivy('#0f0f23'),
            foreground_color=hex_to_kivy('#ffffff'),
            cursor_color=hex_to_kivy('#e94560')
        )
        content.add_widget(interval_input)
        
        # Info label
        info_label = Label(
            text=f'Current: {self.server_url}\nConfig file: {CONFIG_FILE}',
            font_size='11sp',
            color=get_color_from_hex('#666666'),
            size_hint_y=None,
            height=dp(60)
        )
        content.add_widget(info_label)
        
        # Buttons
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        def save_settings(instance):
            new_url = url_input.text.strip().rstrip('/')
            new_interval = int(interval_input.text) if interval_input.text.isdigit() else 5
            
            if new_url and new_url != self.server_url:
                self.server_url = new_url
                self.config['server_url'] = new_url
                print(f"Server URL changed to: {new_url}")
            
            if new_interval != self.fetch_interval:
                self.fetch_interval = new_interval
                self.config['fetch_interval'] = new_interval
                
                # Reschedule fetch
                Clock.unschedule(self.fetch_schedule)
                self.fetch_schedule = Clock.schedule_interval(
                    lambda dt: self.fetch_app(silent=True),
                    self.fetch_interval
                )
                print(f"Fetch interval changed to: {new_interval}s")
            
            # Save config
            if ConfigManager.save_config(self.config):
                info_label.text = 'Settings saved successfully!'
                info_label.color = get_color_from_hex('#00ff88')
                Clock.schedule_once(lambda dt: popup.dismiss(), 1)
                Clock.schedule_once(lambda dt: self.fetch_app(), 1.5)
            else:
                info_label.text = 'Error saving settings!'
                info_label.color = get_color_from_hex('#e94560')
        
        save_btn = Button(
            text='Save',
            background_color=hex_to_kivy('#00ff88'),
            background_normal='',
            color=get_color_from_hex('#000000'),
            on_press=save_settings
        )
        btn_box.add_widget(save_btn)
        
        def test_connection(instance):
            test_url = url_input.text.strip().rstrip('/')
            info_label.text = 'Testing connection...'
            info_label.color = get_color_from_hex('#00d9ff')
            
            def _test():
                try:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    
                    url = f"{test_url}/api/health"
                    req = urllib.request.Request(url)
                    
                    with urllib.request.urlopen(req, timeout=5, context=context) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        msg = f'Connection successful!\nStatus: {data.get("status")}'
                        Clock.schedule_once(lambda dt: setattr(info_label, 'text', msg))
                        Clock.schedule_once(lambda dt: setattr(info_label, 'color', get_color_from_hex('#00ff88')))
                
                except Exception as e:
                    msg = f'Connection failed:\n{str(e)[:50]}'
                    Clock.schedule_once(lambda dt: setattr(info_label, 'text', msg))
                    Clock.schedule_once(lambda dt: setattr(info_label, 'color', get_color_from_hex('#e94560')))
            
            threading.Thread(target=_test, daemon=True).start()
        
        test_btn = Button(
            text='Test',
            background_color=hex_to_kivy('#0f3460'),
            background_normal='',
            on_press=test_connection
        )
        btn_box.add_widget(test_btn)
        
        close_btn = Button(
            text='Close',
            background_color=hex_to_kivy('#e94560'),
            background_normal='',
            on_press=lambda x: popup.dismiss()
        )
        btn_box.add_widget(close_btn)
        
        content.add_widget(btn_box)
        
        popup = Popup(
            title='Settings',
            content=content,
            size_hint=(0.95, 0.85) if IS_MOBILE else (0.6, 0.7),
            separator_color=hex_to_kivy('#e94560')
        )
        popup.open()


class MobileAppRunner(App):
    """Main runner app"""
    
    def build(self):
        self.title = 'Dynamic Mobile App'
        Window.clearcolor = get_color_from_hex('#0d1117')
        return AppLoader()


if __name__ == '__main__':
    print("=" * 70)
    print("Dynamic Mobile App Starting...")
    print("=" * 70)
    print(f"Platform: {platform}")
    print(f"Storage: {STORAGE_PATH}")
    print(f"Config: {CONFIG_FILE}")
    print("=" * 70)
    print()
    
    MobileAppRunner().run()
