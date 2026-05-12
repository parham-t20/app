"""
NOVA Music Player
=================
Cross-platform music player for Windows & Android
Built with Python + Kivy + Pygame

Features:
  - Play MP3 / WAV / OGG / FLAC / M4A / AAC
  - Play / Pause / Previous / Next
  - Seek bar with time display
  - Volume control
  - Shuffle & Repeat (Off / One / All)
  - Scrollable playlist with per-track removal
  - Add files or entire folders (tkinter dialog on Windows)
  - Auto-save & restore playlist (JSON)
  - ID3 tag reading via mutagen (title, artist, album, duration)
  - Spinning vinyl disc animation
  - VU meter visualizer
  - Modern dark purple theme – pure Python widgets (no KV bugs)

Install:
    pip install kivy pygame mutagen

Run:
    python music_player.py

Build for Android (Linux / WSL):
    pip install buildozer
    buildozer init   # edit buildozer.spec as needed
    buildozer android debug
"""

# ── stdlib ────────────────────────────────────────────────────
import os
import json
import math
import random
import time
from pathlib import Path

# ── Kivy env/config MUST come before any other kivy import ────
os.environ.setdefault("KIVY_AUDIO", "pygame")

from kivy.config import Config
Config.set("graphics", "width",     "420")
Config.set("graphics", "height",    "800")
Config.set("graphics", "resizable", "1")
Config.set("kivy",     "window_icon", "")

# ── Kivy imports ──────────────────────────────────────────────
from kivy.app            import App
from kivy.clock          import Clock
from kivy.core.window    import Window
from kivy.metrics        import dp, sp
from kivy.animation      import Animation

from kivy.graphics import (
    Color, Rectangle, Ellipse, Line,
    RoundedRectangle,
)

from kivy.properties import (
    StringProperty, NumericProperty,
    BooleanProperty, ListProperty,
)

from kivy.uix.widget      import Widget
from kivy.uix.label       import Label
from kivy.uix.button      import Button
from kivy.uix.slider      import Slider
from kivy.uix.boxlayout   import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview  import ScrollView
from kivy.uix.gridlayout  import GridLayout
from kivy.uix.popup       import Popup
from kivy.uix.behaviors   import ButtonBehavior

# ── Optional: mutagen ─────────────────────────────────────────
try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# ── Pygame audio ──────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    HAS_PYGAME = True
except Exception as _e:
    HAS_PYGAME = False
    print(f"[NOVA] pygame not available: {_e}")

# ── Platform detection ────────────────────────────────────────
try:
    from kivy.utils import platform as _plat
    PLATFORM = _plat
except Exception:
    PLATFORM = "unknown"

IS_ANDROID = (PLATFORM == "android")

if IS_ANDROID:
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ])
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  THEME  (all RGBA tuples)
# ═══════════════════════════════════════════════════════════════
C_BG       = (0.06, 0.06, 0.09, 1)
C_SURFACE  = (0.10, 0.10, 0.14, 1)
C_CARD     = (0.13, 0.12, 0.18, 1)
C_ITEM     = (0.11, 0.11, 0.16, 1)
C_ITEM_SEL = (0.19, 0.11, 0.30, 1)
C_ACCENT   = (0.58, 0.25, 0.95, 1)   # violet
C_PINK     = (0.93, 0.25, 0.56, 1)   # pink
C_TEXT     = (0.94, 0.94, 0.96, 1)
C_MUTED    = (0.45, 0.45, 0.58, 1)

SUPPORTED_EXT = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
PLAYLIST_PATH = os.path.join(
    os.path.expanduser("~"), ".nova_music_playlist.json"
)

# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def fmt_time(seconds):
    try:
        s = int(max(0.0, float(seconds)))
        return f"{s // 60}:{s % 60:02d}"
    except Exception:
        return "0:00"


def get_track_info(path):
    """Return (title, artist, album, duration_seconds)."""
    title  = Path(path).stem
    artist = "Unknown Artist"
    album  = "Unknown Album"
    dur    = 0.0
    if HAS_MUTAGEN:
        try:
            easy = MutagenFile(path, easy=True)
            if easy:
                title  = str(easy.get("title",  [title])[0])
                artist = str(easy.get("artist", [artist])[0])
                album  = str(easy.get("album",  [album])[0])
            raw = MutagenFile(path)
            if raw and hasattr(raw, "info"):
                dur = float(raw.info.length)
        except Exception:
            pass
    return title, artist, album, dur


