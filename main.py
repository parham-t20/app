# lan_scanner_kivy.py
# Simple LAN scanner with Kivy UI (multi-screen, for desktop/mobile)

import os
import csv
import ipaddress
import socket
import platform
import subprocess
import threading
import concurrent.futures

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.properties import (
    StringProperty,
    BooleanProperty,
    NumericProperty,
    ObjectProperty,
)

KV = r'''
#:import dp kivy.metrics.dp

<ConfigScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)

        Label:
            text: 'LanScanner'
            font_size: '22sp'
            size_hint_y: None
            height: self.texture_size[1] + dp(10)

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)

                Label:
                    text: 'Scan mode'
                    size_hint_y: None
                    height: self.texture_size[1] + dp(6)

                BoxLayout:
                    size_hint_y: None
                    height: dp(36)
                    spacing: dp(4)

                    ToggleButton:
                        text: '/24 local'
                        group: 'mode'
                        state: 'down' if app.scan_mode == 'local' else 'normal'
                        on_release: app.scan_mode = 'local'
                    ToggleButton:
                        text: 'CIDR'
                        group: 'mode'
                        state: 'down' if app.scan_mode == 'cidr' else 'normal'
                        on_release: app.scan_mode = 'cidr'
                    ToggleButton:
                        text: 'IP range'
                        group: 'mode'
                        state: 'down' if app.scan_mode == 'range' else 'normal'
                        on_release: app.scan_mode = 'range'

                GridLayout:
                    cols: 2
                    row_default_height: dp(32)
                    row_force_default: True
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(4)

                    Label:
                        text: 'CIDR:'
                    TextInput:
                        text: app.cidr
                        multiline: False
                        on_text: app.cidr = self.text

                    Label:
                        text: 'IP start:'
                    TextInput:
                        text: app.ip_start
                        multiline: False
                        on_text: app.ip_start = self.text

                    Label:
                        text: 'IP end:'
                    TextInput:
                        text: app.ip_end
                        multiline: False
                        on_text: app.ip_end = self.text

                    Label:
                        text: 'Ports mode:'
                    BoxLayout:
                        spacing: dp(4)
                        ToggleButton:
                            text: 'Common'
                            group: 'ports_mode'
                            state: 'down' if app.ports_mode == 'common' else 'normal'
                            on_release: app.ports_mode = 'common'
                        ToggleButton:
                            text: '1..N'
                            group: 'ports_mode'
                            state: 'down' if app.ports_mode == 'range' else 'normal'
                            on_release: app.ports_mode = 'range'
                        ToggleButton:
                            text: 'Custom'
                            group: 'ports_mode'
                            state: 'down' if app.ports_mode == 'custom' else 'normal'
                            on_release: app.ports_mode = 'custom'

                    Label:
                        text: 'N (for 1..N):'
                    TextInput:
                        text: app.end_port
                        multiline: False
                        input_filter: 'int'
                        on_text: app.end_port = self.text

                    Label:
                        text: 'Custom ports:'
                    TextInput:
                        text: app.custom_ports
                        multiline: False
                        on_text: app.custom_ports = self.text

                    Label:
                        text: 'Host threads:'
                    TextInput:
                        text: app.host_workers
                        multiline: False
                        input_filter: 'int'
                        on_text: app.host_workers = self.text

                    Label:
                        text: 'Port threads:'
                    TextInput:
                        text: app.port_workers
                        multiline: False
                        input_filter: 'int'
                        on_text: app.port_workers = self.text

                    Label:
                        text: 'TCP timeout (s):'
                    TextInput:
                        text: app.tcp_timeout
                        multiline: False
                        input_filter: 'float'
                        on_text: app.tcp_timeout = self.text

                    Label:
                        text: 'Ping timeout (s):'
                    TextInput:
                        text: app.ping_timeout
                        multiline: False
                        input_filter: 'float'
                        on_text: app.ping_timeout = self.text

                BoxLayout:
                    size_hint_y: None
                    height: dp(32)
                    spacing: dp(10)

                    BoxLayout:
                        size_hint_x: 0.5
                        spacing: dp(4)
                        Label:
                            text: 'Ping before port scan'
                        CheckBox:
                            active: app.ping_first
                            on_active: app.ping_first = self.active

                    BoxLayout:
                        size_hint_x: 0.5
                        spacing: dp(4)
                        Label:
                            text: 'DNS resolve'
                        CheckBox:
                            active: app.resolve_dns
                            on_active: app.resolve_dns = self.active

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)

            Button:
                text: 'Start scan'
                on_release: app.start_scan()
            Button:
                text: 'Go to results'
                on_release: app.root.current = 'results'

<ResultsScreen>:
    results_container: results_container
    BoxLayout:
        orientation: 'vertical'
        padding: dp(8)
        spacing: dp(6)

        Label:
            text: app.status_text
            size_hint_y: None
            height: self.texture_size[1] + dp(8)

        ProgressBar:
            max: app.progress_max
            value: app.progress_value
            size_hint_y: None
            height: dp(20)

        BoxLayout:
            size_hint_y: None
            height: dp(30)
            spacing: dp(10)

            BoxLayout:
                size_hint_x: 0.5
                spacing: dp(4)
                Label:
                    text: 'Only alive'
                CheckBox:
                    active: app.only_alive
                    on_active:
                        app.only_alive = self.active
                        app.on_filter_changed()

            BoxLayout:
                size_hint_x: 0.5
                spacing: dp(4)
                Label:
                    text: 'Only hostname'
                CheckBox:
                    active: app.only_hostname
                    on_active:
                        app.only_hostname = self.active
                        app.on_filter_changed()

        BoxLayout:
            size_hint_y: None
            height: dp(28)
            spacing: dp(4)
            Label:
                text: 'IP'
            Label:
                text: 'Status'
            Label:
                text: 'Open ports'
            Label:
                text: 'Hostname'

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True
            GridLayout:
                id: results_container
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(2)

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)

            Button:
                text: 'Back'
                on_release: app.go_to_config()
            Button:
                text: 'Save CSV'
                on_release: app.save_csv()
            Button:
                text: 'Stop scan'
                on_release: app.stop_scan()

<DetailsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(6)

        Label:
            text: 'Device info'
            font_size: '18sp'
            size_hint_y: None
            height: self.texture_size[1] + dp(8)

        GridLayout:
            cols: 2
            size_hint_y: None
            height: self.minimum_height
            row_default_height: dp(28)
            row_force_default: True
            spacing: dp(4)

            Label:
                text: 'IP:'
            Label:
                text: root.ip_text

            Label:
                text: 'Status:'
            Label:
                text: root.status_text

            Label:
                text: 'Hostname:'
            Label:
                text: root.host_text

            Label:
                text: 'MAC address:'
            Label:
                text: root.mac_text

            Label:
                text: 'Ping:'
            Label:
                text: root.ping_text

            Label:
                text: 'TTL:'
            Label:
                text: root.ttl_text

            Label:
                text: 'OS guess:'
            Label:
                text: root.os_text

        Label:
            text: 'Open ports:'
            size_hint_y: None
            height: self.texture_size[1] + dp(4)

        ScrollView:
            size_hint_y: 0.5
            do_scroll_x: False
            do_scroll_y: True
            Label:
                text: root.ports_text
                text_size: self.width, None
                size_hint_y: None
                height: self.texture_size[1]

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)

            Button:
                text: 'Back'
                on_release: app.root.current = 'results'
'''


