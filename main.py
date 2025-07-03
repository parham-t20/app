import socket
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

file_name = "/storage/emulated/0/Download/data.txt"


# دیکشنری کشورها و منطقه زمانی
country_timezones = {
    "iran": "Asia/Tehran",
    "usa": "America/New_York",
    "germany": "Europe/Berlin",
    "alman": "Europe/Berlin",
    "russia": "Europe/Moscow",
    "uae": "Asia/Dubai",
    "dubai": "Asia/Dubai",
    "brazil": "America/Sao_Paulo",
    "uk": "Europe/London"
}

class UserPass(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as file:
                data = file.read()
                self.password = str(data)
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


class DeviceScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        box1 = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=22, padding=[10, 30, 10, 10])

        self.lbl = Label(text='IP Address', font_size=30)
        self.txt_input_ip = TextInput(text='192.168.', multiline=False, size_hint_y=None, height=50, font_size=30)
        btn_connect = Button(text='Connect Device', size_hint_y=None, height=80)
        btn_back = Button(text='Back', size_hint_y=None, height=80)

        btn_connect.bind(on_press=self.go_to_send)
        btn_back.bind(on_press=partial(self.change_screen, 'main'))

        box1.bind(minimum_height=box1.setter('height'))
        box1.add_widget(self.lbl)
        box1.add_widget(self.txt_input_ip)
        box1.add_widget(btn_connect)
        box1.add_widget(btn_back)

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box1)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        self.manager.current = screen_name

    def go_to_send(self, instance):
        ip_text = self.txt_input_ip.text
        if ip_text.count('.') != 3 or len(ip_text) < 10:
            self.lbl.text = "Error"
            self.lbl.color = (1, 0, 0, 1)
        else:
            self.lbl.text = "IP Address"
            self.lbl.color = (1, 1, 1, 1)
            send_screen = self.manager.get_screen('send')
            send_screen.ip = ip_text
            self.manager.current = 'send'


class SendToDeviceScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ip = ""

        box2 = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=22, padding=[10, 30, 10, 10])

        lbl = Label(text='Your Message', font_size=30)
        self.txt_input_Message = TextInput(multiline=False, size_hint_y=None, height=50, font_size=30)
        btn_send = Button(text='Send Message', size_hint_y=None, height=80)
        btn_back = Button(text='Back', size_hint_y=None, height=80)

        btn_send.bind(on_press=self.send_message)
        btn_back.bind(on_press=partial(self.change_screen, 'device'))

        box2.bind(minimum_height=box2.setter('height'))
        box2.add_widget(lbl)
        box2.add_widget(self.txt_input_Message)
        box2.add_widget(btn_send)
        box2.add_widget(btn_back)

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box2)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        self.manager.current = screen_name

    def send_message(self, instance):
        msg = self.txt_input_Message.text
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.ip, 12345))
            client.send(msg.encode('utf-8'))
            response = client.recv(1024).decode('utf-8')
            print("Response from server:", response)
            client.close()
        except Exception as e:
            print("Connection error:", e)


class TimeZoneScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        box3 = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=22, padding=[10, 30, 10, 10])

        self.time_lbl = Label(text=f'Country name Time is 00:00:00', font_size=30)
        self.txt_input_time = TextInput(multiline=False, size_hint_y=None, height=50, font_size=30)
        btn_find = Button(text='Find', size_hint_y=None, height=80)
        btn_back = Button(text='Back', size_hint_y=None, height=80)

        box3.add_widget(self.time_lbl)
        box3.add_widget(self.txt_input_time)
        box3.add_widget(btn_find)
        box3.add_widget(btn_back)

        box3.bind(minimum_height=box3.setter('height'))
        btn_find.bind(on_press=self.finder)
        btn_back.bind(on_press=partial(self.change_screen, 'main'))

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box3)
        self.add_widget(anchor)

    def change_screen(self, screen_name, instance):
        self.manager.current = screen_name

    def finder(self, instance):
        try:
            country = self.txt_input_time.text.strip().lower()
            if country in country_timezones:
                tz_name = country_timezones[country]
                tz = timezone(tz_name)
                now = datetime.now(tz)
                self.time_lbl.color = (1, 1, 1, 1)
                self.time_lbl.text = f"Country {country.title()} Time is {now.strftime('%H:%M:%S')}"
            else:
                self.time_lbl.text = "Country not found"
                self.time_lbl.color = (1, 0, 0, 1)
        except Exception as e:
            self.time_lbl.text = "Error occurred"
            self.time_lbl.color = (1, 0, 0, 1)
            print("Error in finder:", e)



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
        self.manager.current = screen_name
        self.input_pass.text = ""
        self.input_pass2.text = ""


    def save_password(self, instance):
        if len(self.input_pass.text) >= 8 and len(self.input_pass2.text) >= 8:

            self.btn_save.color = (0,1,0,1)

            if os.path.exists(file_name):
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(self.input_pass.text)
                    file.close()
                    Clock.schedule_once(lambda dt: self.change_screen('option', instance), 0.7)
                    

            else:
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(self.input_pass.text)
                    file.close()
                    Clock.schedule_once(lambda dt: self.change_screen('option', instance), .07)

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




class MyApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(UserPass(name='userpass'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(DeviceScreen(name='device'))
        sm.add_widget(SendToDeviceScreen(name='send'))
        sm.add_widget(TimeZoneScreen(name='timezone'))
        sm.add_widget(Option(name='option'))
        sm.add_widget(ChengePassword(name='chengepassword'))
        return sm



MyApp().run()