# ═══════════════════════════════════════════════════════════════
#  AUDIO ENGINE
# ═══════════════════════════════════════════════════════════════

class AudioEngine:
    def __init__(self):
        self._path     = None
        self._duration = 0.0
        self._start_t  = 0.0   # wall-clock when play() was called
        self._offset   = 0.0   # seek position
        self.paused    = False
        self.volume    = 0.8
        if HAS_PYGAME:
            pygame.mixer.music.set_volume(self.volume)

    def load(self, path, duration):
        try:
            if HAS_PYGAME:
                pygame.mixer.music.load(path)
            self._path     = path
            self._duration = duration
            self._offset   = 0.0
            self._start_t  = 0.0
            self.paused    = False
            return True
        except Exception as e:
            print(f"[AudioEngine.load] {e}")
            return False

    def play(self):
        if not HAS_PYGAME or not self._path:
            return
        try:
            pygame.mixer.music.play(start=self._offset)
            self._start_t = time.time() - self._offset
            self.paused   = False
        except Exception as e:
            print(f"[AudioEngine.play] {e}")

    def pause(self):
        if not HAS_PYGAME or self.paused:
            return
        pygame.mixer.music.pause()
        self._offset = self.position
        self.paused  = True

    def resume(self):
        if not HAS_PYGAME or not self.paused:
            return
        pygame.mixer.music.unpause()
        self._start_t = time.time() - self._offset
        self.paused   = False

    def stop(self):
        if HAS_PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._offset  = 0.0
        self._start_t = 0.0
        self.paused   = False

    def seek(self, seconds):
        if not HAS_PYGAME or not self._path:
            return
        seconds = max(0.0, min(float(seconds), self._duration))
        try:
            pygame.mixer.music.play(start=seconds)
            self._offset  = seconds
            self._start_t = time.time() - seconds
            self.paused   = False
        except Exception as e:
            print(f"[AudioEngine.seek] {e}")

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        if HAS_PYGAME:
            pygame.mixer.music.set_volume(self.volume)

    @property
    def position(self):
        if self.paused:
            return self._offset
        if HAS_PYGAME and pygame.mixer.music.get_busy():
            return time.time() - self._start_t
        return self._offset

    @property
    def duration(self):
        return self._duration

    @property
    def is_busy(self):
        return HAS_PYGAME and pygame.mixer.music.get_busy()

    def quit(self):
        self.stop()
        if HAS_PYGAME:
            try:
                pygame.mixer.quit()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════
#  VU METER
# ═══════════════════════════════════════════════════════════════