# =============== Scan logic ==================

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

    def _ping_host(self, ip: str) -> bool:
        sys_name = platform.system().lower()
        try:
            if sys_name == "windows":
                cmd = ["ping", "-n", "1", "-w", str(int(self.ping_timeout * 1000)), ip]
            elif sys_name == "linux":
                cmd = ["ping", "-c", "1", "-W", str(max(1, int(self.ping_timeout))), ip]
            else:
                cmd = ["ping", "-c", "1", ip]
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

    def _scan_port(self, ip: str, port: int) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=self.timeout):
                return True
        except Exception:
            return False


# =============== Screens ==================

class ConfigScreen(Screen):
    pass


class ResultsScreen(Screen):
    results_container = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Keep all buttons by IP (even if currently hidden by filter)
        self.all_buttons = {}  # ip -> Button

    def clear_results(self):
        if self.results_container:
            self.results_container.clear_widgets()
        self.all_buttons.clear()

    def update_row(self, ip: str, alive: bool, ports_text: str, hostname: str):
        from kivy.app import App
        app = App.get_running_app()
        text = f"{ip} | {'Alive' if alive else 'Dead'} | {ports_text or '-'} | {hostname or '-'}"

        if ip in self.all_buttons:
            btn = self.all_buttons[ip]
            btn.text = text
        else:
            btn = Button(
                text=text,
                size_hint_y=None,
                height=30,
                halign='left',
            )
            btn.bind(on_release=lambda inst, ip=ip: app.open_details(ip))
            self.all_buttons[ip] = btn

        # Apply filter for this IP (show/hide)
        self.apply_filter_for_ip(ip, app)

    def apply_filter_for_ip(self, ip: str, app):
        btn = self.all_buttons.get(ip)
        if not btn:
            return
        should_show = app.ip_passes_filter(ip)
        container = self.results_container
        if should_show:
            if btn.parent is None:
                container.add_widget(btn)
        else:
            if btn.parent is not None:
                container.remove_widget(btn)

    def apply_filters_to_all(self, app):
        for ip in list(self.all_buttons.keys()):
            self.apply_filter_for_ip(ip, app)


