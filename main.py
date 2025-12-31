# main.py

import os
import json
import threading
import socket
import platform
import ipaddress
import concurrent.futures
import math
from typing import List, Optional, Tuple, Dict, Any, Callable

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, InstructionGroup
from kivy.uix.screenmanager import ScreenManager, Screen

# referenced by KV
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

from kivy.utils import platform as kivy_platform


# ==================== Persistent storage for patterns ====================

def _as_pattern_tuple(x: Any) -> Optional[Tuple[int, ...]]:
    if not isinstance(x, (list, tuple)):
        return None
    out: List[int] = []
    for v in x:
        try:
            iv = int(v)
        except Exception:
            return None
        if not (0 <= iv <= 8):
            return None
        out.append(iv)
    if len(set(out)) != len(out):
        return None
    return tuple(out)


class PatternStore:
    def __init__(self, path: str):
        self.path = str(path)

    def load(self) -> Optional[Dict[str, Tuple[int, ...]]]:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return None
            m = _as_pattern_tuple(data.get("m_pattern"))
            g = _as_pattern_tuple(data.get("g_pattern"))
            if not m or not g:
                return None
            return {"m_pattern": m, "g_pattern": g}
        except Exception:
            return None

    def save(
        self,
        m: Tuple[int, ...],
        g: Tuple[int, ...],
        extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass

        payload: Dict[str, Any] = {"m_pattern": list(m), "g_pattern": list(g)}
        if extra:
            payload.update(extra)

        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


# ==================== Pattern Lock Widget ====================

class PatternLock(Widget):
    dot_radius = dp(18)
    hit_radius = dp(28)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._dot_centers: List[Tuple[float, float]] = []
        self.pattern: List[int] = []

        self._line_group = InstructionGroup()
        self._dots_group = InstructionGroup()
        self.canvas.add(self._line_group)
        self.canvas.add(self._dots_group)

        self._path_line: Optional[Line] = None

        # "neutral" | "success" | "error"
        self.feedback_mode: str = "neutral"
        self.input_locked: bool = False

        # callback: callable(pattern_tuple, lock_widget)
        self.on_complete: Optional[Callable[[Tuple[int, ...], "PatternLock"], None]] = None

        self.bind(pos=self._rebuild, size=self._rebuild)

    def _rebuild(self, *_):
        self._compute_centers()
        self._draw_dots()
        self._redraw_path()

    def _compute_centers(self):
        x0, y0 = self.x, self.y
        w, h = self.width, self.height
        side = min(w, h)
        pad = dp(24)
        usable = max(side - 2 * pad, dp(10))
        step = usable / 2.0

        cx = x0 + w / 2.0
        cy = y0 + h / 2.0
        left = cx - usable / 2.0
        bottom = cy - usable / 2.0

        centers: List[Tuple[float, float]] = []
        for r in range(3):
            for c in range(3):
                centers.append((left + c * step, bottom + (2 - r) * step))
        self._dot_centers = centers

    def _feedback_color(self) -> Tuple[float, float, float, float]:
        if self.feedback_mode == "success":
            return (0.10, 0.85, 0.25, 1.0)
        if self.feedback_mode == "error":
            return (0.95, 0.20, 0.20, 1.0)
        return (0.20, 0.65, 1.00, 1.0)

    def _draw_dots(self):
        self._dots_group.clear()
        sel_rgba = self._feedback_color()

        for i, (cx, cy) in enumerate(self._dot_centers):
            selected = i in self.pattern
            if selected:
                color = Color(*sel_rgba)
                radius = self.dot_radius * 1.1
            else:
                color = Color(0.75, 0.75, 0.75, 1.0)
                radius = self.dot_radius

            self._dots_group.add(color)
            self._dots_group.add(Ellipse(pos=(cx - radius, cy - radius), size=(2 * radius, 2 * radius)))

    def _redraw_path(self):
        self._line_group.clear()
        self._path_line = None
        if not self.pattern:
            return

        pts: List[float] = []
        for idx in self.pattern:
            cx, cy = self._dot_centers[idx]
            pts.extend([cx, cy])

        r, g, b, _a = self._feedback_color()
        self._line_group.add(Color(r, g, b, 0.95))
        self._path_line = Line(points=pts, width=dp(3), cap="round", joint="round")
        self._line_group.add(self._path_line)

    def set_feedback(self, mode: str):
        self.feedback_mode = mode
        self._draw_dots()
        self._redraw_path()

    def reset(self):
        self.input_locked = False
        self.feedback_mode = "neutral"
        self.pattern.clear()
        self._draw_dots()
        self._redraw_path()

    def _hit_test(self, x: float, y: float) -> Optional[int]:
        best_i = None
        best_d = float("inf")
        for i, (cx, cy) in enumerate(self._dot_centers):
            d = math.hypot(x - cx, y - cy)
            if d <= self.hit_radius and d < best_d:
                best_d = d
                best_i = i
        return best_i

    def _add_dot_if_new(self, idx: int):
        if idx not in self.pattern:
            self.pattern.append(idx)
            self._draw_dots()
            self._redraw_path()

    def on_touch_down(self, touch):
        if self.input_locked:
            return True
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        idx = self._hit_test(*touch.pos)
        if idx is not None:
            self._add_dot_if_new(idx)
            touch.grab(self)
            return True
        return True

    def on_touch_move(self, touch):
        if self.input_locked:
            return True
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        idx = self._hit_test(*touch.pos)
        if idx is not None:
            self._add_dot_if_new(idx)
        return True

    def on_touch_up(self, touch):
        if self.input_locked:
            return True
        if touch.grab_current is not self:
            return super().on_touch_up(touch)

        touch.ungrab(self)
        self.input_locked = True

        entered = tuple(self.pattern)
        cb = self.on_complete
        if callable(cb):
            cb(entered, self)
        else:
            App.get_running_app().on_pattern_entered(entered, self)
        return True


# ==================== Screens ====================

class LoginScreen(Screen):
    def on_kv_post(self, base_widget):
        try:
            self.ids.lock.on_complete = App.get_running_app().on_login_pattern
        except Exception:
            pass

    def on_pre_enter(self, *args):
        try:
            self.ids.lock.reset()
        except Exception:
            pass


class PasswordSettingsScreen(Screen):
    help_text = StringProperty("")
    status_text = StringProperty("")
    mode = StringProperty("m")   # "m" or "g"
    step = StringProperty("first")  # "first" or "confirm"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._first_pattern: Optional[Tuple[int, ...]] = None

    def on_kv_post(self, base_widget):
        try:
            self.ids.pw_lock.on_complete = self._on_new_pattern_drawn
        except Exception:
            pass

    def on_pre_enter(self, *args):
        self._reset_flow()

    def _reset_flow(self):
        self.step = "first"
        self._first_pattern = None
        self.status_text = ""
        self.help_text = self._make_help()
        try:
            self.ids.pw_lock.reset()
        except Exception:
            pass

    def set_mode(self, mode: str):
        mode = (mode or "").lower().strip()
        if mode not in ("m", "g"):
            return
        if self.mode == mode:
            return
        self.mode = mode
        self._reset_flow()

    def _make_help(self) -> str:
        app = App.get_running_app()
        save_path = getattr(getattr(app, "pattern_store", None), "path", "(unknown)")
        where = "phone" if app.is_mobile else "laptop/desktop"
        target = "M (Login)" if self.mode == "m" else "G (Admin)"
        return (
            f"Target: {target}\n"
            f"Step: {self.step}\n"
            f"Saved on this device ({where}) at:\n{save_path}\n\n"
            f"Draw a new pattern."
        )

    def _show_temp_feedback(self, lock: PatternLock, mode: str, seconds: float, after=None):
        lock.set_feedback(mode)

        def _later(_dt):
            try:
                lock.reset()
            except Exception:
                pass
            if callable(after):
                after()

        Clock.schedule_once(_later, float(seconds))

    def _on_new_pattern_drawn(self, entered: Tuple[int, ...], lock: PatternLock):
        if not entered or len(entered) < 4:
            self.status_text = "Pattern too short (minimum 4 dots)."
            self.help_text = self._make_help()
            self._show_temp_feedback(lock, "error", 1.0, after=self._reset_flow)
            return

        if self.step == "first":
            self._first_pattern = entered
            self.step = "confirm"
            self.status_text = "Now draw the SAME pattern again to confirm."
            self.help_text = self._make_help()
            self._show_temp_feedback(lock, "success", 0.35)
            return

        # confirm step
        if self._first_pattern != entered:
            self.status_text = "Patterns do not match. Try again."
            self.help_text = self._make_help()
            self._show_temp_feedback(lock, "error", 1.0, after=self._reset_flow)
            return

        app = App.get_running_app()
        other = app.g_pattern if self.mode == "m" else app.m_pattern
        if entered == other:
            self.status_text = "This pattern equals the other password. Choose a different one."
            self.help_text = self._make_help()
            self._show_temp_feedback(lock, "error", 1.0, after=self._reset_flow)
            return

        if self.mode == "m":
            app.m_pattern = entered
        else:
            app.g_pattern = entered

        ok = app.save_patterns()
        self.status_text = "Saved ✅" if ok else "Save failed ❌"
        self.help_text = self._make_help()
        self._show_temp_feedback(lock, "success", 0.8, after=self._reset_flow)

    def go_back(self):
        App.get_running_app().go_to_login()


# ==================== Scanner logic ====================

class LanScanner:
    def __init__(self, timeout=0.5, ping_timeout=1.0):
        self.timeout = float(timeout)
        self.ping_timeout = float(ping_timeout)
        try:
            self._platform = str(kivy_platform)
        except Exception:
            self._platform = platform.system().lower()

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _ping_host(self, ip):
        """
        روی اندروید/IOS از system ping استفاده نمی‌کنیم (سازگاری بهتر).
        روی دسکتاپ اگر ping در سیستم باشد، از آن استفاده می‌کنیم.
        """
        # موبایل: یک "TCP ping" سبک روی پورت‌های رایج
        if self._platform in ("android", "ios"):
            for port in (80, 443):
                try:
                    with socket.create_connection((ip, port), timeout=self.timeout):
                        return True
                except Exception:
                    continue
            return False

        # دسکتاپ: تلاش برای استفاده از دستور ping سیستم
        sys_name = platform.system().lower()
        try:
            if sys_name == "windows":
                cmd = ["ping", "-n", "1", "-w", str(int(self.ping_timeout * 1000)), ip]
            else:
                cmd = ["ping", "-c", "1", "-W", str(max(1, int(self.ping_timeout))), ip]
        except Exception:
            return False

        try:
            import subprocess
            proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.ping_timeout + 1.0,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _scan_port(self, ip, port):
        try:
            with socket.create_connection((ip, port), timeout=self.timeout):
                return True
        except Exception:
            return False


class VaultRow(BoxLayout):
    pass


PORT_INFO = {
    20: "FTP (data)",
    21: "FTP (control)",
    22: "SSH (remote shell)",
    23: "Telnet (legacy remote shell)",
    25: "SMTP (mail sending)",
    53: "DNS",
    67: "DHCP (server)",
    68: "DHCP (client)",
    80: "HTTP (web)",
    110: "POP3 (mail)",
    123: "NTP (time)",
    135: "MS RPC",
    139: "NetBIOS (Windows file sharing)",
    143: "IMAP (mail)",
    161: "SNMP",
    389: "LDAP",
    443: "HTTPS (secure web)",
    445: "SMB (Windows file sharing)",
    465: "SMTPS",
    587: "SMTP Submission",
    631: "IPP (printing)",
    993: "IMAPS",
    995: "POP3S",
    1433: "MS SQL Server",
    1521: "Oracle DB",
    1883: "MQTT",
    1900: "SSDP/UPnP",
    2049: "NFS",
    2375: "Docker (insecure API)",
    2376: "Docker (TLS API)",
    3306: "MySQL/MariaDB",
    3389: "RDP (Remote Desktop)",
    5432: "PostgreSQL",
    5672: "AMQP (RabbitMQ)",
    5900: "VNC (remote desktop)",
    6379: "Redis",
    8080: "HTTP-alt (web)",
    8443: "HTTPS-alt (web)",
}


# ==================== KV ====================

KV = r'''
#:import dp kivy.metrics.dp

<LoginScreen>:
    BoxLayout:
        padding: dp(18)
        canvas.before:
            Color:
                rgba: 0.08, 0.08, 0.08, 1
            Rectangle:
                pos: self.pos
                size: self.size
        PatternLock:
            id: lock

<PasswordSettingsScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(10)

        BoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(8)

            Button:
                text: "Back"
                size_hint_x: None
                width: dp(90)
                on_release: root.go_back()

            Label:
                text: "Change Patterns (draw to set)"
                text_size: self.width, None
                halign: "left"
                valign: "middle"

        BoxLayout:
            size_hint_y: None
            height: dp(42)
            spacing: dp(8)

            ToggleButton:
                id: mode_m
                text: "M (Login)"
                group: "mode"
                state: "down"
                on_state:
                    if self.state == "down": root.set_mode("m")

            ToggleButton:
                id: mode_g
                text: "G (Admin)"
                group: "mode"
                on_state:
                    if self.state == "down": root.set_mode("g")

        Label:
            text: root.help_text
            size_hint_y: None
            text_size: self.width, None
            halign: "left"
            valign: "top"
            height: self.texture_size[1] + dp(8)

        PatternLock:
            id: pw_lock

        Label:
            text: root.status_text
            size_hint_y: None
            text_size: self.width, None
            halign: "left"
            valign: "middle"
            height: self.texture_size[1] + dp(8)


<TextInput>:
    font_size: '18sp'
    halign: 'center'
    padding_x: dp(10)
    padding_y: max(0, (self.height - self.line_height) / 2)

<Row@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(46)
    spacing: dp(6)
    padding: dp(6)

    ip: ''
    real_ip: ''
    alive: ''
    ports: ''
    host: ''

    canvas.before:
        Color:
            rgba: 0.12, 0.12, 0.12, 0.30
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: 1, 1, 1, 1
        Line:
            rectangle: (self.x, self.y, self.width, self.height)
            width: 1.2

    Label:
        text: root.ip
        size_hint_x: 0.22
        text_size: self.size
        valign: 'middle'
        halign: 'left'
    Label:
        text: root.alive
        size_hint_x: 0.10
        text_size: self.size
        valign: 'middle'
        halign: 'center'
    Label:
        text: root.ports
        size_hint_x: 0.33
        text_size: self.size
        valign: 'middle'
        halign: 'left'
    Label:
        text: root.host
        size_hint_x: 0.25
        text_size: self.size
        valign: 'middle'
        halign: 'left'
    Button:
        text: 'Details'
        size_hint_x: 0.10
        on_release: app.root.get_screen('main').content.show_details(root.real_ip)

<VaultRow>:
    orientation: 'horizontal'
    size_hint: 1, None
    height: dp(42)
    spacing: dp(8)
    padding: dp(10)
    canvas.before:
        Color:
            rgba: 0.12, 0.12, 0.12, 0.30
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: 1, 1, 1, 1
        Line:
            rectangle: (self.x, self.y, self.width, self.height)
            width: 1.2


<MainScreen>:
    orientation: 'vertical'
    padding: dp(8)
    spacing: dp(6)

    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(6)

        ToggleButton:
            id: tab_config
            text: 'Settings'
            group: 'tabs'
            state: 'down'
            background_normal: ''
            background_down: ''
            background_color: (0.15, 0.55, 0.95, 1) if self.state == 'down' else (0.18, 0.18, 0.18, 1)
            color: 1,1,1,1
            on_state:
                if self.state == 'down': root.ids.sm.current = 'config'

        ToggleButton:
            id: tab_vault
            text: 'Vault'
            group: 'tabs'
            background_normal: ''
            background_down: ''
            background_color: (0.15, 0.55, 0.95, 1) if self.state == 'down' else (0.18, 0.18, 0.18, 1)
            color: 1,1,1,1
            on_state:
                if self.state == 'down': root.ids.sm.current = 'vault'

    ScreenManager:
        id: sm

        Screen:
            name: 'config'
            ScrollView:
                do_scroll_x: False
                bar_width: dp(10)
                scroll_type: ['bars', 'content']
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(14)
                    padding: dp(4), dp(10), dp(10), dp(10)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        Label:
                            text: root.local_ip_text
                            text_size: self.size
                            halign: 'left'
                            valign: 'middle'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        TextInput:
                            id: cidr_input
                            text: ''
                            multiline: False
                            hint_text: 'CIDR  (مثال: 192.168.1.0/24)'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        TextInput:
                            id: ports_input
                            text: '1-1024'
                            multiline: False
                            hint_text: 'Ports  (مثال: 80,443 یا 1-1024)'

                    BoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: dp(36) * 3 + dp(6) * 2
                        spacing: dp(6)

                        ToggleButton:
                            id: filter_toggle
                            text: 'Only with hostname: ON' if self.state == 'down' else 'Only with hostname: OFF'
                            state: 'down'
                            on_state:
                                root.filter_hostname = (self.state == 'down')
                                self.text = 'Only with hostname: ON' if self.state == 'down' else 'Only with hostname: OFF'
                                root.refresh_view()

                        ToggleButton:
                            id: ping_toggle
                            text: 'Ping first: ON' if self.state == 'down' else 'Ping first: OFF'
                            state: 'down'
                            on_state:
                                root.ping_first = (self.state == 'down')
                                self.text = 'Ping first: ON' if self.state == 'down' else 'Ping first: OFF'

                        ToggleButton:
                            id: dns_toggle
                            text: 'Resolve DNS: ON' if self.state == 'down' else 'Resolve DNS: OFF'
                            state: 'down'
                            on_state:
                                root.resolve_dns = (self.state == 'down')
                                self.text = 'Resolve DNS: ON' if self.state == 'down' else 'Resolve DNS: OFF'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(8)
                        Button:
                            id: start_btn
                            text: 'Start scan'
                            disabled: root.scanning
                            background_normal: ''
                            background_color: (0.2, 0.9, 0.3, 1) if not self.disabled else (0.2, 0.9, 0.3, 0.35)
                            on_press: root.start_scan()
                        Button:
                            id: stop_btn
                            text: 'Stop'
                            disabled: not root.scanning
                            on_press: root.stop_scan()
                        Button:
                            text: 'Clear'
                            on_press: root.clear_results()

        Screen:
            name: 'results'
            BoxLayout:
                orientation: 'vertical'
                spacing: dp(6)

                BoxLayout:
                    size_hint_y: None
                    height: dp(30)
                    spacing: dp(6)
                    ProgressBar:
                        max: 1.0
                        value: root.progress_value
                    Label:
                        text: str(int(root.progress_value * 100)) + '%'
                        size_hint_x: None
                        width: dp(60)
                        text_size: self.size
                        halign: 'right'
                        valign: 'middle'

                BoxLayout:
                    size_hint_y: None
                    height: dp(46)
                    spacing: dp(6)
                    padding: dp(6)
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                        Color:
                            rgba: 0, 0, 0, 1
                        Line:
                            rectangle: (self.x, self.y, self.width, self.height)
                            width: 1.2

                    Label:
                        text: 'IP'
                        color: 0,0,0,1
                        size_hint_x: 0.22
                        text_size: self.size
                        valign: 'middle'
                        halign: 'left'
                    Label:
                        text: 'Alive'
                        color: 0,0,0,1
                        size_hint_x: 0.10
                        text_size: self.size
                        valign: 'middle'
                        halign: 'center'
                    Label:
                        text: 'Ports'
                        color: 0,0,0,1
                        size_hint_x: 0.33
                        text_size: self.size
                        valign: 'middle'
                        halign: 'left'
                    Label:
                        text: 'Host'
                        color: 0,0,0,1
                        size_hint_x: 0.25
                        text_size: self.size
                        valign: 'middle'
                        halign: 'left'
                    Label:
                        text: 'Action'
                        color: 0,0,0,1
                        size_hint_x: 0.10
                        text_size: self.size
                        valign: 'middle'
                        halign: 'center'

                RecycleView:
                    id: rv
                    bar_width: dp(10)
                    scroll_type: ['bars', 'content']
                    viewclass: 'Row'
                    RecycleBoxLayout:
                        default_size: None, dp(46)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(6)
                        orientation: 'vertical'

        Screen:
            name: 'vault'
            on_pre_enter: root.refresh_vault_view()
            BoxLayout:
                orientation: 'vertical'
                spacing: dp(8)

                Label:
                    text: "WiFi Credentials Vault (stored locally as JSON)"
                    size_hint_y: None
                    height: dp(28)
                    text_size: self.size
                    halign: 'left'
                    valign: 'middle'

                BoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    spacing: dp(6)
                    TextInput:
                        id: vault_ssid
                        hint_text: 'SSID (key)'
                        multiline: False
                    TextInput:
                        id: vault_pass
                        hint_text: 'Password (value)'
                        multiline: False
                        password: True

                BoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    spacing: dp(6)
                    Button:
                        text: 'Save / Update'
                        on_press: root.vault_save()
                    Button:
                        text: 'Clear inputs'
                        on_press:
                            root.ids.vault_ssid.text = ''
                            root.ids.vault_pass.text = ''

                Label:
                    text: root.vault_status_text
                    size_hint_y: None
                    height: dp(24)
                    text_size: self.size
                    halign: 'left'
                    valign: 'middle'

                ScrollView:
                    do_scroll_x: False
                    do_scroll_y: True
                    bar_width: dp(10)
                    scroll_type: ['bars', 'content']

                    GridLayout:
                        id: vault_grid
                        cols: 1
                        size_hint_y: None
                        height: self.minimum_height
                        size_hint_x: 1
                        spacing: dp(6)
                        padding: dp(6)
'''


# ==================== Main Screen Logic ====================

class MainScreen(BoxLayout):
    local_ip_text = StringProperty("Detecting local IP...")
    progress_value = NumericProperty(0.0)
    scanning = BooleanProperty(False)

    filter_hostname = BooleanProperty(True)
    ping_first = BooleanProperty(True)
    resolve_dns = BooleanProperty(True)

    vault_status_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = LanScanner(timeout=0.4, ping_timeout=1.0)
        self.stop_event: Optional[threading.Event] = None
        self.rows: Dict[str, Dict[str, Any]] = {}

        self.vault_path: Optional[str] = None
        self.vault_items: List[Dict[str, str]] = []

        self._auto_cidr_value = ""
        self._netinfo_lock = threading.Lock()
        self._netinfo_event = None
        self._results_switch_delay_sec = 2.0

        Clock.schedule_once(self._init_storage, 0)
        Clock.schedule_once(self._start_auto_network_refresh, 0)

    def _start_auto_network_refresh(self, _dt):
        self.request_network_info_refresh()
        if self._netinfo_event is None:
            self._netinfo_event = Clock.schedule_interval(
                lambda __dt: self.request_network_info_refresh(), 1.0
            )

    def request_network_info_refresh(self):
        if not self._netinfo_lock.acquire(blocking=False):
            return

        def worker():
            try:
                ip = self.scanner.get_local_ip()
                parts = (ip or "").split(".")
                subnet = ".".join(parts[:3]) + ".0/24" if len(parts) == 4 else ""

                def apply_ui():
                    try:
                        self.local_ip_text = (
                            f"Local IP: {ip} | Network: {subnet}"
                            if subnet
                            else f"Local IP: {ip or 'unknown'}"
                        )
                        if subnet and "cidr_input" in self.ids:
                            current = (self.ids.cidr_input.text or "").strip()
                            if (not current) or (current == self._auto_cidr_value):
                                self.ids.cidr_input.text = subnet
                                self._auto_cidr_value = subnet
                    except Exception:
                        pass

                self._ui(apply_ui)
            finally:
                try:
                    self._netinfo_lock.release()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    # -------- Details popup --------
    def show_details(self, ip: str):
        ip = str(ip)
        row = self.rows.get(ip, {})
        open_ports = sorted(list(row.get("ports") or []))
        hostname = row.get("hostname") or ""

        if open_ports:
            lines = [f"{p}: {PORT_INFO.get(int(p), 'Unknown service')}" for p in open_ports]
            ports_text = "\n".join(lines)
        else:
            ports_text = "(no open ports detected)"

        root_box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))

        title_lbl = Label(
            text=f"Details for {ip}" + (f" ({hostname})" if hostname else ""),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            valign="middle",
        )
        title_lbl.bind(size=lambda *_: setattr(title_lbl, "text_size", (title_lbl.width, title_lbl.height)))
        root_box.add_widget(title_lbl)

        ports_lbl = Label(text=f"Open ports:\n{ports_text}", halign="left", valign="top")
        ports_lbl.bind(size=lambda *_: setattr(ports_lbl, "text_size", (ports_lbl.width, None)))
        root_box.add_widget(ports_lbl)

        btn_close = Button(text="Close", size_hint_y=None, height=dp(44))
        root_box.add_widget(btn_close)

        popup = Popup(title="Details", content=root_box, size_hint=(0.92, 0.70))
        btn_close.bind(on_release=popup.dismiss)
        popup.open()

    # ---------- Vault storage ----------
    def _init_storage(self, _dt):
        try:
            app = App.get_running_app()
            base = getattr(app, "user_data_dir", None) or os.getcwd()
            os.makedirs(base, exist_ok=True)
            self.vault_path = os.path.join(base, "wifi_vault.json")
            self._vault_load()
            self.vault_status_text = f"Storage: {self.vault_path}"
            self.refresh_vault_view()
        except Exception as e:
            self.vault_status_text = f"Storage init error: {e}"

    def _vault_load(self):
        self.vault_items = []
        if not self.vault_path or not os.path.exists(self.vault_path):
            return
        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                cleaned = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    ssid = str(item.get("ssid", "")).strip()
                    password = str(item.get("password", ""))
                    if ssid:
                        cleaned.append({"ssid": ssid, "password": password})
                self.vault_items = cleaned
        except Exception:
            self.vault_items = []

    def _vault_write(self):
        if not self.vault_path:
            raise RuntimeError("Storage path is not ready.")
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump(self.vault_items, f, ensure_ascii=False, indent=2)

    def _make_vault_label(self, text: str, hint_x: float, bold: bool = False, align: str = "left") -> Label:
        lbl = Label(
            text=(f"[b]{text}[/b]" if bold else text),
            markup=bold,
            halign=align,
            valign="middle",
            size_hint=(hint_x, 1),
            shorten=True,
            shorten_from="right",
        )

        def _upd(*_):
            lbl.text_size = (max(0, lbl.width - dp(10)), lbl.height)

        lbl.bind(size=_upd)
        _upd()
        return lbl

    def vault_save(self):
        try:
            ssid = (self.ids.vault_ssid.text or "").strip()
            password = self.ids.vault_pass.text or ""
            if not ssid:
                self.show_error("SSID is empty.")
                return

            updated = False
            for item in self.vault_items:
                if item.get("ssid") == ssid:
                    item["password"] = password
                    updated = True
                    break
            if not updated:
                self.vault_items.append({"ssid": ssid, "password": password})

            self.vault_items.sort(key=lambda x: (x.get("ssid", "").lower()))
            self._vault_write()

            self.vault_status_text = f"Saved: {ssid}"
            self.ids.vault_ssid.text = ""
            self.ids.vault_pass.text = ""
            self.refresh_vault_view()
        except Exception as e:
            self.show_error(str(e))

    def vault_confirm_delete(self, ssid: str):
        ssid = str(ssid)

        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        lbl = Label(text=f"Do you want to delete this entry?\n\nSSID: {ssid}", halign="left", valign="middle")
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
        box.add_widget(lbl)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        btn_ok = Button(text="OK")
        btn_cancel = Button(text="Cancel")
        btn_row.add_widget(btn_ok)
        btn_row.add_widget(btn_cancel)
        box.add_widget(btn_row)

        popup = Popup(title="Confirm delete", content=box, size_hint=(0.9, 0.35))

        def do_ok(*_):
            popup.dismiss()
            self.vault_delete(ssid)

        btn_ok.bind(on_release=do_ok)
        btn_cancel.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def vault_delete(self, ssid: str):
        try:
            ssid = str(ssid)
            self.vault_items = [x for x in self.vault_items if x.get("ssid") != ssid]
            self._vault_write()
            self.vault_status_text = f"Deleted: {ssid}"
            self.refresh_vault_view()
        except Exception as e:
            self.show_error(str(e))

    def refresh_vault_view(self):
        try:
            grid = self.ids.vault_grid
        except Exception:
            return

        grid.clear_widgets()

        ssid_x = 0.34
        pass_x = 0.46
        act_x = 0.20

        header = VaultRow()
        header.add_widget(self._make_vault_label("SSID", ssid_x, bold=True, align="left"))
        header.add_widget(self._make_vault_label("Password", pass_x, bold=True, align="left"))
        header.add_widget(self._make_vault_label("Action", act_x, bold=True, align="center"))
        grid.add_widget(header)

        for item in self.vault_items:
            ssid = item.get("ssid", "")
            password = item.get("password", "")

            row = VaultRow()
            row.add_widget(self._make_vault_label(ssid, ssid_x, align="left"))
            row.add_widget(self._make_vault_label(password, pass_x, align="left"))

            btn = Button(text="Delete", size_hint=(act_x, 1), size_hint_min_x=dp(90))
            btn.bind(on_release=lambda _btn, s=ssid: self.vault_confirm_delete(s))
            row.add_widget(btn)

            grid.add_widget(row)

    # ---------- UI helpers ----------
    def show_error(self, message):
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        lbl = Label(text=str(message))
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
        btn = Button(text="OK", size_hint_y=None, height=dp(44))
        box.add_widget(lbl)
        box.add_widget(btn)
        popup = Popup(title="Error", content=box, size_hint=(0.9, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def _ui(self, func, *args, **kwargs):
        Clock.schedule_once(lambda _dt: func(*args, **kwargs), 0)

    # ---------- Targets / ports ----------
    def _build_targets(self):
        cidr_str = (self.ids.cidr_input.text or "").strip()
        if cidr_str:
            try:
                net = ipaddress.ip_network(cidr_str, strict=False)
            except Exception:
                raise ValueError("Invalid CIDR (example: 192.168.1.0/24)")
            return [str(h) for h in net.hosts()]

        ip = self.scanner.get_local_ip()
        parts = ip.split(".")
        if len(parts) != 4:
            raise ValueError("Invalid local IP address")
        cidr = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        net = ipaddress.ip_network(cidr, strict=False)
        return [str(h) for h in net.hosts()]

    @staticmethod
    def _parse_ports_list(text):
        text = (text or "").strip()
        if not text:
            raise ValueError("Ports list is empty")
        result = set()
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                s, e = part.split("-", 1)
                s, e = int(s), int(e)
                if s > e:
                    s, e = e, s
                if s < 1 or e > 65535:
                    raise ValueError(f"Invalid port range: {part}")
                result.update(range(s, e + 1))
            else:
                p = int(part)
                if not (1 <= p <= 65535):
                    raise ValueError(f"Invalid port: {part}")
                result.add(p)
        return sorted(result)

    # ---------- Actions ----------
    def start_scan(self):
        if self.scanning:
            return
        try:
            targets = self._build_targets()
            ports = self._parse_ports_list(self.ids.ports_input.text)
        except ValueError as e:
            self.show_error(str(e))
            return

        if not targets:
            self.show_error("No targets to scan")
            return

        self.clear_results()
        self.scanning = True
        self.stop_event = threading.Event()
        self.progress_value = 0.0

        threading.Thread(
            target=self._scan_worker,
            args=(targets, ports, self.ping_first, self.resolve_dns),
            daemon=True
        ).start()

        def switch_to_results(_dt):
            try:
                self.ids.sm.current = "results"
                self.ids.tab_config.state = "normal"
                self.ids.tab_vault.state = "normal"
            except Exception:
                pass

        Clock.schedule_once(switch_to_results, self._results_switch_delay_sec)

    def stop_scan(self):
        if not self.scanning:
            return
        if self.stop_event:
            self.stop_event.set()

    def clear_results(self):
        self.rows.clear()
        try:
            self.ids.rv.data = []
        except Exception:
            pass
        self.progress_value = 0.0

    def _scan_worker(self, targets, ports, ping_first, resolve_dns):
        try:
            total_hosts = len(targets)
            if total_hosts == 0:
                self._ui(self._finish_scan)
                return

            # ----- Ping stage -----
            hosts_done = 0
            if ping_first:
                with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
                    future_map = {ex.submit(self.scanner._ping_host, ip): ip for ip in targets}
                    for fut in concurrent.futures.as_completed(future_map):
                        if self.stop_event.is_set():
                            break
                        ip = future_map[fut]
                        alive = bool(fut.result())
                        self._ui(self._insert_or_update_ip, ip, alive)
                        hosts_done += 1
                        self._ui(self._update_progress, hosts_done, total_hosts)
            else:
                for i, ip in enumerate(targets, start=1):
                    if self.stop_event.is_set():
                        break
                    self._ui(self._insert_or_update_ip, ip, True)
                    hosts_done = i
                    self._ui(self._update_progress, hosts_done, total_hosts)

            if self.stop_event.is_set():
                self._ui(self._finish_scan)
                return

            if not ports:
                self._ui(self._finish_scan)
                return

            # ----- Port stage -----
            total_port_tasks = len(targets) * len(ports)
            done_tasks = 0
            PROGRESS_EVERY = 200

            for ip in targets:
                if self.stop_event.is_set():
                    break

                open_ports: List[int] = []

                def check_port(p):
                    if self.stop_event.is_set():
                        return None
                    return p if self.scanner._scan_port(ip, p) else None

                with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
                    future_map = {ex.submit(check_port, p): p for p in ports}
                    for fut in concurrent.futures.as_completed(future_map):
                        if self.stop_event.is_set():
                            break

                        res = fut.result()
                        if isinstance(res, int):
                            open_ports.append(res)
                            self._ui(self._update_ports_cell, ip, list(open_ports))

                        done_tasks += 1
                        if (done_tasks % PROGRESS_EVERY == 0) or (done_tasks == total_port_tasks):
                            self._ui(self._update_progress, done_tasks, total_port_tasks)

                if resolve_dns:
                    threading.Thread(target=self._resolve_dns_one, args=(ip,), daemon=True).start()

            self._ui(self._finish_scan)
        except Exception as e:
            self._ui(self.show_error, str(e))
            self._ui(self._finish_scan)

    def _resolve_dns_one(self, ip):
        try:
            host = socket.gethostbyaddr(ip)[0]
        except Exception:
            host = ""
        if self.stop_event and self.stop_event.is_set():
            return
        self._ui(self._update_host_cell, ip, host)

    def _update_progress(self, done, total):
        self.progress_value = 0.0 if total <= 0 else float(done) / float(total)

    def _finish_scan(self):
        self.scanning = False

    def _insert_or_update_ip(self, ip, alive):
        row = self.rows.get(ip)
        if row is None:
            row = {"alive": bool(alive), "ports": set(), "hostname": ""}
            self.rows[ip] = row
        else:
            row["alive"] = bool(alive)
        self.refresh_view()

    def _update_ports_cell(self, ip, ports_list):
        row = self.rows.get(ip)
        if row is None:
            row = {"alive": False, "ports": set(), "hostname": ""}
            self.rows[ip] = row
        row["ports"] = set(ports_list)
        if row["ports"] and not row["alive"]:
            row["alive"] = True
        self.refresh_view()

    def _update_host_cell(self, ip, host):
        row = self.rows.get(ip)
        if row is None:
            row = {"alive": False, "ports": set(), "hostname": ""}
            self.rows[ip] = row
        row["hostname"] = host or ""
        self.refresh_view()

    def refresh_view(self):
        data = []

        def ip_key(s):
            if s.count(".") == 3:
                try:
                    return list(map(int, s.split(".")))
                except Exception:
                    return [999, 999, 999, 999]
            return [999, 999, 999, 999]

        for ips in sorted(self.rows.keys(), key=ip_key):
            row = self.rows[ips]
            hostname = row.get("hostname") or ""
            alive_bool = bool(row.get("alive"))

            if self.filter_hostname:
                if not hostname:
                    continue
            else:
                if not alive_bool:
                    continue

            ports = row.get("ports") or set()
            ports_text = ", ".join(str(p) for p in sorted(ports)) if ports else ""
            alive_text = "True" if alive_bool else "False"

            if len(hostname) > 10:
                hostname = hostname[:10]

            ip_display = str(ips).replace("192.168.", "IP: ")

            data.append({
                "ip": ip_display,
                "real_ip": str(ips),
                "alive": alive_text,
                "ports": ports_text,
                "host": hostname,
            })

        try:
            self.ids.rv.data = data
        except Exception:
            pass


class MainHostScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content = MainScreen()
        self.add_widget(self.content)


# ==================== App ====================

class LanScannerApp(App):
    name = "LanScannerApp"

    DEFAULT_M: Tuple[int, ...] = (6, 3, 0, 4, 2, 5, 8)  # M
    DEFAULT_G: Tuple[int, ...] = (0, 1, 2, 5, 8, 7, 6, 3, 4)  # G

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.m_pattern: Tuple[int, ...] = self.DEFAULT_M
        self.g_pattern: Tuple[int, ...] = self.DEFAULT_G
        self.pattern_store: Optional[PatternStore] = None
        self.is_mobile: bool = False

    def build(self):
        Builder.load_string(KV)

        self.is_mobile = self._detect_mobile()

        base = getattr(self, "user_data_dir", None) or os.getcwd()
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass

        patterns_path = os.path.join(base, "patterns.json")
        self.pattern_store = PatternStore(patterns_path)

        loaded = self.pattern_store.load()
        if loaded:
            self.m_pattern = loaded["m_pattern"]
            self.g_pattern = loaded["g_pattern"]
        else:
            self.save_patterns()

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainHostScreen(name="main"))
        sm.add_widget(PasswordSettingsScreen(name="pw"))
        sm.current = "login"
        return sm

    def _detect_mobile(self) -> bool:
        try:
            return str(kivy_platform) in ("android", "ios")
        except Exception:
            return False

    def save_patterns(self) -> bool:
        if not self.pattern_store:
            return False
        extra = {
            "saved_on_platform": ("phone" if self.is_mobile else "laptop/desktop"),
            "kivy_user_data_dir": getattr(self, "user_data_dir", None),
        }
        return self.pattern_store.save(self.m_pattern, self.g_pattern, extra=extra)

    def go_to_login(self):
        try:
            self.root.current = "login"
        except Exception:
            pass

    def go_to_main(self):
        try:
            self.root.current = "main"
        except Exception:
            pass

    def go_to_password_settings(self):
        try:
            self.root.current = "pw"
        except Exception:
            pass

    def on_login_pattern(self, entered: Tuple[int, ...], lock: PatternLock):
        if not entered:
            lock.reset()
            return

        is_m = (entered == self.m_pattern)
        is_g = (entered == self.g_pattern)

        if is_m or is_g:
            lock.set_feedback("success")

            def later(_dt):
                if is_m:
                    self.go_to_main()
                else:
                    self.go_to_password_settings()
                try:
                    lock.reset()
                except Exception:
                    pass

            Clock.schedule_once(later, 1.0)
            return

        lock.set_feedback("error")
        Clock.schedule_once(lambda _dt: lock.reset(), 1.0)

    # fallback
    def on_pattern_entered(self, entered: Tuple[int, ...], lock: PatternLock):
        self.on_login_pattern(entered, lock)


if __name__ == "__main__":
    LanScannerApp().run()
