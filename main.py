import os
import json
import threading
import socket
import subprocess
import platform
import ipaddress
import concurrent.futures
import re

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button

# Widgets referenced in KV
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout


# ==================== Scanner logic ====================

class LanScanner:
    def __init__(self, timeout=0.5, ping_timeout=1.0):
        self.timeout = float(timeout)
        self.ping_timeout = float(ping_timeout)

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
        sys_name = platform.system().lower()
        try:
            if sys_name == "windows":
                cmd = ["ping", "-n", "1", "-w", str(int(self.ping_timeout * 1000)), ip]
            else:
                cmd = ["ping", "-c", "1", "-W", str(max(1, int(self.ping_timeout))), ip]
        except Exception:
            cmd = ["ping", "-c", "1", ip]

        try:
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


# ==================== UI helper widgets ====================

class VaultRow(BoxLayout):
    """Framed row widget for Vault list."""
    pass


# ==================== Port descriptions ====================

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


def format_bps(bytes_per_sec: float) -> str:
    if bytes_per_sec is None:
        return "N/A"
    b = float(bytes_per_sec)
    if b < 1024:
        return f"{b:.0f} B/s"
    kb = b / 1024.0
    if kb < 1024:
        return f"{kb:.1f} KB/s"
    mb = kb / 1024.0
    if mb < 1024:
        return f"{mb:.2f} MB/s"
    gb = mb / 1024.0
    return f"{gb:.2f} GB/s"


# ==================== Kivy UI ====================

KV = r'''
#:import dp kivy.metrics.dp

# همه TextInput ها وسط‌چین (افقی) + تا حد ممکن عمودی برای تک‌خطی‌ها
<TextInput>:
    halign: 'center'
    padding_y: max(0, (self.height - self.line_height) / 2)

<Row@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(38)
    spacing: dp(6)
    padding: dp(6)
    ip: ''
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
        on_release: app.root.show_details(root.ip)


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

    # Tabs
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
            id: tab_results
            text: 'Results'
            group: 'tabs'
            background_normal: ''
            background_down: ''
            background_color: (0.15, 0.55, 0.95, 1) if self.state == 'down' else (0.18, 0.18, 0.18, 1)
            color: 1,1,1,1
            on_state:
                if self.state == 'down': root.ids.sm.current = 'results'

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

        # Settings screen
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
                    spacing: dp(6)

                    # Local IP (چپ) + WiFi (راست) در یک ردیف
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(10)

                        Label:
                            text: root.local_ip_text
                            text_size: self.size
                            halign: 'left'
                            valign: 'middle'
                            size_hint_x: 0.6

                        Label:
                            text: root.wifi_name_text
                            text_size: self.size
                            halign: 'right'
                            valign: 'middle'
                            size_hint_x: 0.4

                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(6)
                        Button:
                            text: 'Refresh network info'
                            on_press: root.refresh_network_info()

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(6)
                        Label:
                            text: 'CIDR:'
                            size_hint_x: None
                            width: dp(70)
                        TextInput:
                            id: cidr_input
                            text: ''
                            multiline: False
                            hint_text: '192.168.1.0/24'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(6)
                        Label:
                            text: 'Start:'
                            size_hint_x: None
                            width: dp(70)
                        TextInput:
                            id: start_ip_input
                            text: ''
                            multiline: False
                            hint_text: '192.168.1.1'
                        Label:
                            text: 'End:'
                            size_hint_x: None
                            width: dp(60)
                        TextInput:
                            id: end_ip_input
                            text: ''
                            multiline: False
                            hint_text: '192.168.1.254'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(6)
                        Label:
                            text: 'Ports:'
                            size_hint_x: None
                            width: dp(70)
                        TextInput:
                            id: ports_input
                            text: '1-1024'
                            multiline: False
                            hint_text: '80,443 یا 1000-2000'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(6)
                        ToggleButton:
                            id: ping_toggle
                            text: 'Ping first: ON' if self.state == 'down' else 'Ping first: OFF'
                            state: 'down'
                            size_hint_x: 0.5
                            on_state:
                                root.ping_first = (self.state == 'down')
                                self.text = 'Ping first: ON' if self.state == 'down' else 'Ping first: OFF'
                        ToggleButton:
                            id: dns_toggle
                            text: 'Resolve DNS: ON' if self.state == 'down' else 'Resolve DNS: OFF'
                            state: 'down'
                            size_hint_x: 0.5
                            on_state:
                                root.resolve_dns = (self.state == 'down')
                                self.text = 'Resolve DNS: ON' if self.state == 'down' else 'Resolve DNS: OFF'

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(6)
                        ToggleButton:
                            id: filter_toggle
                            text: 'Only with hostname: ON' if self.state == 'down' else 'Only with hostname: OFF'
                            state: 'down'
                            size_hint_x: 1
                            on_state:
                                root.filter_hostname = (self.state == 'down')
                                self.text = 'Only with hostname: ON' if self.state == 'down' else 'Only with hostname: OFF'
                                root.refresh_view()

                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(8)
                        Button:
                            id: start_btn
                            text: 'Start scan'
                            disabled: root.scanning
                            on_press: root.start_scan()
                        Button:
                            id: stop_btn
                            text: 'Stop'
                            disabled: not root.scanning
                            on_press: root.stop_scan()
                        Button:
                            text: 'Clear'
                            on_press: root.clear_results()

        # Results screen
        Screen:
            name: 'results'
            BoxLayout:
                orientation: 'vertical'
                spacing: dp(6)

                # ProgressBar فیت + درصد (بدون نوشته زیر/چپ)
                BoxLayout:
                    size_hint_y: None
                    height: dp(30)
                    spacing: dp(6)
                    padding: 0, 0, 0, 0

                    ProgressBar:
                        id: progress_bar
                        max: 1.0
                        value: root.progress_value
                        size_hint_x: 1

                    Label:
                        id: percent_label
                        text: str(int(root.progress_value * 100)) + '%'
                        size_hint_x: None
                        width: dp(60)
                        text_size: self.size
                        halign: 'right'
                        valign: 'middle'

                RecycleView:
                    id: rv
                    bar_width: dp(10)
                    scroll_type: ['bars', 'content']
                    viewclass: 'Row'
                    RecycleBoxLayout:
                        default_size: None, dp(38)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(6)
                        orientation: 'vertical'

        # Vault screen
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
                    id: vault_scroll
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
                        width: self.parent.width
                        spacing: dp(6)
                        padding: dp(6)
'''