class DetailsScreen(Screen):
    ip_text = StringProperty("")
    status_text = StringProperty("")
    host_text = StringProperty("")
    mac_text = StringProperty("")
    ping_text = StringProperty("")
    ttl_text = StringProperty("")
    os_text = StringProperty("")
    ports_text = StringProperty("")

    def set_details(
        self, ip, alive_text, hostname, mac, ping, ttl, os_guess, ports_text
    ):
        self.ip_text = ip
        self.status_text = alive_text
        self.host_text = hostname
        self.mac_text = mac
        self.ping_text = ping
        self.ttl_text = ttl
        self.os_text = os_guess
        self.ports_text = ports_text


# =============== Main app ==================

class MainApp(App):
    COMMON_PORTS = [53, 80, 135, 139, 143, 443, 445, 1883, 3074, 3306, 3389, 3659, 5222, 8080, 5222, 1883, 6379, 27017, 11211, 27015, 25565]

    # Scan settings
    scan_mode = StringProperty("local")      # local / cidr / range
    cidr = StringProperty("192.168.0.0/24")
    ip_start = StringProperty("192.168.0.1")
    ip_end = StringProperty("192.168.0.245")

    ports_mode = StringProperty("common")    # common / range / custom
    end_port = StringProperty("1024")
    custom_ports = StringProperty("53,80,443,110,143,1883,3306,3389,5222,6379,8080")

    ping_first = BooleanProperty(True)
    resolve_dns = BooleanProperty(True)

    host_workers = StringProperty("200")
    port_workers = StringProperty("100")
    tcp_timeout = StringProperty("0.4")
    ping_timeout = StringProperty("1.0")

    status_text = StringProperty("Ready")
    progress_value = NumericProperty(0)
    progress_max = NumericProperty(1)

    # Filters
    only_alive = BooleanProperty(True)
    only_hostname = BooleanProperty(True)

    scanning = BooleanProperty(False)
    selected_ip = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = None
        self.stop_event = None
        self.alive_by_ip = {}
        self.open_ports_by_ip = {}
        self.hostname_by_ip = {}

    def build(self):
        self.title = "LAN Scanner - Kivy"
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(ConfigScreen(name="config"))
        sm.add_widget(ResultsScreen(name="results"))
        sm.add_widget(DetailsScreen(name="details"))
        return sm

    # ---------- Filter helpers ----------

    def ip_passes_filter(self, ip: str) -> bool:
        if self.only_alive and not self.alive_by_ip.get(ip, False):
            return False
        if self.only_hostname and not (self.hostname_by_ip.get(ip) or "").strip():
            return False
        return True

    def on_filter_changed(self):
        if not self.root:
            return
        res = self.root.get_screen("results")
        res.apply_filters_to_all(self)

    # ---------- Message helpers ----------

    def show_message(self, title, text):
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        content.add_widget(Label(text=text))
        btn = Button(text="Close", size_hint_y=None, height=40)
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def show_error(self, text):
        self.show_message("Error", text)

    def show_info(self, text):
        self.show_message("Info", text)

    # ---------- Config reading ----------

    def read_config(self):
        try:
            host_workers = max(1, int(self.host_workers))
            port_workers = max(1, int(self.port_workers))
        except ValueError:
            raise ValueError("Thread values must be integers.")

        try:
            tcp_timeout = float(self.tcp_timeout)
            ping_timeout = float(self.ping_timeout)
            if tcp_timeout <= 0 or ping_timeout <= 0:
                raise ValueError
        except ValueError:
            raise ValueError("Timeout values must be positive floats.")

        pmode = self.ports_mode
        if pmode == "common":
            ports = list(self.COMMON_PORTS)
        elif pmode == "range":
            try:
                end_n = int(self.end_port)
                if not (1 <= end_n <= 65535):
                    raise ValueError
            except ValueError:
                raise ValueError("N must be between 1 and 65535.")
            ports = list(range(1, end_n + 1))
        else:
            ports = self.parse_ports_list(self.custom_ports)

        cfg = {
            "mode": self.scan_mode,
            "cidr": self.cidr.strip(),
            "ip_start": self.ip_start.strip(),
            "ip_end": self.ip_end.strip(),
            "ports": ports,
            "ping_first": bool(self.ping_first),
            "resolve_dns": bool(self.resolve_dns),
            "host_workers": host_workers,
            "port_workers": port_workers,
            "tcp_timeout": tcp_timeout,
            "ping_timeout": ping_timeout,
        }
        return cfg

    @staticmethod
    def parse_ports_list(text: str):
        text = (text or "").strip()
        if not text:
            raise ValueError("Port list is empty.")
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

    def build_targets(self, cfg):
        mode = cfg["mode"]
        if mode == "local":
            local_ip = LanScanner().get_local_ip()
            parts = local_ip.split(".")
            if len(parts) != 4:
                raise ValueError("Invalid local IP.")
            cidr = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            net = ipaddress.ip_network(cidr, strict=False)
            return [str(h) for h in net.hosts()]
        elif mode == "cidr":
            try:
                net = ipaddress.ip_network(cfg["cidr"], strict=False)
            except Exception:
                raise ValueError("Invalid CIDR. Example: 192.168.1.0/24")
            return [str(h) for h in net.hosts()]
        else:
            try:
                a = int(ipaddress.IPv4Address(cfg["ip_start"]))
                b = int(ipaddress.IPv4Address(cfg["ip_end"]))
            except Exception:
                raise ValueError("Invalid IP range.")
            if a > b:
                a, b = b, a
            return [str(ipaddress.IPv4Address(i)) for i in range(a, b + 1)]

    # ---------- Scan control ----------

    def start_scan(self):
        if self.scanning:
            return
        try:
            cfg = self.read_config()
        except ValueError as e:
            self.show_error(str(e))
            return

        self.clear_results()
        self.stop_event = threading.Event()
        self.scanning = True
        self.status_text = "Starting scan..."

        self.scanner = LanScanner(
            timeout=cfg["tcp_timeout"], ping_timeout=cfg["ping_timeout"]
        )

        t = threading.Thread(target=self.scan_worker, args=(cfg,), daemon=True)
        t.start()

        self.root.current = "results"

    def stop_scan(self):
        if self.scanning and self.stop_event:
            self.stop_event.set()
            self.status_text = "Stopping..."

    def clear_results(self):
        self.alive_by_ip.clear()
        self.open_ports_by_ip.clear()
        self.hostname_by_ip.clear()
        self.progress_value = 0
        self.progress_max = 1
        self.status_text = "Ready"
        res = self.root.get_screen("results")
        res.clear_results()

    def ui_call(self, func, *args, **kwargs):
        def _wrap(dt):
            func(*args, **kwargs)

        Clock.schedule_once(_wrap)

    def set_progress_max(self, maxv):
        self.progress_max = max(1, maxv)
        self.progress_value = 0

    def update_progress_and_status(self, done, total, stage):
        self.progress_max = max(1, total)
        self.progress_value = min(done, total)
        if stage == "hosts":
            self.status_text = f"Scanning hosts: {done}/{total}"
        else:
            self.status_text = f"Scanning ports: {done}/{total}"

    def finish_scan(self, msg):
        self.scanning = False
        self.status_text = msg

    def insert_or_update_ip(self, ip, alive):
        self.alive_by_ip[ip] = bool(alive)
        if ip not in self.open_ports_by_ip:
            self.open_ports_by_ip[ip] = []
        if ip not in self.hostname_by_ip:
            self.hostname_by_ip[ip] = ""
        res = self.root.get_screen("results")
        res.update_row(ip, bool(alive), self.ports_text(ip), self.hostname_by_ip[ip])

    def update_ports_cell(self, ip, ports_list):
        self.open_ports_by_ip[ip] = sorted(set(ports_list))
        had_alive = bool(self.alive_by_ip.get(ip))
        has_ports = len(self.open_ports_by_ip[ip]) > 0
        alive_now = had_alive or has_ports
        self.alive_by_ip[ip] = alive_now

        if ip not in self.hostname_by_ip:
            self.hostname_by_ip[ip] = ""

        res = self.root.get_screen("results")
        res.update_row(ip, alive_now, self.ports_text(ip), self.hostname_by_ip[ip])

    def update_host_cell(self, ip, host):
        self.hostname_by_ip[ip] = host or ""
        alive = bool(self.alive_by_ip.get(ip))
        res = self.root.get_screen("results")
        res.update_row(ip, alive, self.ports_text(ip), self.hostname_by_ip[ip])

    def ports_text(self, ip):
        ports = self.open_ports_by_ip.get(ip, [])
        return ", ".join(str(p) for p in ports) if ports else ""

    def resolve_dns_one(self, ip):
        try:
            host = socket.gethostbyaddr(ip)[0]
        except Exception:
            host = ""
        if not self.stop_event or not self.stop_event.is_set():
            self.ui_call(self.update_host_cell, ip, host)

    def scan_worker(self, cfg):
        try:
            targets = self.build_targets(cfg)
            total_hosts = len(targets)
            if total_hosts == 0:
                self.ui_call(self.finish_scan, "No targets to scan.")
                return

            self.ui_call(self.set_progress_max, total_hosts)
            self.ui_call(
                lambda: setattr(
                    self, "status_text", f"Scanning hosts: 0/{total_hosts}"
                )
            )

            hosts_done = 0

            if cfg["ping_first"]:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=cfg["host_workers"]
                ) as ex:
                    future_map = {
                        ex.submit(self.scanner._ping_host, ip): ip for ip in targets
                    }
                    for fut in concurrent.futures.as_completed(future_map):
                        if self.stop_event.is_set():
                            break
                        ip = future_map[fut]
                        alive = bool(fut.result())
                        self.ui_call(self.insert_or_update_ip, ip, alive)
                        hosts_done += 1
                        self.ui_call(
                            self.update_progress_and_status,
                            hosts_done,
                            total_hosts,
                            "hosts",
                        )
            else:
                for i, ip in enumerate(targets, start=1):
                    if self.stop_event.is_set():
                        break
                    self.ui_call(self.insert_or_update_ip, ip, True)
                    self.ui_call(
                        self.update_progress_and_status, i, total_hosts, "hosts"
                    )

            if self.stop_event.is_set():
                self.ui_call(self.finish_scan, "Stopped.")
                return

            ports = cfg["ports"]
            if not ports:
                self.ui_call(self.finish_scan, "Done.")
                return

            scan_hosts = list(targets)
            total_port_tasks = len(scan_hosts) * len(ports)
            if total_port_tasks == 0:
                self.ui_call(self.finish_scan, "Done.")
                return

            done_port_tasks = 0
            self.ui_call(self.set_progress_max, total_port_tasks)
            self.ui_call(
                lambda: setattr(
                    self, "status_text", f"Scanning ports: 0/{total_port_tasks}"
                )
            )

            for ip in scan_hosts:
                if self.stop_event.is_set():
                    break

                open_ports = []

                def check_port(p):
                    if self.stop_event.is_set():
                        return None
                    return p if self.scanner._scan_port(ip, p) else None

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=cfg["port_workers"]
                ) as ex:
                    future_map = {ex.submit(check_port, p): p for p in ports}
                    for fut in concurrent.futures.as_completed(future_map):
                        if self.stop_event.is_set():
                            break
                        res_port = fut.result()
                        if isinstance(res_port, int):
                            open_ports.append(res_port)
                            self.ui_call(
                                self.update_ports_cell, ip, list(open_ports)
                            )
                        done_port_tasks += 1
                        self.ui_call(
                            self.update_progress_and_status,
                            done_port_tasks,
                            total_port_tasks,
                            "ports",
                        )

                if cfg["resolve_dns"]:
                    threading.Thread(
                        target=self.resolve_dns_one, args=(ip,), daemon=True
                    ).start()

            if self.stop_event.is_set():
                self.ui_call(self.finish_scan, "Stopped.")
            else:
                self.ui_call(self.finish_scan, "Done.")

        except Exception as e:
            self.ui_call(self.show_error, str(e))
            self.ui_call(self.finish_scan, "Error")

    # ---------- Navigation / save ----------

    def go_to_config(self):
        self.root.current = "config"

    def save_csv(self):
        if not self.alive_by_ip:
            self.show_info("No results to save.")
            return

        path = os.path.join(self.user_data_dir, "lan_scan_results.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["IP", "Alive", "Open Ports", "Hostname"])
                for ip in sorted(self.alive_by_ip.keys()):
                    if not self.ip_passes_filter(ip):
                        continue
                    alive = "Yes" if self.alive_by_ip.get(ip) else "No"
                    ports = self.ports_text(ip)
                    host = self.hostname_by_ip.get(ip, "")
                    w.writerow([ip, alive, ports, host])
            self.show_info(f"CSV saved to:\n{path}")
        except Exception as e:
            self.show_error(f"Error saving CSV:\n{e}")

    # ---------- Details helpers ----------

    def _get_mac_address(self, ip: str) -> str:
        try:
            sys_name = platform.system().lower()
            if sys_name == "windows":
                cmd = ["arp", "-a", ip]
            else:
                cmd = ["arp", "-n", ip]
            output = subprocess.check_output(cmd, encoding="utf-8", errors="ignore")
            import re

            match = re.search(
                r"([0-9A-Fa-f]{2}[-:]){5}([0-9A-Fa-f]{2})", output
            )
            if match:
                return match.group(0)
        except Exception:
            pass
        return "Unknown"

    def _get_ping_info(self, ip: str):
        sys_name = platform.system().lower()
        try:
            if sys_name == "windows":
                cmd = ["ping", "-n", "1", "-w", "1000", ip]
            elif sys_name == "linux":
                cmd = ["ping", "-c", "1", "-W", "1", ip]
            else:
                cmd = ["ping", "-c", "1", ip]
            output = subprocess.check_output(cmd, encoding="utf-8", errors="ignore")
        except Exception:
            return None, None

        import re

        ttl = None
        time_ms = None

        m_ttl = re.search(r"TTL[=:\s]+(\d+)", output, re.IGNORECASE)
        if not m_ttl:
            m_ttl = re.search(r"ttl[=:\s]+(\d+)", output, re.IGNORECASE)
        if m_ttl:
            try:
                ttl = int(m_ttl.group(1))
            except Exception:
                ttl = None

        m_time = re.search(r"time[=<]?\s*([\d\.]+)\s*ms", output, re.IGNORECASE)
        if m_time:
            try:
                time_ms = float(m_time.group(1))
            except Exception:
                time_ms = None

        return time_ms, ttl

    @staticmethod
    def _guess_os_from_ttl(ttl):
        if ttl is None:
            return "Unknown"
        if ttl <= 64:
            return "Probably Linux/Unix"
        elif ttl <= 128:
            return "Probably Windows"
        elif ttl <= 255:
            return "Probably router/network device"
        else:
            return "Unknown"

    def open_details(self, ip: str):
        self.selected_ip = ip
        alive = bool(self.alive_by_ip.get(ip))
        ports = self.open_ports_by_ip.get(ip, [])
        hostname = self.hostname_by_ip.get(ip, "")

        ping_ms, ttl = self._get_ping_info(ip)
        mac_addr = self._get_mac_address(ip)
        os_guess = self._guess_os_from_ttl(ttl)

        ports_lines = []
        if ports:
            for p in ports:
                try:
                    srv = socket.getservbyport(p, "tcp")
                except Exception:
                    srv = "-"
                ports_lines.append(f"{p}  ({srv})")
        else:
            ports_lines.append("No open ports reported.")

        details_screen = self.root.get_screen("details")
        details_screen.set_details(
            ip=ip,
            alive_text="Alive" if alive else "No reply",
            hostname=hostname or "-",
            mac=mac_addr,
            ping=f"{ping_ms:.1f} ms" if ping_ms is not None else "Unknown",
            ttl=str(ttl) if ttl is not None else "Unknown",
            os_guess=os_guess,
            ports_text="\n".join(ports_lines),
        )
        self.root.current = "details"


if __name__ == "__main__":
    MainApp().run()
