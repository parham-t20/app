import os
import requests
import random
import string
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock

SERVER_URL = "https://server-xx0i.onrender.com"
file_name = "/storage/emulated/0/Download/App_data.txt"

class MyApp(App):
    def build(self):
        # AnchorLayout که همه چیز رو وسط نگه می‌دارد
        anchor = AnchorLayout(anchor_x="center", anchor_y="center")

        # BoxLayout عمودی (پهنای کامل بگیره)
        box = BoxLayout(orientation="vertical", spacing=10, size_hint=(1, None))
        box.height = 200  # ارتفاع مشخص

        # ویجت‌ها (size_hint_x=1 یعنی تمام عرض رو بگیرند)
        self.label = Label(text="Type Api key", size_hint_x=1, size_hint_y=None, height=60, font_size=30)
        self.text_input = TextInput(hint_text="Api key", multiline=False, size_hint_x=1 ,size_hint_y=None,  font_size=40,  halign="center", height=60)
        btn = Button(text="Enter", size_hint_x=1, size_hint_y=None, height=60 )
        btn.bind(on_press=self.on_click)
        # اضافه کردن ویجت‌ها به BoxLayout

        radio_box = BoxLayout(orientation="horizontal", spacing=20, size_hint_y=None, height=50)

        self.radio0 = ToggleButton(text="0", group="radio", state="down")  # مقدار 0
        self.radio1 = ToggleButton(text="1", group="radio")                # مقدار 1

        radio_box.add_widget(self.radio0)
        radio_box.add_widget(self.radio1)


        box.add_widget(self.label)
        box.add_widget(self.text_input)
        box.add_widget(radio_box)
        box.add_widget(btn)

        # اضافه کردن BoxLayout به AnchorLayout
        anchor.add_widget(box)

        return anchor
    
    def on_click(self, instance):
        if self.text_input.text > "":
            if self.radio0.state == "down":
                r = requests.post(f"{SERVER_URL}/send", json={"user":self.text_input.text, "api":0})
                if r.status_code == 200:
                    self.text_input.text = ""
                    self.label.text = str(r.status_code)
            
            elif self.radio1.state == "down":
                r = requests.post(f"{SERVER_URL}/send", json={"user":self.text_input.text, "api":1})
                if r.status_code == 200:
                    self.text_input.text = ""
                    self.label.text = str(r.status_code)
        else:
            self.label.text = "plase Type your Api key"

if __name__ == "__main__":
    MyApp().run()
