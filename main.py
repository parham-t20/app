import os
import requests
import random
import string
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock

SERVER_URL = "https://server-xx0i.onrender.com"
file_name = "/storage/emulated/0/Download/App_data.txt"

# تولید یا خواندن API key
if not os.path.exists(file_name):
    api_key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    try:
        requests.post(f"{SERVER_URL}/send", json={"user": api_key, "api": 0})
    except:
        pass
    with open(file_name, "w") as f:
        f.write(api_key)
else:
    with open(file_name, "r") as f:
        api_key = f.read().strip()


class ServerScreen(Screen):
    def on_enter(self):
        # نمایش متن وضعیت
        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.status_label = Label(text="Checking server...")
        box.add_widget(self.status_label)
        self.add_widget(box)

        # هر ۱ ثانیه چک سرور
        self.event = Clock.schedule_interval(self.check_server, 1)

    def on_leave(self):
        if hasattr(self, 'event') and self.event:
            self.event.cancel()

    def check_server(self, dt):
        try:
            response = requests.get(f"{SERVER_URL}/rece", timeout=3)
            if response.status_code == 200:
                data = response.json()
                status = data.get(api_key, 0)
                self.status_label.text = f"Server status: {status}"

                if status == 1:
                    if self.manager:
                        self.manager.current = "main"
                    if self.event:
                        self.event.cancel()
                else:
                    self.show_disabled()
                    if self.event:
                        self.event.cancel()
            else:
                box1 = BoxLayout(orientation="vertical", spacing=10, padding=10)
                box1.add_widget(Label(text="server is not on."))
                popup = Popup(title="Error", content=box1, size_hint=(0.8, 0.5))
                close_btn = Button(text="Close", size_hint=(1, 0.3))
                close_btn.bind(on_release=App.get_running_app().stop)
                box1.add_widget(close_btn)
                popup.open()

        except Exception as e:
            # وقتی به سرور وصل نشد (مثل خطای DNS)
            if response.status_code != 200:
                box2 = BoxLayout(orientation="vertical", spacing=10, padding=10)
                box2.add_widget(Label(text="plase on network."))
                popup = Popup(title="network", content=box2, size_hint=(0.8, 0.5))
                close_btn = Button(text="Close", size_hint=(1, 0.3))
                close_btn.bind(on_release=App.get_running_app().stop)
                box2.add_widget(close_btn)
                popup.open()
            




    def show_disabled(self):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text="Your app has been disabled by the server."))
        popup = Popup(title="Disabled", content=box, size_hint=(0.8, 0.5))
        close_btn = Button(text="Close", size_hint=(1, 0.3))
        close_btn.bind(on_release=App.get_running_app().stop)
        box.add_widget(close_btn)
        popup.open()


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text=f'{api_key}'))
        self.add_widget(box)
        self.on_enter()

    def on_enter(self):

        # هر ۱ ثانیه چک سرور
        self.event = Clock.schedule_interval(self.check_server, 6)

    def on_leave(self):
        if hasattr(self, 'event') and self.event:
            self.event.cancel()

    def check_server(self, dt):
        try:
            response = requests.get(f"{SERVER_URL}/rece", timeout=3)
            if response.status_code == 200:
                data = response.json()

                if data[api_key] == 1:
                    if self.manager:
                        self.manager.current = "main"
                    if self.event:
                        self.event.cancel()
                else:
                    self.show_disabled()
                    if self.event:
                        self.event.cancel()
            else:
                box1 = BoxLayout(orientation="vertical", spacing=10, padding=10)
                box1.add_widget(Label(text="server is not on."))
                popup = Popup(title="Error", content=box1, size_hint=(0.8, 0.5))
                close_btn = Button(text="Close", size_hint=(1, 0.3))
                close_btn.bind(on_release=App.get_running_app().stop)
                box1.add_widget(close_btn)
                popup.open()

        except Exception as e:
            # وقتی به سرور وصل نشد (مثل خطای DNS)
            if response.status_code != 200:
                box2 = BoxLayout(orientation="vertical", spacing=10, padding=10)
                box2.add_widget(Label(text="plase on network."))
                popup = Popup(title="network", content=box2, size_hint=(0.8, 0.5))
                close_btn = Button(text="Close", size_hint=(1, 0.3))
                close_btn.bind(on_release=App.get_running_app().stop)
                box2.add_widget(close_btn)
                popup.open()
            




    def show_disabled(self):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text="Your app has been disabled by the server."))
        popup = Popup(title="Disabled", content=box, size_hint=(0.8, 0.5))
        close_btn = Button(text="Close", size_hint=(1, 0.3))
        close_btn.bind(on_release=App.get_running_app().stop)
        box.add_widget(close_btn)
        popup.open()


class MyApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ServerScreen(name='server'))
        sm.add_widget(MainScreen(name='main'))
        return sm


if __name__ == '__main__':
    MyApp().run()
