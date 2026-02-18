from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Rectangle
from kivy.uix.widget import Widget
from kivy.lang import Builder
import math
import sqlite3
import os
from datetime import datetime

Window.size = (420, 780)
Window.clearcolor = get_color_from_hex("#0A1628")


# ==========================================
#  DATABASE MANAGER
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'auto_fogger.db'
        )
        self._create_table()

    def _create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                duration TEXT,
                reason TEXT,
                date TEXT,
                time TEXT,
                created_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        # Default admin insert kara
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         ("Admin", "admin@fogger.com", "admin123", "admin"))
        conn.commit()
        conn.close()

    def check_login(self, email, password):
        """Email + password ne login check kara"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, role FROM users WHERE email=? AND password=?",
                      (email, password))
        row = cursor.fetchone()
        conn.close()
        return row if row else None

    def get_all_users(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role FROM users ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def add_user(self, name, email, password, role):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                          (name, email, password, role))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    def delete_user(self, email):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email=? AND email != 'admin@fogger.com'",
                      (email,))
        conn.commit()
        conn.close()

    def save_event(self, status, temperature, humidity, duration, reason):
        now = datetime.now()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history
            (status, temperature, humidity, duration, reason, date, time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            status, temperature, humidity, duration, reason,
            now.strftime("%d %b %Y"),
            now.strftime("%I:%M %p"),
            now.strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

    def get_all_events(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, status, temperature, humidity, duration, reason, date, time
            FROM history ORDER BY id DESC LIMIT 50000
        ''')
        rows = cursor.fetchall()
        conn.close()
        return rows

    def delete_all(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history')
        conn.commit()
        conn.close()

    def get_count(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM history')
        count = cursor.fetchone()[0]
        conn.close()
        return count


db = DatabaseManager()


# ==========================================
#  NOTIFICATION WIDGET (Popup Banner)
# ==========================================
class NotificationBanner(MDCard):
    """Animated notification banner that slides in from top"""

    def __init__(self, message, notif_type='warning', **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.92, None)
        self.height = dp(70)
        self.pos_hint = {'center_x': 0.5}
        self.elevation = 12
        self.radius = [12]

        # Colors
        colors = {
            'warning':  ("#7B2D00", "#FF6D00", "#FFE0B2"),
            'danger':   ("#7B0000", "#FF1744", "#FFCDD2"),
            'success':  ("#1B5E20", "#00C853", "#C8E6C9"),
            'info':     ("#0D47A1", "#2979FF", "#BBDEFB"),
        }
        bg_hex, accent_hex, text_hex = colors.get(notif_type, colors['info'])

        with self.canvas.before:
            Color(*get_color_from_hex(bg_hex)[:3], 1)
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[12]
            )
            Color(*get_color_from_hex(accent_hex)[:3], 1)
            self._left_bar = Rectangle(
                pos=self.pos, size=(dp(5), self.height)
            )

        self.bind(pos=self._update_bg, size=self._update_bg)

        layout = MDBoxLayout(
            padding=[dp(16), dp(10), dp(16), dp(10)],
            spacing=dp(8),
        )

        # Icon label
        icon_map = {
            'warning': 'ALERT',
            'danger':  'DANGER',
            'success': 'OK',
            'info':    'INFO',
        }
        icon_lbl = MDLabel(
            text=icon_map.get(notif_type, 'INFO'),
            bold=True,
            size_hint=(None, None),
            size=(dp(55), dp(28)),
            halign='center',
            font_style="Caption",
            theme_text_color="Custom",
            text_color=get_color_from_hex(accent_hex),
        )
        with icon_lbl.canvas.before:
            Color(*get_color_from_hex(accent_hex)[:3], 0.2)
            RoundedRectangle(
                pos=icon_lbl.pos,
                size=icon_lbl.size,
                radius=[6]
            )

        msg_lbl = MDLabel(
            text=message,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=get_color_from_hex(text_hex),
        )

        layout.add_widget(icon_lbl)
        layout.add_widget(msg_lbl)
        self.add_widget(layout)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._left_bar.pos = self.pos
        self._left_bar.size = (dp(5), self.height)


class NotificationManager:
    """Handles showing/hiding notification banners"""

    def __init__(self, parent_widget):
        self.parent = parent_widget
        self._active = []

    def show(self, message, notif_type='warning', duration=4):
        banner = NotificationBanner(message=message, notif_type=notif_type)

        # Position: just below top
        banner.y = Window.height + dp(80)
        banner.x = (Window.width - banner.width * Window.width) / 2

        self.parent.add_widget(banner)
        self._active.append(banner)

        # Slide in
        target_y = Window.height - dp(90)
        anim_in = Animation(y=target_y, duration=0.35, t='out_cubic')
        anim_in.start(banner)

        # Auto dismiss
        Clock.schedule_once(lambda dt: self._dismiss(banner), duration)

    def _dismiss(self, banner):
        if banner.parent:
            anim_out = Animation(
                y=Window.height + dp(80),
                duration=0.3,
                t='in_cubic'
            )
            anim_out.bind(on_complete=lambda *x: self._remove(banner))
            anim_out.start(banner)

    def _remove(self, banner):
        if banner in self._active:
            self._active.remove(banner)
        if banner.parent:
            banner.parent.remove_widget(banner)


KV = '''
<GlowCard>:
    canvas.before:
        Color:
            rgba: 0.07, 0.13, 0.25, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [24]
        Color:
            rgba: 0.12, 0.55, 0.95, 0.12
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [24]

<DashCard>:
    canvas.before:
        Color:
            rgba: 0.07, 0.13, 0.25, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [16]
'''
Builder.load_string(KV)


class GlowCard(MDCard):
    pass

class DashCard(MDCard):
    pass


# ==========================================
#  ANIMATED LOGO
# ==========================================
class AnimatedLogo(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(100), dp(100))
        self._angle = 0
        self._pulse = 0.0
        self._pulse_dir = 1
        Clock.schedule_interval(self._update, 1 / 30)

    def _update(self, dt):
        self._angle = (self._angle + 1.8) % 360
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._pulse_dir = 1
        self._draw()

    def _draw(self, *args):
        pulse = getattr(self, '_pulse', 0.0)
        self.canvas.clear()
        cx = self.center_x
        cy = self.center_y
        r = dp(45)
        with self.canvas:
            Color(0.12, 0.55, 0.95, 0.08 + pulse * 0.07)
            Ellipse(pos=(cx-r-dp(14), cy-r-dp(14)), size=(r*2+dp(28), r*2+dp(28)))
            Color(0.12, 0.55, 0.95, 0.13 + pulse * 0.05)
            Ellipse(pos=(cx-r-dp(7), cy-r-dp(7)), size=(r*2+dp(14), r*2+dp(14)))
            Color(0.05, 0.10, 0.22, 1)
            Ellipse(pos=(cx-r, cy-r), size=(r*2, r*2))
            Color(0.12, 0.55, 0.95, 1)
            Line(circle=(cx, cy, r), width=dp(2.5))
            Color(0.12, 0.55, 0.95, 0.25)
            Line(circle=(cx, cy, r-dp(7)), width=dp(1))
            Color(0.2, 0.65, 1.0, 1)
            Ellipse(pos=(cx-dp(10), cy-dp(6)), size=(dp(20), dp(22)))
            Color(0.4, 0.78, 1.0, 0.9)
            Ellipse(pos=(cx-dp(20), cy+dp(12)), size=(dp(9), dp(9)))
            Ellipse(pos=(cx+dp(11), cy+dp(13)), size=(dp(8), dp(8)))
            Color(0.5, 0.85, 1.0, 0.8)
            Ellipse(pos=(cx-dp(6), cy+dp(20)), size=(dp(11), dp(11)))
            angle = getattr(self, '_angle', 0)
            dot_x = cx + r * math.cos(math.radians(angle))
            dot_y = cy + r * math.sin(math.radians(angle))
            Color(0.5, 0.9, 1.0, 1)
            Ellipse(pos=(dot_x-dp(5), dot_y-dp(5)), size=(dp(10), dp(10)))
            dot2_x = cx + r * math.cos(math.radians(angle + 180))
            dot2_y = cy + r * math.sin(math.radians(angle + 180))
            Color(0.12, 0.55, 0.95, 0.6)
            Ellipse(pos=(dot2_x-dp(3), dot2_y-dp(3)), size=(dp(6), dp(6)))

    def on_size(self, *args): self._draw()
    def on_pos(self, *args): self._draw()


# ==========================================
#  LOGIN SCREEN
# ==========================================
class LoginScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = get_color_from_hex("#0A1628")
        self._build_ui()

    def _build_ui(self):
        self._mode = 'login'  # 'login' or 'register'
        root = MDFloatLayout(md_bg_color=get_color_from_hex("#0A1628"))
        self._card = GlowCard(
            size_hint=(0.88, None), height=dp(580),
            pos_hint={'center_x': 0.5, 'center_y': 0.50}, elevation=0,
        )
        self._card.opacity = 0
        self._layout = MDBoxLayout(
            orientation='vertical',
            padding=[dp(28), dp(22), dp(28), dp(22)],
            spacing=dp(10),
        )

        # Logo
        logo_row = MDBoxLayout(size_hint_y=None, height=dp(100))
        logo_row.add_widget(Widget())
        logo_row.add_widget(AnimatedLogo())
        logo_row.add_widget(Widget())
        self._layout.add_widget(logo_row)

        # App name
        self._layout.add_widget(MDLabel(
            text="AUTO FOGGER", halign='center', bold=True, font_style="H5",
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
            size_hint_y=None, height=dp(34),
        ))
        self._layout.add_widget(MDLabel(
            text="Smart Fogging Control System", halign='center', font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
            size_hint_y=None, height=dp(20),
        ))

        divider = Widget(size_hint_y=None, height=dp(12))
        with divider.canvas:
            Color(0.12, 0.55, 0.95, 0.2)
            Line(points=[dp(10), dp(6), dp(340), dp(6)], width=dp(1))
        self._layout.add_widget(divider)

        # Mode title
        self.mode_title = MDLabel(
            text="Sign In with Email", halign='left', bold=True, font_style="H6",
            theme_text_color="Custom", text_color=get_color_from_hex("#FFFFFF"),
            size_hint_y=None, height=dp(30),
        )
        self._layout.add_widget(self.mode_title)

        # Name field (fakt register la)
        self.name_field = MDTextField(
            hint_text="Full Name", icon_left="account-outline",
            size_hint_y=None, height=dp(50), mode="rectangle",
            line_color_normal=get_color_from_hex("#1E3A5F"),
            line_color_focus=get_color_from_hex("#1E88E5"),
            hint_text_color_normal=get_color_from_hex("#4A6FA5"),
            text_color_normal=get_color_from_hex("#E8F4FF"),
            fill_color_normal=get_color_from_hex("#0D1F3C"),
            opacity=0,
        )
        self._layout.add_widget(self.name_field)

        # Email field
        self.email_field = MDTextField(
            hint_text="Email", icon_left="email-outline",
            size_hint_y=None, height=dp(50), mode="rectangle",
            line_color_normal=get_color_from_hex("#1E3A5F"),
            line_color_focus=get_color_from_hex("#1E88E5"),
            hint_text_color_normal=get_color_from_hex("#4A6FA5"),
            text_color_normal=get_color_from_hex("#E8F4FF"),
            fill_color_normal=get_color_from_hex("#0D1F3C"),
        )
        self._layout.add_widget(self.email_field)

        # Password field
        self.password_field = MDTextField(
            hint_text="Password", icon_left="lock-outline", password=True,
            size_hint_y=None, height=dp(50), mode="rectangle",
            line_color_normal=get_color_from_hex("#1E3A5F"),
            line_color_focus=get_color_from_hex("#1E88E5"),
            hint_text_color_normal=get_color_from_hex("#4A6FA5"),
            text_color_normal=get_color_from_hex("#E8F4FF"),
            fill_color_normal=get_color_from_hex("#0D1F3C"),
        )
        self._layout.add_widget(self.password_field)

        # Message label
        self.msg_label = MDLabel(
            text="", halign='center', font_style="Caption",
            size_hint_y=None, height=dp(20),
            theme_text_color="Custom", text_color=get_color_from_hex("#FF5252"),
        )
        self._layout.add_widget(self.msg_label)

        # Main button (Login / Register)
        self.action_btn = MDRaisedButton(
            text="LOGIN", size_hint=(1, None), height=dp(50),
            md_bg_color=get_color_from_hex("#1565C0"), elevation=8,
            on_release=self._action,
        )
        self._layout.add_widget(self.action_btn)

        # Toggle button - Login <-> Register
        self.toggle_btn = MDFlatButton(
            text="New user? Register here",
            size_hint=(1, None), height=dp(36),
            theme_text_color="Custom",
            text_color=get_color_from_hex("#4A90D9"),
            on_release=self._toggle_mode,
        )
        self._layout.add_widget(self.toggle_btn)

        self._card.add_widget(self._layout)
        root.add_widget(self._card)
        root.add_widget(MDLabel(
            text="Auto Fogger  v1.0.0", halign='center', font_style="Overline",
            theme_text_color="Custom", text_color=get_color_from_hex("#1A2F4A"),
            size_hint=(1, None), height=dp(28),
            pos_hint={'center_x': 0.5, 'y': 0.008},
        ))
        self.add_widget(root)
        Clock.schedule_once(
            lambda dt: Animation(opacity=1, duration=0.7, t='out_cubic').start(self._card), 0.2
        )

    def _toggle_mode(self, instance):
        """Login <-> Register switch"""
        if self._mode == 'login':
            self._mode = 'register'
            self.mode_title.text = "Create Account"
            self.action_btn.text = "REGISTER"
            self.action_btn.md_bg_color = get_color_from_hex("#1B5E20")
            self.toggle_btn.text = "Already have account? Login"
            # Name field show kara
            self.name_field.opacity = 1
            self.name_field.height = dp(50)
            self._card.height = dp(640)
        else:
            self._mode = 'login'
            self.mode_title.text = "Sign In with Email"
            self.action_btn.text = "LOGIN"
            self.action_btn.md_bg_color = get_color_from_hex("#1565C0")
            self.toggle_btn.text = "New user? Register here"
            # Name field hide kara
            self.name_field.opacity = 0
            self.name_field.height = dp(0)
            self._card.height = dp(580)
            self.name_field.text = ""

    def _action(self, instance):
        if self._mode == 'login':
            self.login(instance)
        else:
            self.register(instance)

    def login(self, instance):
        email = self.email_field.text.strip()
        password = self.password_field.text.strip()
        if not email:
            self._show_msg("Please enter your email", error=True)
            return
        if "@" not in email:
            self._show_msg("Please enter valid email!", error=True)
            return
        if not password:
            self._show_msg("Please enter your password", error=True)
            return
        self.action_btn.text = "Verifying..."
        self.action_btn.disabled = True
        Clock.schedule_once(lambda dt: self._verify(email, password), 0.9)

    def register(self, instance):
        name = self.name_field.text.strip()
        email = self.email_field.text.strip()
        password = self.password_field.text.strip()
        if not name:
            self._show_msg("Please enter your name", error=True)
            return
        if not email or "@" not in email:
            self._show_msg("Please enter valid email!", error=True)
            return
        if not password or len(password) < 4:
            self._show_msg("Password must be 4+ characters!", error=True)
            return
        self._save_register(name, email, password)

    def _save_register(self, name, email, password):
        success = db.add_user(name, email, password, "user")
        if success:
            self._show_msg(f"Account created! Welcome {name}!", error=False)
            self.action_btn.text = "REGISTER"
            self.action_btn.disabled = False
            # Auto login
            Clock.schedule_once(lambda dt: self._verify(email, password), 0.1)
        else:
            self._show_msg("Email already registered!", error=True)
            self.action_btn.text = "REGISTER"
            self.action_btn.disabled = False

    def _verify(self, email, password):
        result = db.check_login(email, password)
        if result:
            name, role = result
            self._show_msg(f"Welcome {name}!", error=False)
            self.action_btn.text = "Welcome!"
            self.action_btn.md_bg_color = get_color_from_hex("#1B5E20")
            def go_dashboard(dt):
                dash = self.manager.get_screen('dashboard')
                dash.set_user(name, role)
                self.manager.current = 'dashboard'
            Clock.schedule_once(go_dashboard, 0.8)
        else:
            self._show_msg("Wrong email or password!", error=True)
            self.action_btn.text = "LOGIN"
            self.action_btn.disabled = False
            orig_x = self.action_btn.x
            shake = (
                Animation(x=orig_x+dp(10), duration=0.05) +
                Animation(x=orig_x-dp(10), duration=0.05) +
                Animation(x=orig_x+dp(7), duration=0.05) +
                Animation(x=orig_x-dp(7), duration=0.05) +
                Animation(x=orig_x, duration=0.05)
            )
            shake.start(self.action_btn)

    def _show_msg(self, msg, error=True):
        self.msg_label.text = msg
        self.msg_label.opacity = 1
        self.msg_label.text_color = get_color_from_hex(
            "#FF5252" if error else "#69F0AE"
        )
        if error:
            def fade(dt):
                anim = Animation(opacity=0, duration=2.0)
                anim.bind(on_complete=lambda *x: (
                    setattr(self.msg_label, 'text', ''),
                    setattr(self.msg_label, 'opacity', 1)
                ))
                anim.start(self.msg_label)
            Clock.schedule_once(fade, 2.0)


# ==========================================
#  DASHBOARD SCREEN
# ==========================================
class DashboardScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = get_color_from_hex("#0A1628")
        self._motor_on = False
        self._temp = 32.0
        self._humidity = 65.0
        self._motor_start_time = None
        self._last_alert_temp = 0
        self._notif_manager = None
        self._root_float = None
        self._current_user = "admin"
        self._current_role = "admin"
        self._manual_mode = False  # Manual ON asel tar True
        self._build_ui()
        Clock.schedule_interval(self._update_sensors, 5)

    def set_user(self, username, role):
        """Login nantarcha user set kara"""
        self._current_user = username
        self._current_role = role
        # Welcome label update
        role_badge = "ADMIN" if role == "admin" else "USER"
        self.welcome_label.text = f"Welcome, {username}!  [{role_badge}]"
        # User role - motor button disable kara
        if role == "user":
            self.motor_btn.disabled = True
            self.motor_btn.md_bg_color = get_color_from_hex("#37474F")
            self.motor_btn.text = "Only Admin Can Control"
        else:
            self.motor_btn.disabled = False
            self.motor_btn.text = "TURN ON"
            self.motor_btn.md_bg_color = get_color_from_hex("#1565C0")


    def _build_ui(self):
        # Root FloatLayout for notifications overlay
        self._root_float = MDFloatLayout(
            md_bg_color=get_color_from_hex("#0A1628")
        )
        self._notif_manager = NotificationManager(self._root_float)

        main = MDBoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(12),
            size_hint=(1, 1),
        )

        # Top bar
        topbar = MDBoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        topbar.add_widget(MDLabel(
            text="Auto Fogger", font_style="H6", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
        ))
        topbar.add_widget(MDRaisedButton(
            text="Logout", size_hint=(None, None), size=(dp(90), dp(38)),
            md_bg_color=get_color_from_hex("#B71C1C"), elevation=4,
            on_release=self._logout,
        ))

        # Welcome
        welcome_card = DashCard(size_hint_y=None, height=dp(56), elevation=0)
        wl = MDBoxLayout(padding=[dp(16), dp(8), dp(16), dp(8)])
        self.welcome_label = MDLabel(
            text="Welcome, Admin!  [ADMIN]", font_style="Subtitle1", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
        )
        wl.add_widget(self.welcome_label)
        welcome_card.add_widget(wl)

        # Sensor row
        sensor_row = MDBoxLayout(size_hint_y=None, height=dp(100), spacing=dp(12))

        temp_card = DashCard(elevation=0)
        tl = MDBoxLayout(orientation='vertical', padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(4))
        tl.add_widget(MDLabel(
            text="Temperature", font_style="Caption", halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
        ))
        self.temp_label = MDLabel(
            text="32.0 C", font_style="H5", bold=True, halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#FF7043"),
        )
        tl.add_widget(self.temp_label)
        temp_card.add_widget(tl)

        hum_card = DashCard(elevation=0)
        hl = MDBoxLayout(orientation='vertical', padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(4))
        hl.add_widget(MDLabel(
            text="Humidity", font_style="Caption", halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
        ))
        self.hum_label = MDLabel(
            text="65.0 %", font_style="H5", bold=True, halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#29B6F6"),
        )
        hl.add_widget(self.hum_label)
        hum_card.add_widget(hl)

        sensor_row.add_widget(temp_card)
        sensor_row.add_widget(hum_card)

        # Motor card
        motor_card = DashCard(size_hint_y=None, height=dp(220), elevation=0)
        ml = MDBoxLayout(
            orientation='vertical',
            padding=[dp(20), dp(18), dp(20), dp(18)],
            spacing=dp(14),
        )
        ml.add_widget(MDLabel(
            text="Motor Control", font_style="H6", bold=True, halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
            size_hint_y=None, height=dp(32),
        ))
        self.motor_status_label = MDLabel(
            text="MOTOR OFF", font_style="H5", bold=True, halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#546E7A"),
            size_hint_y=None, height=dp(40),
        )
        self.motor_reason = MDLabel(
            text="Press button to start fogging", font_style="Caption", halign='center',
            theme_text_color="Custom", text_color=get_color_from_hex("#3D6A9E"),
            size_hint_y=None, height=dp(22),
        )
        self.motor_btn = MDRaisedButton(
            text="TURN ON", size_hint=(1, None), height=dp(50),
            md_bg_color=get_color_from_hex("#1565C0"), elevation=6,
            on_release=self._toggle_motor,
        )
        ml.add_widget(self.motor_status_label)
        ml.add_widget(self.motor_reason)
        ml.add_widget(self.motor_btn)
        motor_card.add_widget(ml)

        self.db_count_label = MDLabel(
            text=f"Total Records: {db.get_count()}",
            halign='center', font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#3D6A9E"),
            size_hint_y=None, height=dp(20),
        )

        history_btn = MDRaisedButton(
            text="VIEW HISTORY", size_hint=(1, None), height=dp(50),
            md_bg_color=get_color_from_hex("#0D47A1"), elevation=4,
            on_release=self._go_history,
        )

        main.add_widget(topbar)
        main.add_widget(welcome_card)
        main.add_widget(sensor_row)
        main.add_widget(motor_card)
        main.add_widget(self.db_count_label)
        main.add_widget(history_btn)
        main.add_widget(Widget())

        self._root_float.add_widget(main)
        self.add_widget(self._root_float)

    def _update_sensors(self, dt):
        import random
        self._temp = round(28 + random.uniform(0, 16), 1)
        self._humidity = round(55 + random.uniform(0, 20), 1)
        self.temp_label.text = f"{self._temp} C"
        self.hum_label.text = f"{self._humidity} %"

        # ✅ Manual ON asel tar temperature kahi karnar nahi
        if self._manual_mode:
            return

        if self._temp >= 40.0:
            # Auto: Temperature 40C+ - Motor AUTO ON
            if self._last_alert_temp != 40:
                self._last_alert_temp = 40
                if not self._motor_on:
                    self._auto_start()
                self._notif_manager.show(
                    f"Temperature {self._temp} C Hot - Motor Chalu Zali!",
                    notif_type='warning',
                    duration=5
                )
        else:
            # Auto: Temperature 40C khali - Motor AUTO OFF
            if self._last_alert_temp == 40:
                self._last_alert_temp = 0
                if self._motor_on:
                    self._auto_stop()
                    self._notif_manager.show(
                        f"Temperature Normal {self._temp} C - Motor Band Zali!",
                        notif_type='success',
                        duration=5
                    )

    def _auto_start(self):
        self._manual_mode = False  # Auto mode
        self._motor_on = True
        self._motor_start_time = datetime.now()
        self._update_motor_ui()
        db.save_event(
            status="ON", temperature=self._temp, humidity=self._humidity,
            duration="-", reason=f"Auto ON - Temperature {self._temp} C Hot"
        )
        self._refresh_count()

    def _auto_stop(self):
        duration_str = "-"
        if self._motor_start_time:
            diff = datetime.now() - self._motor_start_time
            minutes = int(diff.total_seconds() // 60)
            seconds = int(diff.total_seconds() % 60)
            duration_str = f"{minutes}m {seconds}s"
        self._motor_on = False
        self._update_motor_ui()
        self._motor_start_time = None
        db.save_event(
            status="OFF", temperature=self._temp, humidity=self._humidity,
            duration=duration_str, reason=f"Auto OFF - Temperature {self._temp} C Normal"
        )
        self._refresh_count()

    def _toggle_motor(self, instance):
        self._motor_on = not self._motor_on
        if self._motor_on:
            # ✅ Manual ON - mode set kara, temperature touch nahi
            self._manual_mode = True
            self._motor_start_time = datetime.now()
            self._update_motor_ui()
            db.save_event(
                status="ON", temperature=self._temp, humidity=self._humidity,
                duration="-", reason="Manual Start"
            )
            self._notif_manager.show(
                "Motor Manual Chalu Zali!", notif_type='success', duration=3
            )
        else:
            # ✅ Manual OFF - mode reset kara
            self._manual_mode = False
            self._last_alert_temp = 0  # Alert reset
            duration_str = "-"
            if self._motor_start_time:
                diff = datetime.now() - self._motor_start_time
                minutes = int(diff.total_seconds() // 60)
                seconds = int(diff.total_seconds() % 60)
                duration_str = f"{minutes}m {seconds}s"
            self._update_motor_ui()
            db.save_event(
                status="OFF", temperature=self._temp, humidity=self._humidity,
                duration=duration_str, reason="Manual Stop"
            )
            self._notif_manager.show(
                f"Motor Manual Band Zali! | Duration: {duration_str}",
                notif_type='info', duration=3
            )
            self._motor_start_time = None
        self._refresh_count()

    def _refresh_count(self):
        self.db_count_label.text = f"Total Records: {db.get_count()}"

    def _update_motor_ui(self):
        if self._motor_on:
            self.motor_status_label.text = "MOTOR ON"
            self.motor_status_label.text_color = get_color_from_hex("#69F0AE")
            self.motor_reason.text = "Fogging in progress..."
            self.motor_reason.text_color = get_color_from_hex("#69F0AE")
            self.motor_btn.text = "TURN OFF"
            self.motor_btn.md_bg_color = get_color_from_hex("#B71C1C")
        else:
            self.motor_status_label.text = "MOTOR OFF"
            self.motor_status_label.text_color = get_color_from_hex("#546E7A")
            self.motor_reason.text = "Press button to start fogging"
            self.motor_reason.text_color = get_color_from_hex("#3D6A9E")
            self.motor_btn.text = "TURN ON"
            self.motor_btn.md_bg_color = get_color_from_hex("#1565C0")

    def _go_history(self, instance):
        self.manager.get_screen('history').load_history()
        self.manager.current = 'history'

    def _logout(self, instance):
        self.manager.current = 'login'

    def on_enter(self):
        self._refresh_count()


# ==========================================
#  HISTORY SCREEN
# ==========================================
class HistoryScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = get_color_from_hex("#0A1628")
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.scrollview import MDScrollView

        self.root_layout = MDBoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(12),
        )

        topbar = MDBoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        topbar.add_widget(MDRaisedButton(
            text="Back", size_hint=(None, None), size=(dp(80), dp(38)),
            md_bg_color=get_color_from_hex("#1565C0"), elevation=4,
            on_release=lambda x: setattr(self.manager, 'current', 'dashboard'),
        ))
        topbar.add_widget(MDLabel(
            text="History", font_style="H6", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
        ))
        topbar.add_widget(MDRaisedButton(
            text="Clear All", size_hint=(None, None), size=(dp(90), dp(38)),
            md_bg_color=get_color_from_hex("#B71C1C"), elevation=4,
            on_release=self._clear_history,
        ))

        self.count_label = MDLabel(
            text=f"Total Records: {db.get_count()}",
            halign='center', font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
            size_hint_y=None, height=dp(24),
        )

        self.scroll = MDScrollView()
        self.scroll_layout = MDBoxLayout(
            orientation='vertical', spacing=dp(10),
            size_hint_y=None, padding=[0, dp(4), 0, dp(4)],
        )
        self.scroll_layout.bind(minimum_height=self.scroll_layout.setter('height'))
        self.scroll.add_widget(self.scroll_layout)

        self.root_layout.add_widget(topbar)
        self.root_layout.add_widget(self.count_label)
        self.root_layout.add_widget(self.scroll)
        self.add_widget(self.root_layout)
        self.load_history()

    def load_history(self):
        self.scroll_layout.clear_widgets()
        rows = db.get_all_events()
        self.count_label.text = f"Total Records: {len(rows)}"

        if not rows:
            self.scroll_layout.add_widget(MDLabel(
                text="No history yet!\nStart using the motor to see records here.",
                halign='center', font_style="Body1",
                theme_text_color="Custom", text_color=get_color_from_hex("#3D6A9E"),
                size_hint_y=None, height=dp(100),
            ))
            return

        for row in rows:
            row_id, status, temp, humidity, duration, reason, date, time_str = row
            self._add_card(status, temp, humidity, duration, reason, date, time_str)

    def _add_card(self, status, temp, humidity, duration, reason, date, time_str):
        is_on = status == 'ON'
        status_color = "#69F0AE" if is_on else "#FF7043"

        card = DashCard(size_hint_y=None, height=dp(130), elevation=0)
        cl = MDBoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(10), dp(16), dp(10)],
            spacing=dp(6),
        )

        row1 = MDBoxLayout(size_hint_y=None, height=dp(26))
        row1.add_widget(MDLabel(
            text=f"Motor {status}", font_style="Subtitle1", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex(status_color),
        ))
        row1.add_widget(MDLabel(
            text=date, font_style="Caption", halign='right',
            theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
        ))

        row2 = MDBoxLayout(size_hint_y=None, height=dp(22))
        row2.add_widget(MDLabel(
            text=f"Time: {time_str}", font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#B0BEC5"),
        ))
        row2.add_widget(MDLabel(
            text=f"Duration: {duration}", font_style="Caption", halign='right',
            theme_text_color="Custom", text_color=get_color_from_hex("#B0BEC5"),
        ))

        cl.add_widget(row1)
        cl.add_widget(row2)
        cl.add_widget(MDLabel(
            text=f"Reason: {reason}", font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
            size_hint_y=None, height=dp(22),
        ))
        cl.add_widget(MDLabel(
            text=f"Temp: {temp} C   Humidity: {humidity} %",
            font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#FF7043"),
            size_hint_y=None, height=dp(20),
        ))

        card.add_widget(cl)
        self.scroll_layout.add_widget(card)

    def _clear_history(self, instance):
        db.delete_all()
        self.load_history()

    def on_enter(self):
        self.load_history()




# ==========================================
#  USERS MANAGEMENT SCREEN
# ==========================================
class UsersScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = get_color_from_hex("#0A1628")
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.scrollview import MDScrollView

        self.root_layout = MDBoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(12),
        )

        # Top bar
        topbar = MDBoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        topbar.add_widget(MDRaisedButton(
            text="Back", size_hint=(None, None), size=(dp(80), dp(38)),
            md_bg_color=get_color_from_hex("#1565C0"), elevation=4,
            on_release=lambda x: setattr(self.manager, 'current', 'dashboard'),
        ))
        topbar.add_widget(MDLabel(
            text="Manage Users", font_style="H6", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
        ))

        # Add user card
        add_card = DashCard(size_hint_y=None, height=dp(260), elevation=0)
        add_layout = MDBoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(10),
        )
        add_layout.add_widget(MDLabel(
            text="Add New User", font_style="Subtitle1", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
            size_hint_y=None, height=dp(28),
        ))
        self.new_name = MDTextField(
            hint_text="Full Name", size_hint_y=None, height=dp(46), mode="rectangle",
            line_color_normal=get_color_from_hex("#1E3A5F"),
            line_color_focus=get_color_from_hex("#1E88E5"),
            hint_text_color_normal=get_color_from_hex("#4A6FA5"),
            text_color_normal=get_color_from_hex("#E8F4FF"),
            fill_color_normal=get_color_from_hex("#0D1F3C"),
        )
        self.new_email = MDTextField(
            hint_text="Email", size_hint_y=None, height=dp(46), mode="rectangle",
            line_color_normal=get_color_from_hex("#1E3A5F"),
            line_color_focus=get_color_from_hex("#1E88E5"),
            hint_text_color_normal=get_color_from_hex("#4A6FA5"),
            text_color_normal=get_color_from_hex("#E8F4FF"),
            fill_color_normal=get_color_from_hex("#0D1F3C"),
        )
        self.new_password = MDTextField(
            hint_text="Password", password=True,
            size_hint_y=None, height=dp(46), mode="rectangle",
            line_color_normal=get_color_from_hex("#1E3A5F"),
            line_color_focus=get_color_from_hex("#1E88E5"),
            hint_text_color_normal=get_color_from_hex("#4A6FA5"),
            text_color_normal=get_color_from_hex("#E8F4FF"),
            fill_color_normal=get_color_from_hex("#0D1F3C"),
        )

        # Role buttons row
        role_row = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self._selected_role = "user"

        self.admin_btn = MDRaisedButton(
            text="Admin", size_hint=(1, None), height=dp(38),
            md_bg_color=get_color_from_hex("#37474F"),
            on_release=lambda x: self._select_role("admin"),
        )
        self.user_btn = MDRaisedButton(
            text="User", size_hint=(1, None), height=dp(38),
            md_bg_color=get_color_from_hex("#1565C0"),
            on_release=lambda x: self._select_role("user"),
        )
        role_row.add_widget(self.admin_btn)
        role_row.add_widget(self.user_btn)

        self.add_msg = MDLabel(
            text="", halign='center', font_style="Caption",
            theme_text_color="Custom", text_color=get_color_from_hex("#69F0AE"),
            size_hint_y=None, height=dp(20),
        )

        add_btn = MDRaisedButton(
            text="ADD USER", size_hint=(1, None), height=dp(44),
            md_bg_color=get_color_from_hex("#1B5E20"), elevation=4,
            on_release=self._add_user,
        )

        add_layout.add_widget(self.new_name)
        add_layout.add_widget(self.new_email)
        add_layout.add_widget(self.new_password)
        add_layout.add_widget(role_row)
        add_layout.add_widget(self.add_msg)
        add_layout.add_widget(add_btn)
        add_card.add_widget(add_layout)

        # Users list
        self.count_label = MDLabel(
            text="Users List:", font_style="Subtitle1", bold=True,
            theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
            size_hint_y=None, height=dp(28),
        )

        self.scroll = MDScrollView()
        self.scroll_layout = MDBoxLayout(
            orientation='vertical', spacing=dp(8),
            size_hint_y=None, padding=[0, dp(4), 0, dp(4)],
        )
        self.scroll_layout.bind(minimum_height=self.scroll_layout.setter('height'))
        self.scroll.add_widget(self.scroll_layout)

        self.root_layout.add_widget(topbar)
        self.root_layout.add_widget(add_card)
        self.root_layout.add_widget(self.count_label)
        self.root_layout.add_widget(self.scroll)
        self.add_widget(self.root_layout)
        self._load_users()

    def _select_role(self, role):
        self._selected_role = role
        if role == "admin":
            self.admin_btn.md_bg_color = get_color_from_hex("#1565C0")
            self.user_btn.md_bg_color = get_color_from_hex("#37474F")
        else:
            self.user_btn.md_bg_color = get_color_from_hex("#1565C0")
            self.admin_btn.md_bg_color = get_color_from_hex("#37474F")

    def _add_user(self, instance):
        name = self.new_name.text.strip()
        email = self.new_email.text.strip()
        password = self.new_password.text.strip()

        if not name or not email or not password:
            self.add_msg.text = "Please fill all fields!"
            self.add_msg.text_color = get_color_from_hex("#FF5252")
            return

        if "@" not in email:
            self.add_msg.text = "Please enter valid email!"
            self.add_msg.text_color = get_color_from_hex("#FF5252")
            return

        if len(password) < 4:
            self.add_msg.text = "Password must be 4+ characters!"
            self.add_msg.text_color = get_color_from_hex("#FF5252")
            return

        success = db.add_user(name, email, password, self._selected_role)
        if success:
            self.add_msg.text = f"{name} added successfully!"
            self.add_msg.text_color = get_color_from_hex("#69F0AE")
            self.new_name.text = ""
            self.new_email.text = ""
            self.new_password.text = ""
            self._load_users()
        else:
            self.add_msg.text = "Email already exists!"
            self.add_msg.text_color = get_color_from_hex("#FF5252")

    def _load_users(self):
        self.scroll_layout.clear_widgets()
        users = db.get_all_users()
        self.count_label.text = f"Users List: ({len(users)} users)"

        for user_id, name, email, role in users:
            card = DashCard(size_hint_y=None, height=dp(78), elevation=0)
            row = MDBoxLayout(
                padding=[dp(16), dp(8), dp(16), dp(8)],
                spacing=dp(8),
            )

            is_admin = role == "admin"
            role_color = "#FF7043" if is_admin else "#29B6F6"
            role_text = "ADMIN" if is_admin else "USER"

            # Name + email + role
            info_col = MDBoxLayout(orientation='vertical', spacing=dp(2))
            info_col.add_widget(MDLabel(
                text=name, font_style="Subtitle1", bold=True,
                theme_text_color="Custom", text_color=get_color_from_hex("#E8F4FF"),
                size_hint_y=None, height=dp(20),
            ))
            info_col.add_widget(MDLabel(
                text=email, font_style="Caption",
                theme_text_color="Custom", text_color=get_color_from_hex("#4A90D9"),
                size_hint_y=None, height=dp(16),
            ))
            info_col.add_widget(MDLabel(
                text=role_text, font_style="Caption",
                theme_text_color="Custom", text_color=get_color_from_hex(role_color),
                size_hint_y=None, height=dp(16),
            ))

            row.add_widget(info_col)

            # Delete button - admin delete nahi hota
            if email != 'admin@fogger.com':
                del_btn = MDRaisedButton(
                    text="Delete", size_hint=(None, None), size=(dp(75), dp(34)),
                    md_bg_color=get_color_from_hex("#B71C1C"), elevation=2,
                )
                del_btn.bind(on_release=lambda x, e=email: self._delete_user(e))
                row.add_widget(del_btn)
            else:
                row.add_widget(MDLabel(
                    text="Protected", font_style="Caption", halign='right',
                    theme_text_color="Custom", text_color=get_color_from_hex("#546E7A"),
                    size_hint=(None, None), size=(dp(75), dp(34)),
                ))

            card.add_widget(row)
            self.scroll_layout.add_widget(card)

    def _delete_user(self, username):
        db.delete_user(username)
        self._load_users()

    def on_enter(self):
        self._load_users()

# ==========================================
#  MAIN APP
# ==========================================
class AutoFoggerApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.primary_hue = "700"
        self.theme_cls.theme_style = "Dark"
        self.title = "Auto Fogger"
        sm = MDScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        sm.add_widget(HistoryScreen(name='history'))
        sm.add_widget(UsersScreen(name='users'))
        return sm


if __name__ == "__main__":
    AutoFoggerApp().run()
