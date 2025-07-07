from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from pytz import timezone
from datetime import datetime
from functools import partial
from kivy.clock import Clock
import os


#file_name = "/storage/emulated/0/Download/data.txt"
file_name = "data.txt"


class UserPass(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as file:
                data = file.read()
                self.password = str(data)
                file.close()
        else:
            self.password = "0000"
        
        box = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=24, padding=[10, 30, 10, 10])
        self.input_password = TextInput(hint_text="Enter Password", multiline=False, size_hint_y=None, height=80, font_size=58)
        self.btn_ok = Button(text="Enter", size_hint_y=None, height=80)
        self.btn_ok.color = (1, 1, 1, 1)

        box.add_widget(self.input_password)
        box.add_widget(self.btn_ok)

        box.bind(minimum_height=box.setter('height'))
        self.btn_ok.bind(on_press=partial(self.change_screen, 'main'))

        anchor = AnchorLayout(anchor_y='center')
        anchor.add_widget(box)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        if self.input_password.text == self.password:
            self.btn_ok.color = (0, 1, 0, 1)
            Clock.schedule_once(lambda dt: self.go_to_main(screen_name), 0.7)  # تاخیر ۱ ثانیه‌ای
        else:
            self.input_password.text = ""
            self.btn_ok.color = (1, 0, 0, 1)

    def go_to_main(self, screen_name):
        self.manager.current = screen_name
        self.input_password.text = ""
