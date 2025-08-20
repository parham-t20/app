import os
import requests
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout

SERVER_URL = "https://server-xx0i.onrender.com"
file_name = "/storage/emulated/0/Download/App_resive.txt"


# ----------------- ComboBox فقط انتخابی -----------------
class ComboBox(BoxLayout):
    def __init__(self, items, columns=2, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.items = items
        self.columns = columns
        self.selected_text = ""

        # دکمه اصلی (نمایش انتخاب)
        self.main_button = Button(
            text="Select Api key",
            size_hint_x=1,
            size_hint_y=None,
            height=60,
            font_size=25
        )
        self.add_widget(self.main_button)

        # DropDown
        self.dropdown = DropDown()

        # GridLayout برای چندستونه کردن
        grid = GridLayout(cols=self.columns, size_hint_y=None, spacing=5, padding=5)
        grid.bind(minimum_height=grid.setter("height"))

        for item in self.items:
            btn = Button(text=item, size_hint_y=None, height=40)
            btn.bind(on_release=lambda btn: self.select_item(btn.text))
            grid.add_widget(btn)

        self.dropdown.add_widget(grid)

        # وقتی روی دکمه اصلی کلیک شد Dropdown باز شود
        self.main_button.bind(on_release=self.dropdown.open)

    def select_item(self, text):
        self.selected_text = text
        self.main_button.text = text
        self.dropdown.dismiss()

    def get_text(self):
        return self.selected_text


# ----------------- اپ اصلی -----------------
class MyApp(App):
    def build(self):
        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        box = BoxLayout(orientation="vertical", spacing=10, size_hint=(1, None))
        box.height = 400

        self.label = Label(
            text="Select Api key",
            size_hint_x=1,
            size_hint_y=None,
            height=60,
            font_size=30,
        )

        # گرفتن دیتا از سرور
        response = requests.get(f"{SERVER_URL}/rece")
        data = response.json()
        keys_list = list(data.keys())

        # ساخت ComboBox فقط انتخابی
        self.combo = ComboBox(keys_list, columns=3)

        # دکمه‌ها
        btn = Button(text="Enter", size_hint_x=1, size_hint_y=None, height=60)
        btn.bind(on_press=self.on_click)

        # رادیوها
        radio_box = BoxLayout(
            orientation="horizontal", spacing=20, size_hint_y=None, height=50
        )

        self.radio0 = ToggleButton(text="0", group="radio", state="down")
        self.radio1 = ToggleButton(text="1", group="radio")
        radio_box.add_widget(self.radio0)
        radio_box.add_widget(self.radio1)

        # اضافه کردن به Box
        box.add_widget(self.label)
        box.add_widget(self.combo)
        box.add_widget(radio_box)
        box.add_widget(btn)


        anchor.add_widget(box)
        return anchor

    def on_click(self, instance):
        text_value = self.combo.get_text()
        if text_value.strip() != "":
            if self.radio0.state == "down":
                r = requests.post(
                    f"{SERVER_URL}/send", json={"user": text_value, "api": 0}
                )
                if r.status_code == 200:
                    self.combo.main_button.text = "Select Api key"
                    self.label.text = str(r.status_code)

            elif self.radio1.state == "down":
                r = requests.post(
                    f"{SERVER_URL}/send", json={"user": text_value, "api": 1}
                )
                if r.status_code == 200:
                    self.combo.main_button.text = "Select Api key"
                    self.label.text = str(r.status_code)
        else:
            self.label.text = "Please Select Api key"

if __name__ == "__main__":
    MyApp().run()