class VUMeter(Widget):
    levels = ListProperty([0.0] * 20)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(levels=self._draw, pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        n     = len(self.levels)
        gap   = dp(2)
        bar_w = max(1.0, (self.width - gap * (n - 1)) / n)
        with self.canvas:
            for i, lv in enumerate(self.levels):
                x    = self.x + i * (bar_w + gap)
                h    = max(dp(3), lv * self.height)
                frac = i / max(1, n - 1)
                r    = min(1.0, frac * 2.0)
                g    = min(1.0, (1.0 - frac) * 2.0)
                Color(r, g, 0.4, 0.25 + 0.75 * lv)
                RoundedRectangle(
                    pos=(x, self.y), size=(bar_w, h), radius=[dp(2)]
                )


# ═══════════════════════════════════════════════════════════════
#  VINYL DISC
# ═══════════════════════════════════════════════════════════════

class VinylDisc(Widget):
    angle    = NumericProperty(0)
    spinning = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, angle=self._draw)
        self._anim = None

    def _draw(self, *_):
        self.canvas.clear()
        cx = self.center_x
        cy = self.center_y
        r  = min(self.width, self.height) / 2.0 - dp(4)

        with self.canvas:
            # outer disc body
            Color(0.12, 0.08, 0.22, 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            # groove rings
            for i in range(7):
                rr = r * (0.92 - i * 0.09)
                Color(0.22, 0.14, 0.35, 0.55)
                Line(circle=(cx, cy, rr), width=dp(0.7))

            # rotating highlight
            a_rad = math.radians(self.angle)
            hx = cx + r * 0.52 * math.cos(a_rad)
            hy = cy + r * 0.52 * math.sin(a_rad)
            Color(1, 1, 1, 0.06)
            Ellipse(
                pos=(hx - r * 0.20, hy - r * 0.13),
                size=(r * 0.40, r * 0.26)
            )

            # center label (accent circle)
            rl = r * 0.29
            Color(*C_ACCENT)
            Ellipse(pos=(cx - rl, cy - rl), size=(rl * 2, rl * 2))

            # inner ring on label
            Color(0.75, 0.45, 1.0, 0.45)
            Line(circle=(cx, cy, rl * 0.68), width=dp(0.9))

            # spindle hole
            rh = dp(4)
            Color(*C_BG)
            Ellipse(pos=(cx - rh, cy - rh), size=(rh * 2, rh * 2))

    def start_spin(self):
        if self.spinning:
            return
        self.spinning = True
        self._step()

    def stop_spin(self):
        self.spinning = False
        if self._anim:
            self._anim.cancel(self)

    def _step(self, *_):
        if not self.spinning:
            return
        self._anim = Animation(
            angle=self.angle + 360, duration=3.6, transition="linear"
        )
        self._anim.bind(on_complete=self._step)
        self._anim.start(self)


# ═══════════════════════════════════════════════════════════════
#  PLAYLIST ROW  (pure Python – no KV, no RecycleView issues)
# ═══════════════════════════════════════════════════════════════

class PlaylistRow(ButtonBehavior, BoxLayout):
    def __init__(self, index, title, artist, duration,
                 selected=False, on_play=None, on_remove=None, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(58))
        super().__init__(orientation="horizontal", **kw)
        self._index     = index
        self._on_play   = on_play
        self._on_remove = on_remove
        self._build(index, title, artist, duration, selected)

    def _build(self, index, title, artist, duration, selected):
        self.padding = [dp(8), dp(4), dp(6), dp(4)]
        self.spacing = dp(6)

        # track number
        self.add_widget(Label(
            text=str(index + 1),
            size_hint=(None, 1), width=dp(28),
            font_size=sp(11), bold=selected,
            color=list(C_ACCENT) if selected else list(C_MUTED),
        ))

        # title + artist
        info = BoxLayout(orientation="vertical", spacing=dp(2))
        lbl_t = Label(
            text=title, font_size=sp(13), bold=selected,
            color=list(C_TEXT) if selected else (0.82, 0.82, 0.88, 1),
            halign="left", valign="middle",
            shorten=True, shorten_from="right",
        )
        lbl_t.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        lbl_a = Label(
            text=artist, font_size=sp(11),
            color=list(C_ACCENT) if selected else list(C_MUTED),
            halign="left", valign="middle",
            shorten=True, shorten_from="right",
        )
        lbl_a.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        info.add_widget(lbl_t)
        info.add_widget(lbl_a)
        self.add_widget(info)

        # duration
        self.add_widget(Label(
            text=duration,
            size_hint=(None, 1), width=dp(40),
            font_size=sp(11), color=list(C_MUTED),
        ))

        # remove button
        btn_del = Button(
            text="✕",
            size_hint=(None, None), size=(dp(26), dp(26)),
            font_size=sp(12),
            background_normal="", background_color=(0.30, 0.08, 0.08, 1),
            color=(0.90, 0.40, 0.40, 1),
        )
        btn_del.bind(
            on_release=lambda *_: self._on_remove and self._on_remove(self._index)
        )
        self.add_widget(btn_del)

        # background drawn in canvas.before
        with self.canvas.before:
            self._bg_col  = Color(*(C_ITEM_SEL if selected else C_ITEM))
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(10)]
            )
        self.bind(pos=self._upd_bg, size=self._upd_bg)

    def _upd_bg(self, *_):
        self._bg_rect.pos  = (self.x + dp(3), self.y + dp(2))
        self._bg_rect.size = (self.width - dp(6), self.height - dp(4))

    def on_release(self):
        if self._on_play:
            self._on_play(self._index)


# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

