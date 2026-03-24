import os
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform


# --- RTL shaping (Persian/Arabic) ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def rtl(text: str) -> str:
        if text is None:
            return ""
        t = str(text)
        reshaped = arabic_reshaper.reshape(t)
        return get_display(reshaped, base_dir="R")

except Exception:
    def rtl(text: str) -> str:
        if text is None:
            return ""
        return str(text)


def fmt_time(seconds: float) -> str:
    try:
        s = int(max(0, seconds))
    except Exception:
        s = 0
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class RootWidget(BoxLayout):
    current_song_name = StringProperty("")
    current_artist = StringProperty("")
    status_text = StringProperty("")
    source_text = StringProperty("")
    elapsed_text = StringProperty("00:00")
    duration_text = StringProperty("00:00")


KV = r"""
#:import dp kivy.metrics.dp

<Label>:
    font_name: "Vazir"
<Button>:
    font_name: "Vazir"

<ControlButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    bold: True
    font_size: "26sp"
    canvas.before:
        Color:
            rgba: (0.17, 0.17, 0.23, 1) if self.state == "normal" else (0.24, 0.24, 0.32, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [22, 22, 22, 22]

<PlayButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    bold: True
    font_size: "30sp"
    canvas.before:
        Color:
            rgba: (0.18, 0.55, 0.95, 1) if self.state == "normal" else (0.12, 0.42, 0.78, 1)
        Ellipse:
            pos: self.pos
            size: self.size

# --- Improved RTL-friendly song item ---
<SongButton@Button>:
    background_normal: ""
    background_down: ""
    color: 1, 1, 1, 1
    font_size: "15sp"
    text_size: self.width - dp(24), self.height - dp(16)
    halign: "right"
    valign: "middle"
    padding: dp(14), dp(8)
    shorten: True
    shorten_from: "left"
    line_height: 1.15
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [18, 18, 18, 18]

<RootWidget>:
    orientation: "vertical"
    padding: dp(14)
    spacing: dp(12)

    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.10, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # Header (بدون دکمه بروزرسانی)
    BoxLayout:
        size_hint_y: None
        height: dp(46)
        spacing: dp(10)

        Label:
            text: "Music Player"
            color: 1, 1, 1, 1
            font_size: "26sp"
            text_size: self.size
            halign: "left"
            valign: "middle"

    BoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: dp(140)
        padding: dp(14)
        spacing: dp(12)

        canvas.before:
            Color:
                rgba: 0.13, 0.13, 0.18, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [24, 24, 24, 24]

        Label:
            text: "M"
            size_hint_x: None
            width: dp(58)
            font_size: "34sp"
            color: 0.18, 0.55, 0.95, 1
            bold: True

        BoxLayout:
            orientation: "vertical"
            spacing: dp(4)

            Label:
                text: ""
                size_hint_y: None
                height: dp(22)
                color: 0.65, 0.75, 0.95, 1
                font_size: "12sp"
                text_size: self.size
                halign: "right"
                valign: "middle"

            Label:
                text: root.current_song_name
                color: 1, 1, 1, 1
                font_size: "22sp"
                shorten: False
                text_size: self.size
                halign: "right"
                valign: "middle"

            Label:
                text: root.current_artist
                color: 0.82, 0.82, 0.9, 1
                font_size: "14sp"
                shorten: False
                text_size: self.size
                halign: "right"
                valign: "middle"

            Label:
                text: root.status_text
                color: 0.65, 0.9, 0.75, 1
                font_size: "13sp"
                shorten: False
                text_size: self.size
                halign: "right"
                valign: "middle"

    Label:
        text: root.source_text
        size_hint_y: None
        height: dp(22)
        color: 0.75, 0.75, 0.82, 1
        font_size: "12sp"
        text_size: self.size
        halign: "right"
        valign: "middle"

    # (متن "کتابخانه" حذف شد)

    ScrollView:
        do_scroll_x: False
        bar_width: dp(7)

        GridLayout:
            id: song_list
            cols: 1
            spacing: dp(10)
            padding: [0, 0, 0, dp(8)]
            size_hint_y: None
            height: self.minimum_height

    AnchorLayout:
        anchor_x: "center"
        anchor_y: "center"
        size_hint_y: None
        height: dp(150)

        BoxLayout:
            orientation: "vertical"
            size_hint: None, None
            width: dp(360)
            height: dp(130)
            spacing: dp(8)

            BoxLayout:
                size_hint_y: None
                height: dp(28)
                spacing: dp(8)

                Label:
                    text: root.elapsed_text
                    size_hint_x: None
                    width: dp(55)
                    color: 0.85, 0.85, 0.92, 1
                    font_size: "12sp"
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

                Slider:
                    id: seek_slider
                    min: 0
                    max: 1
                    value: 0
                    step: 0
                    on_touch_down: app.seek_touch_down(self, args[1])
                    on_touch_move: app.seek_touch_move(self, args[1])
                    on_touch_up: app.seek_touch_up(self, args[1])

                Label:
                    text: root.duration_text
                    size_hint_x: None
                    width: dp(55)
                    color: 0.85, 0.85, 0.92, 1
                    font_size: "12sp"
                    halign: "right"
                    valign: "middle"
                    text_size: self.size

            BoxLayout:
                size_hint_y: None
                height: dp(86)
                spacing: dp(18)

                ControlButton:
                    text: "<<"
                    on_release: app.play_previous()

                PlayButton:
                    text: app.play_pause_icon
                    size_hint_x: None
                    width: dp(86)
                    on_release: app.toggle_play_pause()

                ControlButton:
                    text: ">>"
                    on_release: app.play_next()
"""