class MainScreen(BoxLayout):
    status_text = StringProperty("Ready")  # دیگر نمایش داده نمی‌شود (طبق درخواست)
    local_ip_text = StringProperty("Detecting local IP...")
    wifi_name_text = StringProperty("WiFi (SSID): detecting...")
    progress_value = NumericProperty(0.0)
    scanning = BooleanProperty(False)

    filter_hostname = BooleanProperty(True)
    ping_first = BooleanProperty(True)
    resolve_dns = BooleanProperty(True)

    vault_status_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = LanScanner(timeout=0.4, ping_timeout=1.0)
        self.stop_event = None
        self.rows = {}

        # Vault storage
        self.vault_path = None
        self.vault_items = []  # [{"ssid": str, "password": str}]

        # برای autofill کردن CIDR
        self._auto_cidr_value = ""

        Clock.schedule_once(self._init_local_info, 0)
        Clock.schedule_once(self._init_storage, 0)

    # ---------------- Details popup ----------------
    def show_details(self, ip: str):
        ip = str(ip)
        row = self.rows.get(ip, {})
        open_ports = sorted(list(row.get("ports") or []))
        hostname = row.get("hostname") or ""

        if open_ports:
            lines = []
            for p in open_ports:
                desc = PORT_INFO.get(int(p), "Unknown service")
                lines.append(f"{p}: {desc}")
            ports_text = "\n".join(lines)
        else:
            ports_text = "(no open ports detected)"

        note = (
            "Note: Per-device download/upload speed is not available here.\n"
            "Displayed speed is total network throughput of this device."
        )

        root_box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        title_lbl = Label(
            text=f"Details for {ip}" + (f" ({hostname})" if hostname else ""),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            valign="middle",
        )
        title_lbl.bind(size=lambda *_: setattr(title_lbl, "text_size", (title_lbl.width, title_lbl.height)))
        root_box.add_widget(title_lbl)

        ports_lbl = Label(
            text=f"Open ports:\n{ports_text}",
            halign="left",
            valign="top",
        )
        ports_lbl.bind(size=lambda *_: setattr(ports_lbl, "text_size", (ports_lbl.width, None)))
        root_box.add_widget(ports_lbl)

        # اسم Download / Upload مشخص شد
        speed_lbl = Label(
            text="Speed: Download : N/A   Upload : N/A",
            size_hint_y=None,
            height=dp(28),
            halign="left",
            valign="middle",
        )
        speed_lbl.bind(size=lambda *_: setattr(speed_lbl, "text_size", (speed_lbl.width, speed_lbl.height)))
        root_box.add_widget(speed_lbl)

        note_lbl = Label(
            text=note,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(52),
        )
        note_lbl.bind(size=lambda *_: setattr(note_lbl, "text_size", (note_lbl.width, None)))
        root_box.add_widget(note_lbl)

        btn_close = Button(text="Close", size_hint_y=None, height=dp(44))
        root_box.add_widget(btn_close)

        popup = Popup(title="Details", content=root_box, size_hint=(0.92, 0.75))
        btn_close.bind(on_release=popup.dismiss)

        # 1s speed updates if psutil is available
        try:
            import psutil  # type: ignore

            last = {"sent": None, "recv": None}

            def tick(_dt):
                try:
                    c = psutil.net_io_counters()
                    sent = int(c.bytes_sent)
                    recv = int(c.bytes_recv)

                    if last["sent"] is None:
                        last["sent"] = sent
                        last["recv"] = recv
                        speed_lbl.text = "Speed: Download : measuring...   Upload : measuring..."
                        return

                    up = sent - last["sent"]
                    down = recv - last["recv"]
                    last["sent"] = sent
                    last["recv"] = recv

                    speed_lbl.text = f"Speed: Download : {format_bps(down)}   Upload : {format_bps(up)}"
                except Exception:
                    speed_lbl.text = "Speed: Download : N/A   Upload : N/A"

            ev = Clock.schedule_interval(tick, 1.0)

            def on_dismiss(_popup):
                try:
                    ev.cancel()
                except Exception:
                    pass

            popup.bind(on_dismiss=on_dismiss)
        except Exception:
            speed_lbl.text = "Speed: Download : N/A   Upload : N/A (psutil not available)"

        popup.open()

    # ---------- Storage ----------
    def _init_storage(self, dt):
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

    # ---------- Vault helpers (responsive) ----------
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

    # ---------- Vault (Save / Delete with confirmation) ----------
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

        # نسبت‌های ستون‌ها (Responsive)
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

            btn = Button(
                text="Delete",
                size_hint=(act_x, 1),
                size_hint_min_x=dp(90),
            )
            btn.bind(on_release=lambda _btn, s=ssid: self.vault_confirm_delete(s))
            row.add_widget(btn)

            grid.add_widget(row)

    # ---------- Local IP + SSID ----------
    def get_current_ssid_android(self):
        try:
            from jnius import autoclass
            from android import mActivity
        except Exception:
            return None

        try:
            Context = autoclass('android.content.Context')
            wifi_service = mActivity.getSystemService(Context.WIFI_SERVICE)
            if not wifi_service:
                return None
            info = wifi_service.getConnectionInfo()
            if not info:
                return None
            ssid = info.getSSID()
            if not ssid:
                return None
            ssid = str(ssid)
            if ssid.startswith('"') and ssid.endswith('"'):
                ssid = ssid[1:-1]
            if ssid.lower() in ("<unknown ssid>", "unknown ssid"):
                return None
            return ssid
        except Exception:
            return None

    def _get_wifi_ssid_windows(self):
        try:
            proc = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            m = re.search(r'^\s*SSID\s*:\s*(.+)\s*$', out, flags=re.MULTILINE)
            return m.group(1).strip() if m else None
        except Exception:
            return None

    def _get_wifi_ssid_linux(self):
        try:
            proc = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if proc.returncode != 0:
                return None
            for line in (proc.stdout or "").splitlines():
                if line.startswith("yes:"):
                    ssid = line.split(":", 1)[1].strip()
                    return ssid or None
            return None
        except Exception:
            return None

    def _get_wifi_ssid_macos(self):
        try:
            airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            proc = subprocess.run([airport, "-I"], capture_output=True, text=True, timeout=2.0)
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            m = re.search(r'^\s*SSID:\s*(.+)\s*$', out, flags=re.MULTILINE)
            return m.group(1).strip() if m else None
        except Exception:
            return None

    def get_wifi_ssid(self):
        ssid = self.get_current_ssid_android()
        if ssid:
            return ssid
        sys_name = platform.system().lower()
        if sys_name == "windows":
            return self._get_wifi_ssid_windows()
        if sys_name == "darwin":
            return self._get_wifi_ssid_macos()
        if sys_name == "linux":
            return self._get_wifi_ssid_linux()
        return None

    def refresh_network_info(self):
        self._init_local_info(0)

    def _init_local_info(self, dt):
        subnet = ""
        try:
            ip = self.scanner.get_local_ip()
            parts = ip.split(".")
            if len(parts) == 4:
                subnet = ".".join(parts[:3]) + ".0/24"
                self.local_ip_text = f"Local IP: {ip} | Network: {subnet}"
            else:
                self.local_ip_text = f"Local IP: {ip}"
        except Exception:
            self.local_ip_text = "Local IP: unknown"

        ssid = self.get_wifi_ssid()
        self.wifi_name_text = f"WiFi (SSID): {ssid}" if ssid else "WiFi (SSID): not detected / not connected"

        # اگر کاربر CIDR را دستی عوض نکرده باشد، CIDR را با شبکه محلی autofill کن
        try:
            if subnet and "cidr_input" in self.ids:
                current = (self.ids.cidr_input.text or "").strip()
                if (not current) or (current == self._auto_cidr_value):
                    self.ids.cidr_input.text = subnet
                    self._auto_cidr_value = subnet
        except Exception:
            pass

    # ---------- UI helpers ----------
    def show_error(self, message):
        box = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        lbl = Label(text=str(message))
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, None)))
        btn = Button(text="OK", size_hint_y=None, height=dp(44))
        box.add_widget(lbl)
        box.add_widget(btn)
        popup = Popup(title="Error", content=box, size_hint=(0.9, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def _ui(self, func, *args, **kwargs):
        Clock.schedule_once(lambda dt: func(*args, **kwargs), 0)

    # ---------- Config / targets / ports ----------
    def _build_targets(self):
        """
        بدون Mode:
        - اگر Start و End پر باشند => Range
        - اگر CIDR پر باشد => CIDR
        - اگر هیچکدام نبود => Local /24
        """
        start = (self.ids.start_ip_input.text or "").strip()
        end = (self.ids.end_ip_input.text or "").strip()
        cidr_str = (self.ids.cidr_input.text or "").strip()

        # Range
        if start or end:
            if not start or not end:
                raise ValueError("Start و End باید هر دو پر باشند.")
            try:
                a = int(ipaddress.IPv4Address(start))
                b = int(ipaddress.IPv4Address(end))
            except Exception:
                raise ValueError("Invalid IP range")
            if a > b:
                a, b = b, a
            return [str(ipaddress.IPv4Address(i)) for i in range(a, b + 1)]

        # CIDR
        if cidr_str:
            try:
                net = ipaddress.ip_network(cidr_str, strict=False)
            except Exception:
                raise ValueError("Invalid CIDR (example: 192.168.1.0/24)")
            return [str(h) for h in net.hosts()]

        # Local /24 fallback
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

    # ---------- Public actions ----------
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

        # Auto switch to Results tab
        self.ids.sm.current = "results"
        self.ids.tab_results.state = "down"

        self.clear_results()
        self.scanning = True
        self.stop_event = threading.Event()
        self.status_text = "Starting scan..."
        self.progress_value = 0.0

        threading.Thread(
            target=self._scan_worker,
            args=(targets, ports, self.ping_first, self.resolve_dns),
            daemon=True
        ).start()

    def stop_scan(self):
        if not self.scanning:
            return
        if self.stop_event:
            self.stop_event.set()
            self.status_text = "Stopping..."

    def clear_results(self):
        self.rows.clear()
        self.ids.rv.data = []
        self.progress_value = 0.0
        self.status_text = "Ready"

    # ---------- Worker thread ----------
    def _scan_worker(self, targets, ports, ping_first, resolve_dns):
        try:
            total_hosts = len(targets)
            if total_hosts == 0:
                self._ui(self._finish_scan, "No targets")
                return

            hosts_done = 0
            if ping_first:
                self._ui(self._set_status, "Pinging hosts...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
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
                self._ui(self._set_status, "Marking hosts alive (no ping)...")
                for i, ip in enumerate(targets, start=1):
                    if self.stop_event.is_set():
                        break
                    self._ui(self._insert_or_update_ip, ip, True)
                    hosts_done = i
                    self._ui(self._update_progress, hosts_done, total_hosts)

            if self.stop_event.is_set():
                self._ui(self._finish_scan, "Stopped")
                return

            if not ports:
                self._ui(self._finish_scan, "No ports specified")
                return

            total_port_tasks = len(targets) * len(ports)
            if total_port_tasks == 0:
                self._ui(self._finish_scan, "Done")
                return

            done_tasks = 0
            self._ui(self._set_status, "Scanning ports...")

            for ip in targets:
                if self.stop_event.is_set():
                    break

                open_ports = []

                def check_port(p):
                    if self.stop_event.is_set():
                        return None
                    return p if self.scanner._scan_port(ip, p) else None

                with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
                    future_map = {ex.submit(check_port, p): p for p in ports}
                    for fut in concurrent.futures.as_completed(future_map):
                        if self.stop_event.is_set():
                            break
                        res = fut.result()
                        if isinstance(res, int):
                            open_ports.append(res)
                            self._ui(self._update_ports_cell, ip, list(open_ports))
                        done_tasks += 1
                        self._ui(self._update_progress, done_tasks, total_port_tasks)

                if resolve_dns:
                    threading.Thread(target=self._resolve_dns_one, args=(ip,), daemon=True).start()

            self._ui(self._finish_scan, "Stopped" if self.stop_event.is_set() else "Done")
        except Exception as e:
            self._ui(self.show_error, str(e))
            self._ui(self._finish_scan, "Error")

    def _resolve_dns_one(self, ip):
        try:
            host = socket.gethostbyaddr(ip)[0]
        except Exception:
            host = ""
        if self.stop_event and self.stop_event.is_set():
            return
        self._ui(self._update_host_cell, ip, host)

    # ---------- Data model / UI update helpers ----------
    def _set_status(self, text):
        self.status_text = text

    def _update_progress(self, done, total):
        self.progress_value = 0.0 if total <= 0 else float(done) / float(total)

    def _finish_scan(self, message):
        self.status_text = message
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

        for ip in sorted(self.rows.keys(), key=ip_key):
            row = self.rows[ip]
            hostname = row.get("hostname") or ""
            if self.filter_hostname and not hostname:
                continue
            ports = row.get("ports") or set()
            ports_text = ", ".join(str(p) for p in sorted(ports)) if ports else ""
            alive_text = "Connect" if row.get("alive") else "Disconnect"
            data.append({
                "ip": ip,
                "alive": alive_text,
                "ports": ports_text,
                "host": hostname,
            })
        self.ids.rv.data = data


class LanScannerApp(App):
    def build(self):
        Builder.load_string(KV)
        return MainScreen()


if __name__ == "__main__":
    LanScannerApp().run()
