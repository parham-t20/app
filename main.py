import kivy
kivy.require("2.0.0")

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.clock import Clock

import socket, ipaddress, platform, subprocess, concurrent.futures

# کلاس LanScanner همون کدی هست که دادی (بدون تغییر اینجا قرار بده)
# کلاس Wifi هم همون رو بیار




class LanScanner:
    def __init__(self, timeout=0.5, ping_timeout=1):
        """
        timeout: timeout (ثانیه) برای اتصال TCP به پورت‌ها
        ping_timeout: timeout (ثانیه) برای فرمان ping
        """
        self.timeout = timeout
        self.ping_timeout = ping_timeout
        self._ping_flag = '-n' if platform.system().lower() == 'windows' else '-c'

    def get_local_ip(self):
        """آی‌پی محلی را با اتصال UDP به یک آدرس بیرونی (بدون ارسال داده) پیدا می‌کند."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # آدرس و پورت هدف واقعی ارسال نمی‌شود، فقط باعث می‌شود سیستم آی‌پی محلی را انتخاب کند
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def _ping_host(self, ip):
        """پینگ ساده با استفاده از subprocess. برگشت: True اگر پاسخ داد."""
        try:
            cmd = ['ping', self._ping_flag, '1', '-w' if platform.system().lower() == 'windows' else '-W', str(int(self.ping_timeout*1000)) if platform.system().lower() == 'windows' else str(self.ping_timeout), ip]
            # بعضی سیستم‌ها -W مقدار برحسب ثانیه می‌پذیرند، ویندوز -w میلی‌ثانیه
            # برای سازگاری، اگر ویندوز است از -w میلی‌ثانیه، در غیر اینصورت -W ثانیه
        except Exception:
            cmd = ['ping', self._ping_flag, '1', ip]

        try:
            # خاموش کردن خروجی، فقط کد بازگشتی را بررسی می‌کنیم
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=self.ping_timeout+1)
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _scan_port(self, ip, port):
        """سعی می‌کند به ip:port متصل شود. برگشت True اگر باز بود."""
        try:
            with socket.create_connection((ip, port), timeout=self.timeout):
                return True
        except Exception:
            return False

    def _ip_generator_from_cidr(self, cidr):
        """دریافت لیست آدرس‌ها از یک CIDR مثل '192.168.1.0/24' (همه هاست‌ها به جز network و broadcast)."""
        net = ipaddress.ip_network(cidr, strict=False)
        for host in net.hosts():
            yield str(host)

    def scan_hosts(self, cidr=None, ip_start=None, ip_end=None, workers=100, ping_first=True):
        """
        دو حالت:
          - اگر cidr داده شود (مثلاً '192.168.1.0/24') همه هاست‌های آن اسکن می‌شوند.
          - وگرنه اگر ip_start و ip_end داده شوند، range بین آن‌ها اسکن می‌شود (هر دو inclusive).
        برمی‌گرداند: dict {ip: {'alive': True/False}}
        """
        targets = []
        if cidr:
            targets = list(self._ip_generator_from_cidr(cidr))
        elif ip_start and ip_end:
            a = ipaddress.IPv4Address(ip_start)
            b = ipaddress.IPv4Address(ip_end)
            if a > b:
                a, b = b, a
            cur = a
            while cur <= b:
                targets.append(str(cur))
                cur += 1
        else:
            raise ValueError("باید یا cidr یا ip_start و ip_end رو تعیین کنی")

        results = {}
        def check(ip):
            alive = self._ping_host(ip) if ping_first else True
            return ip, alive

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(check, ip) for ip in targets]
            for f in concurrent.futures.as_completed(futures):
                ip, alive = f.result()
                results[ip] = {'alive': alive}
        return results

    def scan_ports(self, ip, ports=None, workers=100):
        """
        اسکن پورت‌های یک آی‌پی. ports لیستی از اعداد پورت است.
        خروجی: {'ip': ip, 'open_ports': [..]}
        """
        if ports is None:
            ports = [22, 23, 53, 80, 135, 139, 143, 443, 445, 3306, 3389, 8080]  # پورت‌های متداول
        open_ports = []

        def check_port(p):
            if self._scan_port(ip, p):
                return p
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(check_port, p) for p in ports]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res is not None:
                    open_ports.append(res)

        return {'ip': ip, 'open_ports': sorted(open_ports)}

    def scan_network(self, cidr=None, ip_start=None, ip_end=None, ports=None, workers_hosts=200, workers_ports=100, ping_first=True):
        """
        ترکیب: ابتدا هاست‌ها را پیدا می‌کند، سپس برای هر هاست زنده پورت‌ها را می‌بیند.
        خروجی: dict { ip: { 'alive': bool, 'open_ports': [...] } }
        """
        hosts = self.scan_hosts(cidr=cidr, ip_start=ip_start, ip_end=ip_end, workers=workers_hosts, ping_first=ping_first)
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex_outer:
            futures = []
            for ip, info in hosts.items():
                if info['alive'] or not ping_first:
                    futures.append(ex_outer.submit(self.scan_ports, ip, ports, workers=workers_ports))
                else:
                    results[ip] = {'alive': False, 'open_ports': []}

            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                results[r['ip']] = {'alive': True, 'open_ports': r['open_ports']}
        # اضافه کردن هر آی‌پی که ping نداد ولی در hosts بود (در صورت race)
        for ip, info in hosts.items():
            if ip not in results:
                results[ip] = {'alive': info['alive'], 'open_ports': []}
        return results


class Wifi:
    __All__ = None
    def scanipaddress(self, end_range=1024, ip_address=None):
        global local_ip
        scanner = LanScanner(timeout=0.4, ping_timeout=1)
        if ip_address == None:
            local_ip = scanner.get_local_ip()
            Wifi.__All__ = True
        else:
            local_ip = ip_address
            Wifi.__All__ = False
        print("Local IP:", local_ip)

        # تولید CIDR از IP
        parts = local_ip.split('.')
        cidr = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24" if len(parts) == 4 else None

        all_ports = list(range(1, end_range + 1))
        print(f"Scanning network {cidr} on ports 1-{end_range}...")

        res = scanner.scan_network(cidr=cidr, ports=all_ports)

        # نمایش خروجی
        for ip, info in sorted(res.items()):
            if info['alive'] or info['open_ports']:
                if Wifi.__All__ == False and ip == local_ip:
                    print(f"{ip} | Alive: {info['alive']} | Open Ports: {info['open_ports']}")
                
                elif Wifi.__All__ == True and ip_address == None:
                    print(f"{ip} | Alive: {info['alive']} | Open Ports: {info['open_ports']}")

    def getnamebyip(self, *ip_address:str):
            global name
            try:
                for ip in ip_address:
                    ip_name = socket.gethostbyaddr(ip) 
                    name = ip_name[0]
                    return name

            except socket.herror:
                name = "None"
                return name
                


class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(MainLayout, self).__init__(orientation="vertical", **kwargs)

        self.result = TextInput(
            hint_text="Results will appear here...",
            size_hint=(1, 0.8),
            multiline=True,
            readonly=True,        # <-- فقط خواندنی
            cursor_blink=False,
            halign="center",
            font_size = 20    # غیر فعال کردن چشمک‌زدن مکان‌نما (زیبایی)
        )
        self.add_widget(self.result)

        self.scan_button = Button(text="Scan Network", size_hint=(1, 0.1))
        self.scan_button.bind(on_press=self.start_scan)
        self.add_widget(self.scan_button)

        self.port_input = TextInput(
            hint_text="Enter max port (default 1024)",
            size_hint=(1, None),  # ارتفاع ثابت,        # اندازه مناسب برای یک فیلد تک‌خطی
            multiline=False,
            halign="center",
            height=80,
            font_size=60
        )
        self.add_widget(self.port_input)

    def start_scan(self, instance):
        self.scan_button.disabled = True
        self.port_input.disabled = True
        try:
            end_port = int(self.port_input.text) if self.port_input.text.strip() else 1024
        except:
            end_port = 1024

        self.result.halign="center"
        self.result.text = "Scanning... Please wait.\n"
        Clock.schedule_once(lambda dt: self.do_scan(end_port), 0.2)

    def do_scan(self, end_port):
        wifi = Wifi()
        scanner = LanScanner()
        local_ip = scanner.get_local_ip()

        parts = local_ip.split('.')
        cidr = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

        res = scanner.scan_network(cidr=cidr, ports=list(range(1, end_port + 1)))
        self.result.halign="left"
        output = ""
        for ip, info in sorted(res.items()):
            if info['alive'] or info['open_ports']:
                device_name = wifi.getnamebyip(ip)
                output += f"Name:{device_name} | {ip} | Alive: {info['alive']} | Ports: {info['open_ports']}\n"
        self.scan_button.disabled = False
        self.port_input.disabled = False
        if not output:
            output = "No alive hosts found."

        self.result.text = output


class WifiScannerApp(App):
    def build(self):
        return MainLayout()


if __name__ == "__main__":
    WifiScannerApp().run()
