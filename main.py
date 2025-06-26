import socket
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.anchorlayout import AnchorLayout

class MyApp(App):
    def build(self):
        lbl = Label(text='Enter your name:', size_hint_y=None, height=50)
        self.txt_input_name = TextInput(multiline=False, size_hint_y=None, height=50, font_size=30)
        lbl1 = Label(text='Enter your Email:', size_hint_y=None, height=50)
        self.txt_input_email = TextInput(multiline=False, size_hint_y=None, height=50, font_size=30)
        lbl2 = Label(text='Enter your Password:', size_hint_y=None, height=50)
        self.txt_input_password = TextInput(multiline=False, size_hint_y=None, height=50, font_size=30)
        btn = Button(text='Submit', size_hint_y=None, height=50)

        btn.bind(on_press=self.on_click)

        box = BoxLayout(orientation='vertical', size_hint=(1, None))
        box.bind(minimum_height=box.setter('height'))
        box.add_widget(lbl)
        box.add_widget(self.txt_input_name)
        box.add_widget(lbl1)
        box.add_widget(self.txt_input_email)
        box.add_widget(lbl2)
        box.add_widget(self.txt_input_password)
        box.add_widget(btn)

        anchor = AnchorLayout(anchor_y='top')
        anchor.add_widget(box)
        return anchor

    def on_click(self, instance):
        name = self.txt_input_name.text
        email = self.txt_input_email.text
        password = self.txt_input_password.text
        
        # ارسال داده به لپ‌تاپ (آی‌پی و پورت لپ‌تاپ خود را وارد کنید)
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('192.168.0.105', 12345))  # جایگزین کنید با آی‌پی لپ‌تاپ خود
            send_data = f"{name}|{email}|{password}"
            client.send(send_data.encode('utf-8'))
            response = client.recv(1024).decode('utf-8')
            print("Response from server:", response)
            client.close()
        except Exception as e:
            print("Connection error:", e)

if __name__ == '__main__':
    MyApp().run()
