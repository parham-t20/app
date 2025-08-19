import os
import uuid
import requests
import random
import string
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

SERVER_URL = "https://server-xx0i.onrender.com"  # آدرس سرور خودت
file_name = "/storage/emulated/0/Download/App_data.txt"

if not os.path.exists(file_name):
    api_key = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(32))
    response = requests.post(f"{SERVER_URL}/send", json={"user": api_key, "api":0})
    with open(file_name, "w") as f:
        f.write(api_key)
else:
    with open(file_name, "r") as f:
        api_key = f.read().strip()


class MyApp(App):
    def build(self):
        # مرحله ۱: تولید یا خواندن API Key
        
        
        # مرحله ۲: ارسال به سرور برای بررسی
        try:
            response = requests.get(f"{SERVER_URL}/rece")
            data = response.json()

            if data[api_key] == 1:
                self.show_ave()
            else:
                self.show_error()

        except Exception as e:
            self.show_error()
            return Label(text="خطا در ارتباط با سرور")

    def check_server(self):
        try:
            response = requests.get(f"{SERVER_URL}/rece")
            data = response.json()

            if data[api_key] == 1:
                self.show_ave()
            else:
                self.show_error()

        except Exception as e:
            self.show_error()
            

    def show_error(self):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text="App Is Not Avelabel"))

        # دکمه بستن برنامه
        close_btn = Button(text="close", size_hint=(1, 0.3))
        close_btn.bind(on_release=lambda *args: App.get_running_app().stop())
        box.add_widget(close_btn)

        popup = Popup(title="App", content=box, size_hint=(0.8, 0.5))
        popup.open()

    def show_ave(self):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text="App Is Avelabel"))

        # دکمه بستن برنامه
        close_btn = Button(text="ok", size_hint=(1, 0.3))
        close_btn.bind(on_release=lambda *args: popup.dismiss())
        box.add_widget(close_btn)

        popup = Popup(title="App", content=box, size_hint=(0.8, 0.5))
        popup.open()

        Clock.schedule_once(lambda dt: self.check_server(), 1.0)

MyApp().run()
