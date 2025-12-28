import threading
import socket
import subprocess
import platform
import ipaddress
import concurrent.futures

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button


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
                # Linux / Android / macOS: -c 1, -W <seconds> (on some systems)
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
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _scan_port(self, ip, port):
        try:
            with socket.create_connection((ip, port), timeout=self.timeout):
                return True
        except Exception:
            return False


# ==================== Kivy UI ====================

KV = '''
<Row@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(32)
    spacing: dp(4)
    ip: ''
    alive: ''
    ports: ''
    host: ''
    Label:
        text: root.ip
        size_hint_x: 0.28
        text_size: self.size
        valign: 'middle'
        halign: 'left'
    Label:
        text: root.alive
        size_hint_x: 0.12
        text_size: self.size
        valign: 'middle'
        halign: 'center'
    Label:
        text: root.ports
        size_hint_x: 0.30
        text_size: self.size
        valign: 'middle'
        halign: 'left'
    Label:
        text: root.host
        size_hint_x: 0.30
        text_size: self.size
        valign: 'middle'
        halign: 'left'


<MainScreen>:
    orientation: 'vertical'
    padding: dp(8)
    spacing: dp(6)

    # نوار تب‌ها
    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(6)
        ToggleButton:
            text: 'Setting'
            group: 'tabs'
            state: 'down'
            on_state:
                if self.state == 'down': root.ids.sm.current = 'config'
        ToggleButton:
            text: 'Results'
            group: 'tabs'
            on_state:
                if self.state == 'down': root.ids.sm.current = 'results'

    ScreenManager:
        id: sm

        # صفحه تنظیمات
        Screen:
            name: 'config'
            ScrollView:
                do_scroll_x: False
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)

                    # نمایش IP محلی + SSID
                    BoxLayout:
                        size_hint_y: None
                        height: dp(32)
                        Label:
                            text: root.local_ip_text
                            text_size: self.size
                            halign: 'left'
                            valign: 'middle'

                    # انتخاب Mode
                    BoxLayout:
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(6)
                        Label:
                            text: 'Mode:'
                            size_hint_x: None
                            width: dp(70)
                        Spinner:
                            id: mode_spinner
                            text: 'Local /24'
                            values: ['Local /24', 'CIDR', 'Range']
                            size_hint_x: 1
                            on_text: root.on_mode_change(self.text)

                    # ورودی CIDR
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
                            text: '192.168.1.0/24'
                            multiline: False
                            hint_text: '192.168.1.0/24'

                    # Range: Start / End
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
                            text: '192.168.1.1'
                            multiline: False
                            hint_text: '192.168.1.1'
                        Label:
                            text: 'End:'
                            size_hint_x: None
                            width: dp(60)
                        TextInput:
                            id: end_ip_input
                            text: '192.168.1.254'
                            multiline: False
                            hint_text: '192.168.1.254'

                    # Ports
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
                            hint_text: '80,443 or 1000-2000'

                    # Toggle ها ردیف ۱ (Ping و DNS)
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

                    # Toggle hostname filter در ردیف جدا
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

                    # دکمه‌های Start / Stop / Clear
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

        # صفحه نتایج
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
                        id: progress_bar
                        max: 1.0
                        value: root.progress_value
                    Label:
                        id: status_label
                        text: root.status_text
                        size_hint_x: None
                        width: dp(220)
                        text_size: self.size
                        halign: 'left'
                        valign: 'middle'

                RecycleView:
                    id: rv
                    viewclass: 'Row'
                    RecycleBoxLayout:
                        default_size: None, dp(32)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        orientation: 'vertical'
'''