Builder.load_string(KV)


class MusicPlayerApp(App):
    play_pause_icon = StringProperty(">")
    _seeking = BooleanProperty(False)

    def build(self):
        self.title = "Music Player"

        # font
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "Vazirmatn-Regular.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(
                "فونت پیدا نشد. Vazirmatn-Regular.ttf را در assets/fonts/ بگذار.\n"
                f"Expected: {font_path}"
            )
        LabelBase.register(name="Vazir", fn_regular=font_path)

        self.desktop_sound = None
        self.android_player = None

        self.is_playing = False
        self.is_paused = False
        self.paused_position = 0.0

        self.song_items = []
        self.song_buttons = []
        self.current_index = -1
        self.active_index = -1

        self.seek_event = None

        self.root_widget = RootWidget()
        self.root_widget.current_song_name = rtl("هیچ آهنگی انتخاب نشده")
        self.root_widget.current_artist = rtl("از کتابخانه یک آهنگ انتخاب کنید")
        self.root_widget.status_text = rtl("در حال بارگذاری...")
        self.root_widget.source_text = rtl("منبع: نامشخص")
        return self.root_widget

    def on_start(self):
        # هر بار فقط یکبار هنگام باز شدن برنامه، لیست را بساز
        self.load_songs()
        self.seek_event = Clock.schedule_interval(self.update_seek_slider, 0.15)

    def reset_play_state(self):
        self.is_playing = False
        self.is_paused = False
        self.paused_position = 0.0
        self.play_pause_icon = ">"

    def set_playing_state(self):
        self.is_playing = True
        self.is_paused = False
        self.play_pause_icon = "||"

    def set_paused_state(self):
        self.is_playing = False
        self.is_paused = True
        self.play_pause_icon = ">"

    def has_active_player(self):
        if platform == "android":
            return self.android_player is not None
        return self.desktop_sound is not None or self.is_paused

    # -------- seekbar update --------
    def update_seek_slider(self, dt):
        if self._seeking:
            return

        slider = self.root_widget.ids.get("seek_slider")
        if not slider:
            return

        elapsed = 0.0
        duration = 0.0

        if platform == "android":
            if self.android_player and (self.is_playing or self.is_paused):
                try:
                    duration = self.android_player.getDuration() / 1000.0
                    elapsed = self.android_player.getCurrentPosition() / 1000.0
                except Exception:
                    duration, elapsed = 0.0, 0.0
        else:
            if self.desktop_sound is not None and self.is_playing:
                try:
                    duration = float(self.desktop_sound.length or 0.0)
                    elapsed = float(self.desktop_sound.get_pos() or 0.0)
                except Exception:
                    duration, elapsed = 0.0, 0.0
            elif self.is_paused and self.active_index != -1:
                duration = float(slider.max or 0.0)
                elapsed = float(self.paused_position)

        if duration and duration > 0:
            slider.max = duration
            slider.value = min(max(elapsed, 0), duration)
            self.root_widget.duration_text = fmt_time(duration)
            self.root_widget.elapsed_text = fmt_time(elapsed)
        else:
            slider.max = 1
            slider.value = 0
            self.root_widget.duration_text = "00:00"
            self.root_widget.elapsed_text = "00:00"

    # -------- dragging seek --------
    def seek_touch_down(self, slider, touch):
        if not slider.collide_point(*touch.pos):
            return
        if self.active_index == -1:
            return
        self._seeking = True

    def seek_touch_move(self, slider, touch):
        if not self._seeking:
            return
        self._seek_to(slider.value)

    def seek_touch_up(self, slider, touch):
        if not self._seeking:
            return
        self._seek_to(slider.value)
        Clock.schedule_once(lambda dt: setattr(self, "_seeking", False), 0.05)

    def _seek_to(self, seconds):
        if self.active_index == -1:
            return
        t = float(seconds)

        if platform == "android":
            if self.android_player:
                try:
                    self.android_player.seekTo(int(t * 1000))
                except Exception:
                    pass
        else:
            if self.desktop_sound and self.is_playing:
                try:
                    self.desktop_sound.seek(t)
                except Exception:
                    pass
            else:
                self.paused_position = t

        self.root_widget.elapsed_text = fmt_time(t)

    # -------- library load --------
    def load_songs(self, *args):
        self.stop_music(update_status=False)
        if platform == "android":
            self.request_android_permissions()
        else:
            self.load_desktop_songs()

    def load_desktop_songs(self):
        supported_ext = (".mp3", ".wav", ".ogg", ".m4a")
        possible_dirs = [
            os.path.join(os.path.expanduser("~"), "Music"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "music"),
        ]

        found_files, seen = [], set()
        for base_dir in possible_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                for filename in files:
                    if filename.lower().endswith(supported_ext):
                        full_path = os.path.join(root, filename)
                        if full_path not in seen:
                            seen.add(full_path)
                            found_files.append(full_path)

        items = []
        for path in found_files:
            title = os.path.splitext(os.path.basename(path))[0]
            items.append({"title": title, "artist": "Unknown Artist", "path": path})

        self.song_items = sorted(items, key=lambda x: x["title"].lower())
        self.root_widget.source_text = rtl("منبع: پوشه موسیقی ویندوز")
        self.populate_song_list()

    def request_android_permissions(self):
        try:
            from android.permissions import request_permissions
        except Exception:
            self.root_widget.status_text = rtl("ماژول مجوزهای اندروید در دسترس نیست")
            self.song_items = []
            self.populate_song_list()
            return

        permissions = [
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_AUDIO",
        ]
        self.root_widget.status_text = rtl("درخواست مجوز...")
        request_permissions(permissions, self.on_android_permissions_result)

    def on_android_permissions_result(self, permissions, grants):
        granted = any(grants)
        Clock.schedule_once(lambda dt: self.after_android_permissions(granted), 0)

    def after_android_permissions(self, granted):
        if not granted:
            self.song_items = []
            self.root_widget.source_text = rtl("منبع: موزیک‌های دستگاه")
            self.root_widget.status_text = rtl("مجوز داده نشد")
            self.populate_song_list()
            return
        self.load_android_songs()

    def load_android_songs(self):
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            MediaStore = autoclass("android.provider.MediaStore")
            ContentUris = autoclass("android.content.ContentUris")

            context = PythonActivity.mActivity
            resolver = context.getContentResolver()

            uri = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
            projection = [
                MediaStore.Audio.Media._ID,
                MediaStore.Audio.Media.TITLE,
                MediaStore.Audio.Media.ARTIST,
                MediaStore.Audio.Media.IS_MUSIC,
            ]
            selection = MediaStore.Audio.Media.IS_MUSIC + " != 0"
            sort_order = MediaStore.Audio.Media.TITLE + " ASC"

            cursor = resolver.query(uri, projection, selection, None, sort_order)

            items = []
            if cursor:
                id_index = cursor.getColumnIndex(MediaStore.Audio.Media._ID)
                title_index = cursor.getColumnIndex(MediaStore.Audio.Media.TITLE)
                artist_index = cursor.getColumnIndex(MediaStore.Audio.Media.ARTIST)

                while cursor.moveToNext():
                    song_id = cursor.getLong(id_index)
                    title = cursor.getString(title_index) or "Unknown Title"
                    artist = cursor.getString(artist_index) or "Unknown Artist"
                    if artist == "<unknown>":
                        artist = "Unknown Artist"

                    content_uri = ContentUris.withAppendedId(uri, song_id)
                    items.append({"title": title, "artist": artist, "uri": content_uri.toString()})

                cursor.close()

            self.song_items = items
            self.root_widget.source_text = rtl("منبع: موزیک‌های دستگاه")
            self.populate_song_list()

        except Exception as e:
            self.song_items = []
            self.root_widget.source_text = rtl("منبع: موزیک‌های دستگاه")
            self.root_widget.status_text = rtl(f"خطا: {str(e)}")
            self.populate_song_list()

    def populate_song_list(self):
        container = self.root_widget.ids.song_list
        container.clear_widgets()
        self.song_buttons = []

        if not self.song_items:
            self.current_index = -1
            self.active_index = -1
            self.root_widget.current_song_name = rtl("هیچ آهنگی انتخاب نشده")
            self.root_widget.current_artist = rtl("آهنگی وجود ندارد")
            self.root_widget.status_text = rtl("آهنگی پیدا نشد")
            container.add_widget(Label(text=rtl("آهنگی پیدا نشد"), size_hint_y=None, height=dp(50), color=(1, 1, 1, 1)))
            return

        for i, item in enumerate(self.song_items):
            btn = Factory.SongButton(
                text=f"{rtl(item['title'])}\n{rtl(item['artist'])}",
                size_hint_y=None,
                height=dp(74),
                background_color=(0.14, 0.14, 0.19, 1),
            )
            btn.bind(on_release=partial(self.select_song, i))
            container.add_widget(btn)
            self.song_buttons.append(btn)

        self.root_widget.status_text = rtl(f"{len(self.song_items)} آهنگ پیدا شد")
        self.refresh_selection()

    # -------- selection --------
    def select_song(self, index, *args):
        self.current_index = index
        item = self.song_items[index]

        self.root_widget.current_song_name = rtl(item["title"])
        self.root_widget.current_artist = rtl(item["artist"])
        self.refresh_selection()

        if self.active_index == self.current_index:
            if self.is_paused:
                self.root_widget.status_text = rtl("در حال پخش...")
                self.resume_current()
            elif self.is_playing:
                self.root_widget.status_text = rtl("در حال پخش...")
            else:
                self.root_widget.status_text = rtl("در حال بارگذاری...")
                self.play_selected()
            return

        self.root_widget.status_text = rtl("در حال بارگذاری...")
        self.play_selected()

    def refresh_selection(self):
        for i, btn in enumerate(self.song_buttons):
            btn.background_color = (0.18, 0.55, 0.95, 1) if i == self.current_index else (0.14, 0.14, 0.19, 1)

    # -------- playback --------
    def toggle_play_pause(self, *args):
        if not self.song_items:
            self.root_widget.status_text = rtl("آهنگی وجود ندارد")
            return

        if self.current_index == -1:
            self.select_song(0)
            return

        if self.active_index != self.current_index or not self.has_active_player():
            self.play_selected()
            return

        if self.is_paused:
            self.resume_current()
        elif self.is_playing:
            self.pause_current()
        else:
            self.play_selected()

    def play_selected(self, *args):
        if not self.song_items:
            self.root_widget.status_text = rtl("آهنگی وجود ندارد")
            return
        if self.current_index == -1:
            self.current_index = 0

        item = self.song_items[self.current_index]
        if platform == "android":
            self.play_android_song(item)
        else:
            self.play_desktop_song(item)

    def play_desktop_song(self, item):
        filepath = item.get("path")
        if not filepath or not os.path.exists(filepath):
            self.root_widget.status_text = rtl("فایل پیدا نشد")
            return

        self.stop_music(update_status=False)

        sound = SoundLoader.load(filepath)
        if sound is None:
            self.root_widget.status_text = rtl("امکان باز کردن فایل نیست")
            return

        self.desktop_sound = sound
        self.desktop_sound.play()

        self.paused_position = 0.0

        slider = self.root_widget.ids.get("seek_slider")
        if slider:
            slider.value = 0
            slider.max = float(self.desktop_sound.length or 1)

        self.root_widget.elapsed_text = "00:00"
        self.root_widget.duration_text = fmt_time(float(self.desktop_sound.length or 0))

        self.active_index = self.current_index
        self.root_widget.status_text = rtl("در حال پخش...")
        self.set_playing_state()

    def play_android_song(self, item):
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Uri = autoclass("android.net.Uri")
            MediaPlayer = autoclass("android.media.MediaPlayer")
            AudioManager = autoclass("android.media.AudioManager")

            context = PythonActivity.mActivity

            self.stop_music(update_status=False)

            player = MediaPlayer()
            player.setAudioStreamType(AudioManager.STREAM_MUSIC)
            player.setDataSource(context, Uri.parse(item["uri"]))
            player.prepare()
            player.start()

            self.android_player = player
            self.active_index = self.current_index
            self.paused_position = 0.0

            self.root_widget.elapsed_text = "00:00"
            self.root_widget.duration_text = "00:00"

            slider = self.root_widget.ids.get("seek_slider")
            if slider:
                slider.value = 0
                slider.max = 1

            self.root_widget.status_text = rtl("در حال پخش...")
            self.set_playing_state()

        except Exception as e:
            self.root_widget.status_text = rtl(f"خطا در پخش: {str(e)}")

    def pause_current(self):
        if self.active_index == -1:
            return

        if platform == "android":
            if self.android_player:
                try:
                    self.android_player.pause()
                    self.root_widget.status_text = rtl("مکث")
                    self.set_paused_state()
                except Exception as e:
                    self.root_widget.status_text = rtl(f"خطا: {str(e)}")
        else:
            if self.desktop_sound:
                try:
                    pos = self.desktop_sound.get_pos()
                    self.paused_position = float(pos or 0.0)
                except Exception:
                    self.paused_position = 0.0

                try:
                    self.desktop_sound.stop()
                except Exception:
                    pass
                self.desktop_sound = None

                self.root_widget.elapsed_text = fmt_time(self.paused_position)
                self.root_widget.status_text = rtl("مکث")
                self.set_paused_state()

    def resume_current(self):
        if self.active_index == -1:
            return

        item = self.song_items[self.active_index]

        if platform == "android":
            if self.android_player:
                try:
                    self.android_player.start()
                    self.root_widget.status_text = rtl("در حال پخش...")
                    self.set_playing_state()
                except Exception as e:
                    self.root_widget.status_text = rtl(f"خطا: {str(e)}")
        else:
            filepath = item.get("path")
            if not filepath or not os.path.exists(filepath):
                self.root_widget.status_text = rtl("فایل پیدا نشد")
                return

            sound = SoundLoader.load(filepath)
            if sound is None:
                self.root_widget.status_text = rtl("امکان باز کردن فایل نیست")
                return

            self._seeking = True
            self.desktop_sound = sound
            self.desktop_sound.play()

            seek_position = float(self.paused_position)
            if seek_position > 0:
                Clock.schedule_once(lambda dt: self.seek_desktop_resume(seek_position), 0.18)
            else:
                Clock.schedule_once(lambda dt: setattr(self, "_seeking", False), 0.05)

            self.root_widget.status_text = rtl("در حال پخش...")
            self.set_playing_state()

    def seek_desktop_resume(self, position):
        if self.desktop_sound:
            try:
                self.desktop_sound.seek(position)
            except Exception:
                pass

        slider = self.root_widget.ids.get("seek_slider")
        if slider:
            slider.value = float(position)

        self.root_widget.elapsed_text = fmt_time(position)
        Clock.schedule_once(lambda dt: setattr(self, "_seeking", False), 0.05)

    def stop_music(self, *args, update_status=True):
        if self.desktop_sound:
            try:
                self.desktop_sound.stop()
            except Exception:
                pass
            self.desktop_sound = None

        if self.android_player:
            try:
                self.android_player.stop()
            except Exception:
                pass
            try:
                self.android_player.reset()
            except Exception:
                pass
            try:
                self.android_player.release()
            except Exception:
                pass
            self.android_player = None

        self.active_index = -1
        self.reset_play_state()

        slider = self.root_widget.ids.get("seek_slider")
        if slider and not self._seeking:
            slider.max = 1
            slider.value = 0

        self.root_widget.elapsed_text = "00:00"
        self.root_widget.duration_text = "00:00"

        if update_status:
            self.root_widget.status_text = rtl("ایستاد")

    def play_next(self, *args):
        if not self.song_items:
            return
        self.current_index = 0 if self.current_index == -1 else (self.current_index + 1) % len(self.song_items)
        self.select_song(self.current_index)

    def play_previous(self, *args):
        if not self.song_items:
            return
        self.current_index = 0 if self.current_index == -1 else (self.current_index - 1) % len(self.song_items)
        self.select_song(self.current_index)

    def on_stop(self):
        if self.seek_event:
            try:
                self.seek_event.cancel()
            except Exception:
                pass
        self.stop_music(update_status=False)


if __name__ == "__main__":
    MusicPlayerApp().run()
