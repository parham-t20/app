import socket
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.popup import Popup
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


data_file = {"Password_Save" : "data.txt"}#/storage/emulated/0/duk/myapp/App_data.txt


class UserPass(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


        if os.path.exists(data_file["Password_Save"]):
            with open(data_file["Password_Save"], "r", encoding="utf-8") as file:
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




class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        box = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=20, padding=10)

        btn_connect = Button(text='Connect To Device', size_hint_y=None, height=80)
        btn_time_zone = Button(text="Time Zone Finder", size_hint_y=None, height=80)
        btn_option = Button(text="Option", size_hint_y=None, height=80)

        btn_connect.bind(on_press=partial(self.change_screen, 'device'))
        btn_time_zone.bind(on_press=partial(self.change_screen, 'timezone'))
        btn_option.bind(on_press=partial(self.change_screen, 'option'))

        box.add_widget(btn_connect)
        box.add_widget(btn_time_zone)
        box.add_widget(btn_option)
        box.bind(minimum_height=box.setter('height'))

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        self.manager.current = screen_name





class ChengePassword(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        box5 = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=22, padding=[10, 30, 10, 10])

        box5.bind(minimum_height=box5.setter('height'))

        self.input_pass = TextInput(hint_text="Password",multiline=False, size_hint_y=None, height=50, font_size=30)
        self.input_pass2 = TextInput(hint_text="Confirm Password",multiline=False, size_hint_y=None, height=50, font_size=30)
        self.btn_save = Button(text='Password Save', size_hint_y=None, height=80)
        self.btn_back = Button(text='Back', size_hint_y=None, height=80)

        
        self.btn_save.bind(on_press=self.save_password)
        self.btn_back.bind(on_press=partial(self.change_screen, 'option'))


        box5.add_widget(self.input_pass)
        box5.add_widget(self.input_pass2)
        box5.add_widget(self.btn_save)
        box5.add_widget(self.btn_back)

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box5)
        self.add_widget(anchor)


    def change_screen(self, screen_name, instance):
        self.input_pass.text = ""
        self.input_pass2.text = ""
        Clock.schedule_once(lambda dt: self.go_to_main(screen_name,instance=instance), 0.7)


    def go_to_main(self, screen_name, instance):
        self.manager.current = screen_name


    def save_password(self, instance):
        if len(self.input_pass.text) >= 8 and len(self.input_pass2.text) >= 8:

            self.btn_save.color = (0,1,0,1)

            if os.path.exists(data_file["Password_Save"]):
                with open(data_file["Password_Save"], "w", encoding="utf-8") as file:
                    file.write(self.input_pass.text)
                    file.close()
                    self.change_screen('option', instance)
                    

            else:
                with open(data_file["Password_Save"], "w", encoding="utf-8") as file:
                    file.write(self.input_pass.text)
                    file.close()
                    self.change_screen('option', instance)

        else:
            self.input_pass2.text = ""
            self.btn_save.color = (1,0,0,1)
            Clock.schedule_once(lambda dt: self.change_btn(), 1)

    def change_btn(self):
        self.btn_save.color = (1,1,1,1)


class Option(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        box5 = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=22, padding=[10, 30, 10, 10])

        box5.bind(minimum_height=box5.setter('height'))

        self.btn_chenge = Button(text='Chenge Password', size_hint_y=None, height=80)
        self.btn_back = Button(text='Back', size_hint_y=None, height=80)

        self.btn_chenge.bind(on_press=partial(self.change_screen, 'chengepassword'))
        self.btn_back.bind(on_press=partial(self.change_screen, 'main'))
        

        box5.add_widget(self.btn_chenge)
        box5.add_widget(self.btn_back)

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box5)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        self.manager.current = screen_name



class MyApp(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text="plase Active Application", size_hint_y=None, height=50))

        close_button = Button(text="close", size_hint=(1, 0.3))
        content.add_widget(close_button)

        popup = Popup(title="message from App",
                      content=content,
                      size_hint=(0.6, 0.3),
                      auto_dismiss=False)
        close_button.bind(on_press=self.cls)
        popup.open()


        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(content)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        self.manager.current = screen_name




class MyApp(App):
    def build(self):
        try:
            sm = ScreenManager()
            sm.add_widget(UserPass(name='userpass'))
            sm.add_widget(MainScreen(name='main'))
            sm.add_widget(Option(name='option'))
            sm.add_widget(ChengePassword(name='chengepassword'))
            return sm
        except Exception as e:
            print("Error in build method:", e)
            return Label(text="An error occurred while building the app.")

if __name__ == '__main__':
    MyApp().run()
