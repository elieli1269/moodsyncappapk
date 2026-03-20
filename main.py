#!/usr/bin/env python3
"""
MoodSync Mobile v2 — WebView + FCM + polling + login auto
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
import os, json, threading, time

HOME_URL    = "https://moodsync.alwaysdata.net"
LOGIN_URL   = "https://moodsync.alwaysdata.net/login.php"
CHAT_URL    = HOME_URL + "/chat.php"
NOTIF_URL   = HOME_URL + "/notifications.php"
PROFILE_URL = HOME_URL + "/profile.php"
API_MSGS    = HOME_URL + "/api/messages_count.php"
API_NOTIFS  = HOME_URL + "/api/notifications_count.php"
API_FCM_REG = HOME_URL + "/api/fcm_register.php"

MS_BG      = (0.086, 0.086, 0.102, 1)
MS_NAVBAR  = (0.065, 0.065, 0.085, 1)
MS_TOOL    = (0.090, 0.090, 0.118, 1)
MS_ACCENT  = (0.486, 0.361, 0.988, 1)
MS_ACCENT2 = (0.655, 0.545, 0.988, 1)
MS_TEXT    = (0.910, 0.902, 0.941, 1)
MS_DIM     = (0.533, 0.502, 0.627, 1)
MS_GREEN   = (0.506, 0.788, 0.584, 1)
MS_RED     = (0.949, 0.545, 0.510, 1)
MS_BADGE   = (0.949, 0.333, 0.333, 1)

DATA_DIR     = os.path.join(os.path.expanduser("~"), ".moodsync")
os.makedirs(DATA_DIR, exist_ok=True)
ACCOUNT_FILE = os.path.join(DATA_DIR, "account.json")

def load_account():
    try:
        if os.path.exists(ACCOUNT_FILE):
            return json.loads(open(ACCOUNT_FILE).read())
    except: pass
    return {}

def save_account(username, fcm_token=""):
    d = load_account()
    d["username"] = username
    if fcm_token: d["fcm_token"] = fcm_token
    open(ACCOUNT_FILE, 'w').write(json.dumps(d))

def save_fcm_token(token):
    d = load_account()
    d["fcm_token"] = token
    open(ACCOUNT_FILE, 'w').write(json.dumps(d))

def clear_account():
    try: os.remove(ACCOUNT_FILE)
    except: pass

def is_logged_in():
    return bool(load_account().get("username"))

def get_username():
    return load_account().get("username", "")

def get_fcm_token():
    return load_account().get("fcm_token", "")

# ── Android platform ──────────────────────────────────────────────────────────

if platform == "android":
    try:
        from android.runnable import run_on_ui_thread
        from jnius import autoclass, PythonJavaClass, java_method

        PythonActivity  = autoclass("org.kivy.android.PythonActivity")
        WebView         = autoclass("android.webkit.WebView")
        WebViewClient   = autoclass("android.webkit.WebViewClient")
        WebChromeClient = autoclass("android.webkit.WebChromeClient")
        CookieManager   = autoclass("android.webkit.CookieManager")
        LayoutParams    = autoclass("android.view.ViewGroup$LayoutParams")
        Color_java      = autoclass("android.graphics.Color")
        NotifManager    = autoclass("android.app.NotificationManager")
        NotifCompat     = autoclass("androidx.core.app.NotificationCompat")
        NotifChannel    = autoclass("android.app.NotificationChannel")
        PendingIntent   = autoclass("android.app.PendingIntent")
        Intent          = autoclass("android.content.Intent")
        Context         = autoclass("android.content.Context")
        Build           = autoclass("android.os.Build")
        FirebaseMsg     = autoclass("com.google.firebase.messaging.FirebaseMessaging")

        CHANNEL_ID = "moodsync_channel"

        def create_notif_channel():
            try:
                act = PythonActivity.mActivity
                if Build.VERSION.SDK_INT >= 26:
                    ch = NotifChannel(
                        CHANNEL_ID, "MoodSync",
                        NotifManager.IMPORTANCE_HIGH)
                    ch.enableVibration(True)
                    nm = act.getSystemService(Context.NOTIFICATION_SERVICE)
                    nm = autoclass("android.app.NotificationManager").cast(nm) \
                        if hasattr(autoclass("android.app.NotificationManager"), 'cast') \
                        else nm
                    try:
                        from jnius import cast as jcast
                        nm2 = jcast("android.app.NotificationManager", nm)
                        nm2.createNotificationChannel(ch)
                    except:
                        pass
            except Exception as e:
                print("Channel error:", e)

        def send_notif(title, body, nid=100):
            try:
                act = PythonActivity.mActivity
                intent = Intent(act, PythonActivity)
                intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
                flags = PendingIntent.FLAG_UPDATE_CURRENT
                if Build.VERSION.SDK_INT >= 23:
                    flags |= PendingIntent.FLAG_IMMUTABLE
                pi = PendingIntent.getActivity(act, nid, intent, flags)
                b = NotifCompat.Builder(act, CHANNEL_ID)
                b.setSmallIcon(act.getApplicationInfo().icon)
                b.setContentTitle(title)
                b.setContentText(body)
                b.setAutoCancel(True)
                b.setPriority(NotifCompat.PRIORITY_HIGH)
                b.setContentIntent(pi)
                try:
                    from jnius import cast as jcast
                    nm = jcast("android.app.NotificationManager",
                               act.getSystemService(Context.NOTIFICATION_SERVICE))
                    nm.notify(nid, b.build())
                except:
                    pass
            except Exception as e:
                print("Notif error:", e)

        def get_fcm_token_android(cb):
            try:
                class Listener(PythonJavaClass):
                    __javainterfaces__ = [
                        'com/google/android/gms/tasks/OnSuccessListener']
                    __javacontext__ = 'app'

                    @java_method('(Ljava/lang/Object;)V')
                    def onSuccess(self, result):
                        Clock.schedule_once(
                            lambda dt: cb(str(result)), 0)

                FirebaseMsg.getInstance().getToken().addOnSuccessListener(
                    Listener())
            except Exception as e:
                print("FCM token error:", e)
                cb("")

        class MSWebViewClient(WebViewClient):
            def __init__(self, w):
                super().__init__()
                self._w = w

            def onPageStarted(self, wv, url, fav):
                self._w.current_url = url or ""
                if self._w.on_url:
                    Clock.schedule_once(
                        lambda dt, u=url: self._w.on_url(u or ""), 0)

            def onPageFinished(self, wv, url):
                self._w.current_url = url or ""
                self._w.can_back = wv.canGoBack()
                self._w.can_fwd  = wv.canGoForward()
                t = wv.getTitle()
                if t and self._w.on_title:
                    Clock.schedule_once(
                        lambda dt, _t=str(t): self._w.on_title(_t), 0)
                # Détecter user connecté
                wv.evaluateJavascript(
                    "(function(){"
                    "var m=document.querySelector('meta[name=\"username\"]');"
                    "if(m&&m.content){document.title='__USER__:'+m.content;return;}"
                    "var d=document.querySelector('[data-username]');"
                    "if(d){document.title='__USER__:'+d.getAttribute('data-username');}"
                    "})()", None)

            def shouldOverrideUrlLoading(self, wv, url):
                return False

        class AndroidWebView(Widget):
            current_url = StringProperty("")
            can_back    = BooleanProperty(False)
            can_fwd     = BooleanProperty(False)
            on_title    = None
            on_url      = None

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._wv = None
                Clock.schedule_once(self._create, 0)
                self.bind(pos=self._update, size=self._update)

            @run_on_ui_thread
            def _create(self, *a):
                act = PythonActivity.mActivity
                cm  = CookieManager.getInstance()
                cm.setAcceptCookie(True)

                self._wv = WebView(act)
                s = self._wv.getSettings()
                s.setJavaScriptEnabled(True)
                s.setDomStorageEnabled(True)
                s.setLoadWithOverviewMode(True)
                s.setUseWideViewPort(True)
                s.setBuiltInZoomControls(False)
                s.setDisplayZoomControls(False)
                s.setMediaPlaybackRequiresUserGesture(False)
                s.setMixedContentMode(0)
                s.setAllowFileAccess(True)
                ua = s.getUserAgentString()
                s.setUserAgentString(ua + " MoodSyncApp/1.0")

                self._wv.setWebViewClient(MSWebViewClient(self))
                self._wv.setWebChromeClient(WebChromeClient())
                self._wv.setBackgroundColor(Color_java.parseColor("#161619"))

                act.addContentView(self._wv, LayoutParams(
                    LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))

                start_url = HOME_URL if is_logged_in() else LOGIN_URL
                self._wv.loadUrl(start_url)
                Clock.schedule_once(self._update, 0.2)

            @run_on_ui_thread
            def _update(self, *a):
                if not self._wv: return
                from kivy.core.window import Window as W
                self._wv.setX(int(self.x))
                self._wv.setY(int(W.height - self.y - self.height))
                lp = self._wv.getLayoutParams()
                lp.width  = int(self.width)
                lp.height = int(self.height)
                self._wv.setLayoutParams(lp)
                self._wv.requestLayout()

            @run_on_ui_thread
            def load(self, url):
                if self._wv: self._wv.loadUrl(url)

            @run_on_ui_thread
            def run_js(self, js):
                if self._wv:
                    self._wv.evaluateJavascript(js, None)

            @run_on_ui_thread
            def back(self):
                if self._wv and self._wv.canGoBack():
                    self._wv.goBack()

            @run_on_ui_thread
            def reload(self):
                if self._wv: self._wv.reload()

            @run_on_ui_thread
            def clear_cookies(self):
                cm = CookieManager.getInstance()
                cm.removeAllCookies(None)
                cm.flush()

        ANDROID_OK = True

    except Exception as e:
        print("Android init error:", e)
        ANDROID_OK = False

        def create_notif_channel(): pass
        def send_notif(t, b, nid=100): pass
        def get_fcm_token_android(cb): Clock.schedule_once(lambda dt: cb(""), 0.1)

        class AndroidWebView(Widget):
            current_url = StringProperty("")
            can_back    = BooleanProperty(False)
            can_fwd     = BooleanProperty(False)
            on_title    = None
            on_url      = None
            def load(self, url): pass
            def run_js(self, js): pass
            def back(self): pass
            def reload(self): pass
            def clear_cookies(self): pass

else:
    ANDROID_OK = False
    def create_notif_channel(): pass
    def send_notif(t, b, nid=100): print(f"NOTIF: {t} — {b}")
    def get_fcm_token_android(cb): Clock.schedule_once(lambda dt: cb(""), 0.1)

    class AndroidWebView(Widget):
        current_url = StringProperty("")
        can_back    = BooleanProperty(False)
        can_fwd     = BooleanProperty(False)
        on_title    = None
        on_url      = None
        def load(self, url): pass
        def run_js(self, js): pass
        def back(self): pass
        def reload(self): pass
        def clear_cookies(self): pass

# ── Badge ─────────────────────────────────────────────────────────────────────

class Badge(Widget):
    count = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(16), dp(16))
        self.bind(count=self._draw, pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        if self.count <= 0:
            return
        with self.canvas:
            Color(*MS_BADGE)
            Ellipse(pos=self.pos, size=self.size)
        n = str(min(self.count, 99))
        lbl = Label(text=n, font_size=sp(8), color=(1,1,1,1),
                    size=self.size, pos=self.pos,
                    halign='center', valign='middle')
        lbl.texture_update()
        if lbl.texture:
            with self.canvas:
                Color(1,1,1,1)
                Rectangle(
                    texture=lbl.texture,
                    pos=(self.x + (self.width  - lbl.texture.width)  / 2,
                         self.y + (self.height - lbl.texture.height) / 2),
                    size=lbl.texture.size)

# ── NavItem ───────────────────────────────────────────────────────────────────

class NavItem(FloatLayout):
    def __init__(self, icon_text, label_text, callback,
                 has_badge=False, **kwargs):
        super().__init__(**kwargs)
        self._cb = callback

        inner = BoxLayout(
            orientation='vertical',
            padding=[0, dp(5), 0, dp(3)],
            spacing=dp(2),
            size_hint=(1, 1),
        )
        self._icon = Label(
            text=icon_text, font_size=sp(20),
            color=MS_DIM,
            size_hint_y=None, height=dp(26),
            halign='center',
        )
        self._lbl = Label(
            text=label_text, font_size=sp(10),
            color=MS_DIM,
            size_hint_y=None, height=dp(14),
            halign='center',
        )
        inner.add_widget(self._icon)
        inner.add_widget(self._lbl)
        self.add_widget(inner)

        if has_badge:
            self.badge = Badge()
            self.badge.pos_hint = {'center_x': 0.65, 'center_y': 0.72}
            self.add_widget(self.badge)
        else:
            self.badge = None

    def set_active(self, v):
        c = MS_ACCENT2 if v else MS_DIM
        self._icon.color = c
        self._lbl.color  = c

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self._cb: self._cb()
            return True
        return super().on_touch_up(touch)

# ── Bottom Nav ────────────────────────────────────────────────────────────────

class BottomNav(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)
        self.app     = app
        self.size_hint_y = None
        self.height  = dp(60)
        self._items  = {}
        self._active = 'home'
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*MS_NAVBAR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos =lambda *a: setattr(self._bg, 'pos',  self.pos),
            size=lambda *a: setattr(self._bg, 'size', self.size),
        )
        tabs = [
            ('home',    'Accueil',  HOME_URL,    False),
            ('chat',    'Messages', CHAT_URL,    True),
            ('notifs',  'Notifs',   NOTIF_URL,   True),
            ('profile', 'Profil',   PROFILE_URL, False),
        ]
        icons = {
            'home':    'o',
            'chat':    'M',
            'notifs':  'N',
            'profile': 'P',
        }
        for key, label, url, badge in tabs:
            item = NavItem(
                icons[key], label,
                callback=lambda k=key, u=url: self._tap(k, u),
                has_badge=badge,
                size_hint=(1, 1),
            )
            if key == self._active:
                item.set_active(True)
            self._items[key] = item
            self.add_widget(item)

    def _tap(self, key, url):
        self._active = key
        for k, item in self._items.items():
            item.set_active(k == key)
        if not is_logged_in():
            self.app.webview.load(LOGIN_URL)
        else:
            self.app.webview.load(url)
        if key in ('chat', 'notifs'):
            self.set_badge(key, 0)

    def set_active_by_url(self, url):
        key = None
        if '/chat' in url:         key = 'chat'
        elif '/notification' in url: key = 'notifs'
        elif '/profile' in url:    key = 'profile'
        elif url.rstrip('/') == HOME_URL.rstrip('/'): key = 'home'
        if key:
            self._active = key
            for k, item in self._items.items():
                item.set_active(k == key)

    def set_badge(self, key, n):
        item = self._items.get(key)
        if item and item.badge:
            item.badge.count = n

# ── Toolbar ───────────────────────────────────────────────────────────────────

class Toolbar(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)
        self.app = app
        self.size_hint_y = None
        self.height = dp(54)
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*MS_TOOL)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos =lambda *a: setattr(self._bg, 'pos',  self.pos),
            size=lambda *a: setattr(self._bg, 'size', self.size),
        )
        inner = BoxLayout(
            padding=[dp(10), dp(8), dp(10), dp(8)],
            spacing=dp(8),
        )
        self.btn_back = Button(
            text='<', font_size=sp(20), bold=True,
            size_hint=(None, None), size=(dp(40), dp(38)),
            background_normal='', background_color=(0,0,0,0),
            color=MS_DIM,
        )
        self.btn_back.bind(on_press=lambda *a: self.app.go_back())

        self.title_lbl = Label(
            text='MoodSync', font_size=sp(16), bold=True,
            color=MS_TEXT, size_hint_x=1,
            halign='left', valign='middle',
        )
        self.title_lbl.bind(size=self.title_lbl.setter('text_size'))

        self.btn_rel = Button(
            text='R', font_size=sp(16), bold=True,
            size_hint=(None, None), size=(dp(40), dp(38)),
            background_normal='', background_color=(0,0,0,0),
            color=MS_DIM,
        )
        self.btn_rel.bind(on_press=lambda *a: self.app.reload_page())

        self.av_btn = Button(
            text='?', font_size=sp(13), bold=True,
            size_hint=(None, None), size=(dp(34), dp(34)),
            background_normal='', background_color=MS_DIM,
            color=(1,1,1,1),
        )
        self.av_btn.bind(on_press=lambda *a: self.app.toggle_account())

        inner.add_widget(self.btn_back)
        inner.add_widget(self.title_lbl)
        inner.add_widget(self.btn_rel)
        inner.add_widget(self.av_btn)
        self.add_widget(inner)

    def set_title(self, t):
        self.title_lbl.text = t[:26] + ('...' if len(t)>26 else '')

    def set_back(self, v):
        self.btn_back.color = MS_TEXT if v else MS_DIM

    def update_av(self):
        u = get_username()
        if u:
            parts = u.strip().split()
            init  = (parts[0][0] + (parts[-1][0] if len(parts)>1 else '')).upper()
            self.av_btn.text             = init
            self.av_btn.background_color = MS_ACCENT
        else:
            self.av_btn.text             = '?'
            self.av_btn.background_color = MS_DIM

# ── Account panel ─────────────────────────────────────────────────────────────

class AccountPanel(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app      = app
        self._visible = False
        self.opacity  = 0
        self.size_hint = (None, None)
        self.size = (dp(240), dp(240))
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0.13, 0.13, 0.17, 0.97)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos =lambda *a: setattr(self._bg,'pos', self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        lay = BoxLayout(orientation='vertical',
                        padding=dp(16), spacing=dp(10),
                        size_hint=(1,1))

        self._user_lbl = Label(
            text='Non connecte', font_size=sp(13),
            color=MS_DIM, size_hint_y=None, height=dp(22),
            halign='center')
        lay.add_widget(self._user_lbl)

        self._btn_login = self._btn('Se connecter', MS_ACCENT,
                                    self.app.do_login)
        self._btn_profile = self._btn('Mon profil', (0.15,0.15,0.2,1),
                                       self.app.open_profile)
        self._btn_logout  = self._btn('Deconnexion', (0.3,0.1,0.1,1),
                                       self.app.do_logout)
        self._btn_profile.opacity = 0; self._btn_profile.disabled = True
        self._btn_logout.opacity  = 0; self._btn_logout.disabled  = True

        btn_close = Button(
            text='Fermer', size_hint_y=None, height=dp(34),
            background_normal='', background_color=(0,0,0,0),
            color=MS_DIM, font_size=sp(12))
        btn_close.bind(on_press=lambda *a: self.hide())

        for w in (self._user_lbl, self._btn_login,
                  self._btn_profile, self._btn_logout,
                  btn_close, Widget()):
            lay.add_widget(w)
        self.add_widget(lay)

    def _btn(self, txt, col, fn):
        b = Button(text=txt, size_hint_y=None, height=dp(40),
                   background_normal='', background_color=col,
                   color=(1,1,1,1), font_size=sp(13))
        b.bind(on_press=lambda *a: (fn(), self.hide()))
        return b

    def refresh(self):
        if is_logged_in():
            self._user_lbl.text           = get_username()
            self._user_lbl.color          = MS_TEXT
            self._btn_login.opacity       = 0
            self._btn_login.disabled      = True
            self._btn_profile.opacity     = 1
            self._btn_profile.disabled    = False
            self._btn_logout.opacity      = 1
            self._btn_logout.disabled     = False
        else:
            self._user_lbl.text           = 'Non connecte'
            self._user_lbl.color          = MS_DIM
            self._btn_login.opacity       = 1
            self._btn_login.disabled      = False
            self._btn_profile.opacity     = 0
            self._btn_profile.disabled    = True
            self._btn_logout.opacity      = 0
            self._btn_logout.disabled     = True

    def show(self):
        self.refresh()
        self._visible = True
        self.opacity  = 1

    def hide(self):
        self._visible = False
        self.opacity  = 0

    def toggle(self):
        if self._visible: self.hide()
        else: self.show()

# ── Layout principal ──────────────────────────────────────────────────────────

class Root(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos =lambda *a: setattr(self._bg,'pos', self.pos),
            size=lambda *a: setattr(self._bg,'size',self.size),
        )

        self.wv = AndroidWebView(size_hint=(1,1), pos_hint={'x':0,'y':0})
        self.wv.on_title = self._on_title
        self.wv.on_url   = self._on_url
        self.add_widget(self.wv)

        self.tb = Toolbar(app, size_hint=(1,None), pos_hint={'x':0,'top':1})
        self.add_widget(self.tb)

        self.nav = BottomNav(app, size_hint=(1,None), pos_hint={'x':0,'y':0})
        self.add_widget(self.nav)

        self.acc_panel = AccountPanel(app)
        self.add_widget(self.acc_panel)

        Clock.schedule_once(self._adjust, 0.3)
        self.tb.bind(height=self._adjust)
        self.nav.bind(height=self._adjust)

    def _adjust(self, *a):
        th = self.tb.height
        nh = self.nav.height
        h  = self.height - th - nh
        if h > 0:
            self.wv.size_hint = (1, None)
            self.wv.height    = h
            self.wv.y         = nh

    def on_size(self, *a):
        self._adjust()
        self._pos_panel()

    def _pos_panel(self):
        self.acc_panel.pos = (
            self.width - self.acc_panel.width - dp(8),
            self.height - self.tb.height - self.acc_panel.height - dp(4),
        )

    def _on_title(self, title):
        if title.startswith('__USER__:'):
            name = title.split(':', 1)[1].strip()
            if name and not is_logged_in():
                save_account(name, get_fcm_token())
                Clock.schedule_once(
                    lambda dt: self.app._after_login(name), 0)
            return
        self.tb.set_title(title)

    def _on_url(self, url):
        self.tb.set_back(self.wv.can_back)
        self.nav.set_active_by_url(url)

# ── Polling ───────────────────────────────────────────────────────────────────

class Poller:
    def __init__(self, app):
        self.app  = app
        self._run = False
        self._last_msgs   = 0
        self._last_notifs = 0

    def start(self):
        if self._run: return
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._run = False

    def _loop(self):
        import urllib.request
        while self._run:
            if is_logged_in():
                for url, attr, key, nid, title in [
                    (API_MSGS,   '_last_msgs',   'chat',   101, 'MoodSync Messages'),
                    (API_NOTIFS, '_last_notifs', 'notifs', 103, 'MoodSync'),
                ]:
                    try:
                        r = urllib.request.urlopen(url, timeout=5)
                        d = json.loads(r.read().decode())
                        n = int(d.get('count', 0))
                        if n != getattr(self, attr):
                            setattr(self, attr, n)
                            Clock.schedule_once(
                                lambda dt, k=key, c=n:
                                    self.app.set_badge(k, c), 0)
                            if n > 0:
                                body = (f'{n} nouveau(x) message(s)'
                                        if key == 'chat'
                                        else f'{n} nouvelle(s) notification(s)')
                                Clock.schedule_once(
                                    lambda dt, t=title, b=body, i=nid:
                                        send_notif(t, b, i), 0)
                    except:
                        pass
            time.sleep(15)

# ── FCM register ─────────────────────────────────────────────────────────────

def register_fcm(token):
    def _do():
        import urllib.request, urllib.parse
        try:
            body = urllib.parse.urlencode({
                'token':    token,
                'username': get_username(),
                'platform': 'android',
            }).encode()
            urllib.request.urlopen(API_FCM_REG, body, timeout=5)
        except Exception as e:
            print("FCM register error:", e)
    threading.Thread(target=_do, daemon=True).start()

# ── App ───────────────────────────────────────────────────────────────────────

class MoodSyncApp(App):
    def build(self):
        Window.clearcolor = MS_BG
        if platform == 'android':
            Window.fullscreen = True
            create_notif_channel()

        self.layout  = Root(self)
        self.poller  = Poller(self)

        # FCM token
        get_fcm_token_android(self._on_fcm)

        # Démarrer le polling si déjà connecté
        if is_logged_in():
            self.poller.start()
            self.layout.tb.update_av()

        # Timers
        Clock.schedule_interval(self._detect_login, 5)

        # Bouton retour Android
        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_key_down=self._key_down)
            except Exception as e:
                print("key bind error:", e)

        return self.layout

    @property
    def webview(self):
        return self.layout.wv

    # ── Navigation ────────────────────────────────────────────────────────────

    def go_back(self):
        self.layout.wv.back()

    def reload_page(self):
        self.layout.wv.reload()

    def set_badge(self, key, n):
        self.layout.nav.set_badge(key, n)

    # ── Compte ────────────────────────────────────────────────────────────────

    def toggle_account(self):
        self.layout._pos_panel()
        self.layout.acc_panel.toggle()

    def do_login(self):
        self.layout.wv.load(LOGIN_URL)

    def do_logout(self):
        clear_account()
        self.layout.tb.update_av()
        self.poller.stop()
        self.layout.wv.clear_cookies()
        self.layout.wv.load(LOGIN_URL)

    def open_profile(self):
        self.layout.wv.load(PROFILE_URL)

    def _after_login(self, name):
        """Appelé après détection de la connexion."""
        self.layout.tb.update_av()
        self.layout.acc_panel.refresh()
        self.poller.start()
        tok = get_fcm_token()
        if tok:
            register_fcm(tok)

    # ── FCM ───────────────────────────────────────────────────────────────────

    def _on_fcm(self, token):
        if not token: return
        save_fcm_token(token)
        if is_logged_in():
            register_fcm(token)

    # ── Détection login ───────────────────────────────────────────────────────

    def _detect_login(self, dt):
        url = self.layout.wv.current_url
        if 'moodsync' not in url and 'alwaysdata' not in url:
            return
        self.layout.wv.run_js(
            "(function(){"
            "var m=document.querySelector('meta[name=\"username\"]');"
            "if(m&&m.content){document.title='__USER__:'+m.content;return;}"
            "var d=document.querySelector('[data-username]');"
            "if(d)document.title='__USER__:'+d.getAttribute('data-username');"
            "})()"
        )

    # ── Bouton retour Android ─────────────────────────────────────────────────

    def _key_down(self, keycode, *a):
        if keycode == 27:
            if self.layout.acc_panel._visible:
                self.layout.acc_panel.hide()
                return True
            if self.layout.wv.can_back:
                self.layout.wv.back()
                return True
        return False

    def on_stop(self):
        self.poller.stop()


if __name__ == '__main__':
    MoodSyncApp().run()