class NovaMusicApp(App):
    title = "NOVA Music Player"

    _tracks     = []
    _cur_idx    = -1
    _is_playing = False
    _seeking    = False
    _repeat     = 0      # 0=off  1=one  2=all
    _shuffle    = False
    _vu_t       = 0.0

    # ── lifecycle ─────────────────────────────────────────────

    def build(self):
        Window.clearcolor = C_BG
        self.engine = AudioEngine()
        self._load_playlist_file()
        ui = self._build_ui()
        Clock.schedule_interval(self._tick,    0.15)
        Clock.schedule_interval(self._vu_tick, 0.055)
        return ui

    def on_stop(self):
        self.engine.quit()

    # ═══════════════════════════════════════════════════════════
    #  UI BUILD
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        root = BoxLayout(
            orientation="vertical",
            padding=[dp(12), dp(10), dp(12), dp(8)],
            spacing=dp(8),
        )
        # root background
        with root.canvas.before:
            Color(*C_BG)
            self._root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos =lambda w, _: setattr(self._root_bg, "pos",  w.pos),
            size=lambda w, _: setattr(self._root_bg, "size", w.size),
        )

        root.add_widget(self._build_header())
        root.add_widget(self._build_player_card())
        root.add_widget(self._build_seek_row())
        root.add_widget(self._build_controls())
        root.add_widget(self._build_volume_row())
        root.add_widget(self._build_playlist_header())
        root.add_widget(self._build_playlist_area())
        return root

    # ─── header ───────────────────────────────────────────────

    def _build_header(self):
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        row.add_widget(Label(
            text="♪  NOVA",
            font_size=sp(20), bold=True, color=C_ACCENT,
            size_hint_x=None, width=dp(110),
            halign="left",
        ))
        row.add_widget(Widget())
        row.add_widget(self._btn("+ File",   self._open_file_dialog,   C_ACCENT,  dp(76), dp(36)))
        row.add_widget(self._btn("+ Folder", self._open_folder_dialog, C_SURFACE, dp(82), dp(36)))
        row.add_widget(self._btn("💾",       self._save_playlist,      C_SURFACE, dp(36), dp(36)))
        return row

    # ─── player card ──────────────────────────────────────────

    def _build_player_card(self):
        card = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(200),
            padding=[dp(14), dp(12)],
            spacing=dp(12),
        )
        with card.canvas.before:
            Color(*C_CARD)
            self._card_bg = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(18)]
            )
        card.bind(
            pos =lambda w, _: setattr(self._card_bg, "pos",  w.pos),
            size=lambda w, _: setattr(self._card_bg, "size", w.size),
        )

        # vinyl disc on the left
        self.disc = VinylDisc(size_hint=(None, 1), width=dp(168))
        card.add_widget(self.disc)

        # info panel on the right
        info = BoxLayout(orientation="vertical", spacing=dp(5))
        self.lbl_title  = self._mk_info_label("No track selected", sp(14), C_TEXT, bold=True)
        self.lbl_artist = self._mk_info_label("Unknown Artist",    sp(12), C_ACCENT)
        self.lbl_album  = self._mk_info_label("",                  sp(11), C_MUTED)
        self.lbl_time   = self._mk_info_label("0:00 / 0:00",       sp(11), C_MUTED)
        self.vu         = VUMeter(size_hint=(1, None), height=dp(32))
        info.add_widget(self.lbl_title)
        info.add_widget(self.lbl_artist)
        info.add_widget(self.lbl_album)
        info.add_widget(self.lbl_time)
        info.add_widget(Widget())
        info.add_widget(self.vu)
        card.add_widget(info)
        return card

    def _mk_info_label(self, text, size, color, bold=False):
        lbl = Label(
            text=text, font_size=size, bold=bold, color=color,
            halign="left", valign="middle",
            shorten=True, shorten_from="right",
        )
        lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        return lbl

    # ─── seek bar ─────────────────────────────────────────────

    def _build_seek_row(self):
        row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(6))
        self.lbl_pos = Label(
            text="0:00", font_size=sp(11), color=C_MUTED,
            size_hint_x=None, width=dp(36),
        )
        self.seek_bar = Slider(
            min=0, max=1, value=0,
            value_track=True, value_track_color=list(C_ACCENT),
            value_track_width=dp(3), cursor_size=(dp(14), dp(14)),
        )
        self.seek_bar.bind(
            on_touch_down=self._seek_down,
            on_touch_up=self._seek_up,
        )
        self.lbl_dur = Label(
            text="0:00", font_size=sp(11), color=C_MUTED,
            size_hint_x=None, width=dp(36),
        )
        row.add_widget(self.lbl_pos)
        row.add_widget(self.seek_bar)
        row.add_widget(self.lbl_dur)
        return row

    # ─── controls ─────────────────────────────────────────────

    def _build_controls(self):
        row = BoxLayout(
            size_hint_y=None, height=dp(68),
            spacing=dp(6), padding=[dp(4), 0],
        )
        self.btn_shuffle = self._icon_btn("⇄", self._toggle_shuffle, dp(44), sp(20), C_SURFACE)
        self.btn_prev    = self._icon_btn("⏮", self._prev,           dp(52), sp(24), C_SURFACE)
        self.btn_play    = self._icon_btn("▶", self._toggle_play,    dp(64), sp(30), C_ACCENT)
        self.btn_next    = self._icon_btn("⏭", self._next,           dp(52), sp(24), C_SURFACE)
        self.btn_repeat  = self._icon_btn("↻", self._toggle_repeat,  dp(44), sp(20), C_SURFACE)

        row.add_widget(self.btn_shuffle)
        row.add_widget(Widget())
        row.add_widget(self.btn_prev)
        row.add_widget(self.btn_play)
        row.add_widget(self.btn_next)
        row.add_widget(Widget())
        row.add_widget(self.btn_repeat)
        return row

    # ─── volume ───────────────────────────────────────────────

    def _build_volume_row(self):
        row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        row.add_widget(Label(
            text="🔊", font_size=sp(16), color=C_MUTED,
            size_hint_x=None, width=dp(28),
        ))
        self.vol_slider = Slider(
            min=0, max=1, value=0.8,
            value_track=True, value_track_color=list(C_PINK),
            value_track_width=dp(2), cursor_size=(dp(12), dp(12)),
        )
        self.vol_slider.bind(value=lambda _, v: self.engine.set_volume(v))
        row.add_widget(self.vol_slider)
        return row

    # ─── playlist header ──────────────────────────────────────

    def _build_playlist_header(self):
        row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
        row.add_widget(Label(
            text="PLAYLIST", font_size=sp(11), bold=True,
            color=C_MUTED, size_hint_x=None, width=dp(72),
        ))
        self.lbl_count = Label(text="0 tracks", font_size=sp(11), color=C_MUTED)
        row.add_widget(self.lbl_count)
        row.add_widget(Widget())
        row.add_widget(self._btn(
            "Clear All", self._clear_playlist,
            (0.22, 0.06, 0.06, 1), dp(80), dp(26), font=sp(11),
        ))
        return row

    # ─── playlist scroll area ─────────────────────────────────

    def _build_playlist_area(self):
        # card background container
        wrap = FloatLayout()
        with wrap.canvas.before:
            Color(*C_SURFACE)
            self._pl_bg = RoundedRectangle(
                pos=wrap.pos, size=wrap.size, radius=[dp(14)]
            )
        wrap.bind(
            pos =lambda w, _: setattr(self._pl_bg, "pos",  w.pos),
            size=lambda w, _: setattr(self._pl_bg, "size", w.size),
        )

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.pl_box = GridLayout(
            cols=1, spacing=dp(2),
            padding=[dp(6), dp(6), dp(6), dp(6)],
            size_hint_y=None,
        )
        self.pl_box.bind(minimum_height=self.pl_box.setter("height"))
        self.scroll.add_widget(self.pl_box)
        wrap.add_widget(self.scroll)
        return wrap

    # ── small widget factories ────────────────────────────────

    def _btn(self, text, cb, bg, w=dp(88), h=dp(36), font=sp(12)):
        b = Button(
            text=text, size_hint=(None, None), size=(w, h),
            font_size=font, bold=True,
            background_normal="", background_color=bg, color=C_TEXT,
        )
        b.bind(on_release=lambda *_: cb())
        return b

    def _icon_btn(self, text, cb, size=dp(44), font=sp(22), bg=C_SURFACE):
        b = Button(
            text=text, size_hint=(None, None), size=(size, size),
            font_size=font, bold=True,
            background_normal="", background_color=bg, color=C_TEXT,
        )
        b.bind(on_release=lambda *_: cb())
        return b

    # ═══════════════════════════════════════════════════════════
    #  CLOCK CALLBACKS
    # ═══════════════════════════════════════════════════════════

    def _tick(self, dt):
        if self._cur_idx < 0 or not self._is_playing:
            return
        dur = self.engine.duration
        pos = self.engine.position

        if dur > 0 and not self._seeking:
            self.seek_bar.max   = dur
            self.seek_bar.value = min(pos, dur)

        self.lbl_pos.text  = fmt_time(pos)
        self.lbl_dur.text  = fmt_time(dur)
        self.lbl_time.text = f"{fmt_time(pos)} / {fmt_time(dur)}"

        if self._is_playing and not self.engine.is_busy:
            self._on_track_end()

    def _vu_tick(self, dt):
        if not self._is_playing:
            self.vu.levels = [0.0] * 20
            return
        self._vu_t += dt * 5.0
        t = self._vu_t
        self.vu.levels = [
            abs(math.sin(t * (0.55 + i * 0.19) + i * 0.52))
            * (0.28 + 0.72 * random.random())
            for i in range(20)
        ]

    # ═══════════════════════════════════════════════════════════
    #  PLAYBACK
    # ═══════════════════════════════════════════════════════════

    def play_track(self, idx):
        if idx < 0 or idx >= len(self._tracks):
            return
        self._cur_idx = idx
        t = self._tracks[idx]
        if self.engine.load(t["path"], t["dur_sec"]):
            self.engine.play()
            self._is_playing    = True
            self.btn_play.text  = "⏸"
            self.lbl_title.text  = t["title"]
            self.lbl_artist.text = t["artist"]
            self.lbl_album.text  = t["album"]
            self.disc.start_spin()
            self._refresh_playlist_ui()
        else:
            self._popup("Error", f"Cannot open:\n{t['path']}")

    def _toggle_play(self):
        if self._cur_idx < 0:
            if self._tracks:
                self.play_track(0)
            return
        if self._is_playing:
            self.engine.pause()
            self._is_playing   = False
            self.btn_play.text = "▶"
            self.disc.stop_spin()
        else:
            self.engine.resume()
            self._is_playing   = True
            self.btn_play.text = "⏸"
            self.disc.start_spin()

    def _prev(self):
        if not self._tracks:
            return
        idx = (random.randrange(len(self._tracks)) if self._shuffle
               else (self._cur_idx - 1) % len(self._tracks))
        self.play_track(idx)

    def _next(self):
        if not self._tracks:
            return
        idx = (random.randrange(len(self._tracks)) if self._shuffle
               else (self._cur_idx + 1) % len(self._tracks))
        self.play_track(idx)

    def _on_track_end(self):
        if self._repeat == 1:
            self.play_track(self._cur_idx)
        elif self._repeat == 2 or self._shuffle:
            self._next()
        elif self._cur_idx < len(self._tracks) - 1:
            self._next()
        else:
            self._is_playing   = False
            self.btn_play.text = "▶"
            self.disc.stop_spin()

    # ── seek ──────────────────────────────────────────────────

    def _seek_down(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._seeking = True

    def _seek_up(self, widget, touch):
        if self._seeking:
            self._seeking = False
            self.engine.seek(widget.value)

    # ── shuffle / repeat ──────────────────────────────────────

    def _toggle_shuffle(self):
        self._shuffle = not self._shuffle
        self.btn_shuffle.background_color = (
            list(C_ACCENT) if self._shuffle else list(C_SURFACE)
        )

    def _toggle_repeat(self):
        self._repeat = (self._repeat + 1) % 3
        self.btn_repeat.text             = ["↻", "🔂", "🔁"][self._repeat]
        self.btn_repeat.background_color = [
            list(C_SURFACE), list(C_ACCENT), list(C_PINK)
        ][self._repeat]

    # ═══════════════════════════════════════════════════════════
    #  FILE MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def _open_file_dialog(self):
        if IS_ANDROID:
            self._android_pick()
            return
        try:
            import tkinter as tk
            from tkinter import filedialog
            r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
            paths = filedialog.askopenfilenames(
                title="Select audio files",
                filetypes=[
                    ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a *.aac"),
                    ("All files", "*.*"),
                ],
            )
            r.destroy()
            n = sum(1 for p in paths if self._add_track(p))
            if n:
                self._popup("Added", f"{n} track(s) added to playlist.")
        except Exception as e:
            self._popup("Error", str(e))

    def _open_folder_dialog(self):
        if IS_ANDROID:
            self._popup("Info", "On Android please add files one by one.")
            return
        try:
            import tkinter as tk
            from tkinter import filedialog
            r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="Select music folder")
            r.destroy()
            if not folder:
                return
            files = sorted(Path(folder).rglob("*"))
            n = sum(1 for f in files
                    if f.suffix.lower() in SUPPORTED_EXT
                    and self._add_track(str(f)))
            self._popup("Folder Loaded", f"{n} track(s) added.")
        except Exception as e:
            self._popup("Error", str(e))

    def _android_pick(self):
        try:
            from jnius import autoclass
            Intent  = autoclass("android.content.Intent")
            ctx     = autoclass("org.kivy.android.PythonActivity").mActivity
            intent  = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("audio/*")
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
            ctx.startActivityForResult(intent, 1001)
        except Exception as e:
            self._popup("Error", str(e))

    def _add_track(self, path):
        path = str(path)
        if Path(path).suffix.lower() not in SUPPORTED_EXT:
            return False
        if not os.path.isfile(path):
            return False
        if any(t["path"] == path for t in self._tracks):
            return False
        title, artist, album, dur_sec = get_track_info(path)
        self._tracks.append({
            "path":     path,
            "title":    title,
            "artist":   artist,
            "album":    album,
            "dur_sec":  dur_sec,
            "duration": fmt_time(dur_sec),
        })
        self._refresh_playlist_ui()
        return True

    def remove_track(self, idx):
        if idx < 0 or idx >= len(self._tracks):
            return
        self._tracks.pop(idx)
        if idx == self._cur_idx:
            self.engine.stop()
            self._is_playing   = False
            self._cur_idx      = -1
            self.btn_play.text = "▶"
            self.disc.stop_spin()
            self.lbl_title.text  = "No track selected"
            self.lbl_artist.text = "Unknown Artist"
            self.lbl_album.text  = ""
            self.lbl_time.text   = "0:00 / 0:00"
        elif idx < self._cur_idx:
            self._cur_idx -= 1
        self._refresh_playlist_ui()

    def _clear_playlist(self):
        self.engine.stop()
        self._tracks       = []
        self._cur_idx      = -1
        self._is_playing   = False
        self.btn_play.text = "▶"
        self.disc.stop_spin()
        self.lbl_title.text  = "No track selected"
        self.lbl_artist.text = "Unknown Artist"
        self.lbl_album.text  = ""
        self.lbl_time.text   = "0:00 / 0:00"
        self._refresh_playlist_ui()

    # ═══════════════════════════════════════════════════════════
    #  PLAYLIST UI
    # ═══════════════════════════════════════════════════════════

    def _refresh_playlist_ui(self):
        self.pl_box.clear_widgets()
        for i, t in enumerate(self._tracks):
            row = PlaylistRow(
                index    = i,
                title    = t["title"],
                artist   = t["artist"],
                duration = t["duration"],
                selected = (i == self._cur_idx),
                on_play  = self.play_track,
                on_remove= self.remove_track,
            )
            self.pl_box.add_widget(row)
        n = len(self._tracks)
        self.lbl_count.text = f"{n} track{'s' if n != 1 else ''}"

    # ═══════════════════════════════════════════════════════════
    #  SAVE / LOAD
    # ═══════════════════════════════════════════════════════════

    def _save_playlist(self):
        try:
            data = [t["path"] for t in self._tracks]
            with open(PLAYLIST_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._popup("Saved", f"Playlist saved — {len(data)} track(s).")
        except Exception as e:
            self._popup("Error", str(e))

    def _load_playlist_file(self):
        try:
            if os.path.isfile(PLAYLIST_PATH):
                with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
                    paths = json.load(f)
                for p in paths:
                    self._add_track(p)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  POPUP
    # ═══════════════════════════════════════════════════════════

    def _popup(self, title, message):
        content = BoxLayout(
            orientation="vertical", spacing=dp(10), padding=dp(14)
        )
        lbl = Label(
            text=message, font_size=sp(13), color=C_TEXT,
            halign="center", text_size=(dp(260), None),
        )
        content.add_widget(lbl)
        ok = Button(
            text="OK", size_hint_y=None, height=dp(40),
            background_normal="", background_color=list(C_ACCENT),
            color=C_TEXT, bold=True,
        )
        content.add_widget(ok)
        pop = Popup(
            title=title, content=content,
            size_hint=(None, None), size=(dp(300), dp(190)),
            background_color=list(C_CARD),
            title_color=list(C_ACCENT),
            separator_color=list(C_ACCENT),
        )
        ok.bind(on_release=pop.dismiss)
        pop.open()


# ═══════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    NovaMusicApp().run()