class MainScreen(BoxLayout):
    status_text = StringProperty("Ready")
    local_ip_text = StringProperty("Detecting local IP...")
    progress_value = NumericProperty(0.0)
    scanning = BooleanProperty(False)

    filter_hostname = BooleanProperty(True)
    ping_first = BooleanProperty(True)
    resolve_dns = BooleanProperty(True)

    mode = StringProperty("local")  # "local", "cidr", "range"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = LanScanner(timeout=0.4, ping_timeout=1.0)
        self.stop_event = None
        # rows: ip -> {"alive": bool, "ports": set(), "hostname": str}
        self.rows = {}
        Clock.schedule_once(self._init_local_ip, 0)

    # ---- گرفتن SSID روی اندروید (در دسکتاپ None برمی‌گردد) ----
    def get_current_ssid(self):
        try:
            from jnius import autoclass
            from android import mActivity
        except ImportError:
            # روی دسکتاپ یا جایی که android/jnius نیست
            return None
        except Exception:
            return None

        try:
            Context = autoclass('android.content.Context')
            WifiManager = autoclass('android.net.wifi.WifiManager')

            wifi_service = mActivity.getSystemService(Context.WIFI_SERVICE)
            if not wifi_service:
                return None

            info = wifi_service.getConnectionInfo()
            if not info:
                return None

            ssid = info.getSSID()
            if not ssid:
                return None
            # معمولاً با " در ابتدا و انتها برمی‌گردد
            ssid = str(ssid)
            if ssid.startswith('"') and ssid.endswith('"'):
                ssid = ssid[1:-1]
            return ssid
        except Exception:
            return None

    def _init_local_ip(self, dt):
        try:
            ip = self.scanner.get_local_ip()
            parts = ip.split(".")
            if len(parts) == 4:
                subnet = ".".join(parts[:3]) + ".0/24"
                ssid = self.get_current_ssid()
                if ssid:
                    self.local_ip_text = f"Local IP: {ip} | Network: {subnet} | WiFi: {ssid}"
                else:
                    self.local_ip_text = f"Local IP: {ip} | Network: {subnet}"
            else:
                self.local_ip_text = f"Local IP: {ip}"
        except Exception:
            self.local_ip_text = "Local IP: unknown"

    # ---------- UI helpers ----------

    def show_error(self, message):
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        lbl = Label(text=message)
        btn = Button(text="OK", size_hint_y=None, height=dp(40))
        box.add_widget(lbl)
        box.add_widget(btn)
        popup = Popup(title="Error", content=box, size_hint=(0.9, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def on_mode_change(self, text):
        if text.startswith("Local"):
            self.mode = "local"
        elif text == "CIDR":
            self.mode = "cidr"
        else:
            self.mode = "range"

    def _ui(self, func, *args, **kwargs):
        # Schedule a function to run on the main (UI) thread
        Clock.schedule_once(lambda dt: func(*args, **kwargs), 0)

    # ---------- Config / targets / ports ----------

    def _build_targets(self):
        if self.mode == "local":
            ip = self.scanner.get_local_ip()
            parts = ip.split(".")
            if len(parts) != 4:
                raise ValueError("Invalid local IP address")
            cidr = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            net = ipaddress.ip_network(cidr, strict=False)
            return [str(h) for h in net.hosts()]

        elif self.mode == "cidr":
            cidr_str = self.ids.cidr_input.text.strip()
            if not cidr_str:
                raise ValueError("CIDR is empty")
            try:
                net = ipaddress.ip_network(cidr_str, strict=False)
            except Exception:
                raise ValueError("Invalid CIDR (example: 192.168.1.0/24)")
            return [str(h) for h in net.hosts()]

        else:  # range
            start = self.ids.start_ip_input.text.strip()
            end = self.ids.end_ip_input.text.strip()
            if not start or not end:
                raise ValueError("Start and End IP must not be empty")
            try:
                a = int(ipaddress.IPv4Address(start))
                b = int(ipaddress.IPv4Address(end))
            except Exception:
                raise ValueError("Invalid IP range")
            if a > b:
                a, b = b, a
            return [str(ipaddress.IPv4Address(i)) for i in range(a, b + 1)]

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
                try:
                    s, e = part.split("-", 1)
                    s, e = int(s), int(e)
                    if s > e:
                        s, e = e, s
                    if s < 1 or e > 65535:
                        raise ValueError
                    result.update(range(s, e + 1))
                except Exception:
                    raise ValueError(f"Invalid port range: {part}")
            else:
                try:
                    p = int(part)
                    if not (1 <= p <= 65535):
                        raise ValueError
                except Exception:
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

        self.clear_results()
        self.scanning = True
        self.stop_event = threading.Event()
        self.status_text = "Starting scan..."
        self.progress_value = 0.0

        th = threading.Thread(
            target=self._scan_worker,
            args=(targets, ports, self.ping_first, self.resolve_dns),
            daemon=True
        )
        th.start()

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

            # Ping phase
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

            # Port scan phase
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
                    threading.Thread(
                        target=self._resolve_dns_one,
                        args=(ip,),
                        daemon=True
                    ).start()

            if self.stop_event.is_set():
                self._ui(self._finish_scan, "Stopped")
            else:
                self._ui(self._finish_scan, "Done")
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
        if total <= 0:
            self.progress_value = 0.0
        else:
            self.progress_value = float(done) / float(total)

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
        # If any open port found, treat host as alive
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
        for ip in sorted(self.rows.keys(), key=lambda s: list(map(int, s.split("."))) if s.count(".") == 3 else s):
            row = self.rows[ip]
            hostname = row.get("hostname") or ""
            if self.filter_hostname and not hostname:
                continue
            ports = row.get("ports") or set()
            ports_text = ", ".join(str(p) for p in sorted(ports)) if ports else ""
            alive_symbol = "✅" if row.get("alive") else "❌"
            data.append({
                "ip": ip,
                "alive": alive_symbol,
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
