from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from plyer import gps
from kivy.clock import Clock

class GpsTest(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        self.label = Label(text="موقعیت GPS: نامشخص")
        self.btn = Button(text="شروع گرفتن GPS")
        self.btn.bind(on_press=self.start_gps)
        self.layout.add_widget(self.label)
        self.layout.add_widget(self.btn)
        return self.layout

    def start_gps(self, instance):
        try:
            gps.configure(on_location=self.on_location, on_status=self.on_status)
            gps.start(minTime=1000, minDistance=1)
            self.label.text = "در حال دریافت موقعیت..."
        except NotImplementedError:
            self.label.text = "این دستگاه GPS ندارد یا پشتیبانی نمی‌شود."

    def on_location(self, **kwargs):
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        self.label.text = f"Latitude: {lat}\nLongitude: {lon}"

    def on_status(self, stype, status):
        print(f"GPS status: {stype} - {status}")

if __name__ == '__main__':
    GpsTest().run()
