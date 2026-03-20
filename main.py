#!/usr/bin/env python3
"""
MoodSync Mobile v3
+ Page composer message native
+ Son/vibration à la réception
+ Indicateur de frappe
+ Notif appel entrant PeerJS
+ Partage fichier galerie Android
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
import os, json, threading, time

HOME_URL    = "https://moodsync.alwaysdata.net"
LOGIN_URL   = HOME_URL + "/login.php"
CHAT_URL    = HOME_URL + "/chat.php"
NOTIF_URL   = HOME_URL + "/notifications.php"
PROFILE_URL = HOME_URL + "/profile.php"
API_MSGS    = HOME_URL + "/api/messages_count.php"
API_NOTIFS  = HOME_URL + "/api/notifications_count.php"
API_FCM_REG = HOME_URL + "/api/fcm_register.php"
API_SEND    = HOME_URL + "/api/send_message.php"
API_CONVS   = HOME_URL + "/api/conversations.php"
API_TYPING  = HOME_URL + "/api/typing.php"

# Couleurs
MS_BG      = (0.086, 0.086, 0.102, 1)
MS_NAVBAR  = (0.065, 0.065, 0.085, 1)
MS_TOOL    = (0.090, 0.090, 0.118, 1)
MS_SURFACE = (0.122, 0.122, 0.157, 1)
MS_ACCENT  = (0.486, 0.361, 0.988, 1)
MS_ACCENT2 = (0.655, 0.545, 0.988, 1)
MS_TEXT    = (0.910, 0.902, 0.941, 1)
MS_DIM     = (0.533, 0.502, 0.627, 1)
MS_GREEN   = (0.506, 0.788, 0.584, 1)
MS_RED     = (0.949, 0.545, 0.510, 1)
MS_BADGE   = (0.949, 0.333, 0.333, 1)
MS_BUBBLE_IN  = (0.165, 0.165, 0.210, 1)
MS_BUBBLE_OUT = (0.380, 0.270, 0.760, 1)

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
    d = load_account(); d["fcm_token"] = token
    open(ACCOUNT_FILE, 'w').write(json.dumps(d))

def clear_account():
    try: os.remove(ACCOUNT_FILE)
    except: pass

def is_logged_in():    return bool(load_account().get("username"))
def get_username():    return load_account().get("username", "")
def get_fcm_token_s(): return load_account().get("fcm_token", "")

# ── Android platform ──────────────────────────────────────────────────────────

if platform == "android":
    try:
        from android.runnable import run_on_ui_thread
        from jnius import autoclass, PythonJavaClass, java_method, cast as jcast

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
        Vibrator        = autoclass("android.os.Vibrator")
        VibrationEffect = None
        try:
            VibrationEffect = autoclass("android.os.VibrationEffect")
        except: pass
        FirebaseMsg     = autoclass("com.google.firebase.messaging.FirebaseMessaging")
        MediaPlayer     = autoclass("android.media.MediaPlayer")
        RingtoneManager = autoclass("android.media.RingtoneManager")

        CHANNEL_ID    = "moodsync_channel"
        CHANNEL_CALL  = "moodsync_call"

        def create_notif_channel():
            try:
                act = PythonActivity.mActivity
                if Build.VERSION.SDK_INT >= 26:
                    nm = jcast("android.app.NotificationManager",
                               act.getSystemService(Context.NOTIFICATION_SERVICE))
                    ch = NotifChannel(CHANNEL_ID, "MoodSync",
                                      NotifManager.IMPORTANCE_HIGH)
                    ch.enableVibration(True)
                    nm.createNotificationChannel(ch)
                    ch2 = NotifChannel(CHANNEL_CALL, "Appels MoodSync",
                                       NotifManager.IMPORTANCE_MAX)
                    ch2.enableVibration(True)
                    nm.createNotificationChannel(ch2)
            except Exception as e:
                print("Channel error:", e)

        def send_notif(title, body, nid=100, channel=None):
            try:
                act = PythonActivity.mActivity
                ch  = channel or CHANNEL_ID
                intent = Intent(act, PythonActivity)
                intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
                flags = PendingIntent.FLAG_UPDATE_CURRENT
                if Build.VERSION.SDK_INT >= 23:
                    flags |= PendingIntent.FLAG_IMMUTABLE
                pi = PendingIntent.getActivity(act, nid, intent, flags)
                b = NotifCompat.Builder(act, ch)
                b.setSmallIcon(act.getApplicationInfo().icon)
                b.setContentTitle(title)
                b.setContentText(body)
                b.setAutoCancel(True)
                b.setPriority(NotifCompat.PRIORITY_HIGH)
                b.setContentIntent(pi)
                nm = jcast("android.app.NotificationManager",
                           act.getSystemService(Context.NOTIFICATION_SERVICE))
                nm.notify(nid, b.build())
            except Exception as e:
                print("Notif error:", e)

        def vibrate(pattern_ms=None):
            try:
                act = PythonActivity.mActivity
                vib = jcast("android.os.Vibrator",
                            act.getSystemService(Context.VIBRATOR_SERVICE))
                if pattern_ms is None:
                    pattern_ms = [0, 200]
                if VibrationEffect and Build.VERSION.SDK_INT >= 26:
                    arr = autoclass("java.lang.reflect.Array")
                    effect = VibrationEffect.createWaveform(
                        pattern_ms, -1)
                    vib.vibrate(effect)
                else:
                    vib.vibrate(pattern_ms[1] if len(pattern_ms) > 1 else 200)
            except Exception as e:
                print("Vibrate error:", e)

        def play_notif_sound():
            try:
                act = PythonActivity.mActivity
                uri = RingtoneManager.getDefaultUri(
                    RingtoneManager.TYPE_NOTIFICATION)
                rt  = RingtoneManager.getRingtone(act, uri)
                rt.play()
            except Exception as e:
                print("Sound error:", e)

        def play_ringtone():
            try:
                act = PythonActivity.mActivity
                uri = RingtoneManager.getDefaultUri(
                    RingtoneManager.TYPE_RINGTONE)
                rt  = RingtoneManager.getRingtone(act, uri)
                rt.play()
            except Exception as e:
                print("Ringtone error:", e)

        def get_fcm_token_android(cb):
            try:
                class Listener(PythonJavaClass):
                    __javainterfaces__ = [
                        'com/google/android/gms/tasks/OnSuccessListener']
                    __javacontext__ = 'app'
                    @java_method('(Ljava/lang/Object;)V')
                    def onSuccess(self, result):
                        Clock.schedule_once(lambda dt: cb(str(result)), 0)
                FirebaseMsg.getInstance().getToken().addOnSuccessListener(
                    Listener())
            except Exception as e:
                print("FCM token error:", e); cb("")

        def open_gallery_picker(cb):
            """Ouvre la galerie Android et retourne le chemin du fichier."""
            try:
                from android import activity as act_mod
                from android.runnable import run_on_ui_thread as rut

                Intent_local = autoclass("android.content.Intent")
                i = Intent_local(Intent_local.ACTION_PICK)
                i.setType("*/*")
                i.putExtra(Intent_local.EXTRA_MIME_TYPES,
                           ["image/*", "video/*", "audio/*"])

                class ResultListener:
                    def on_result(self, request_code, result_code, data):
                        RESULT_OK = -1
                        if result_code == RESULT_OK and data:
                            uri = data.getData()
                            if uri:
                                Clock.schedule_once(
                                    lambda dt: cb(str(uri.toString())), 0)
                        act_mod.unbind(on_activity_result=self.on_result)

                rl = ResultListener()
                act_mod.bind(on_activity_result=rl.on_result)
                PythonActivity.mActivity.startActivityForResult(i, 42)
            except Exception as e:
                print("Gallery error:", e)
                cb(None)

        class MSWebViewClient(WebViewClient):
            def __init__(self, w):
                super().__init__(); self._w = w

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
                wv.evaluateJavascript(
                    "(function(){"
                    "var m=document.querySelector('meta[name=\"username\"]');"
                    "if(m&&m.content){document.title='__USER__:'+m.content;return;}"
                    "var d=document.querySelector('[data-username]');"
                    "if(d)document.title='__USER__:'+d.getAttribute('data-username');"
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
                start = HOME_URL if is_logged_in() else LOGIN_URL
                self._wv.loadUrl(start)
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
                if self._wv: self._wv.evaluateJavascript(js, None)

            @run_on_ui_thread
            def back(self):
                if self._wv and self._wv.canGoBack(): self._wv.goBack()

            @run_on_ui_thread
            def reload(self):
                if self._wv: self._wv.reload()

            @run_on_ui_thread
            def clear_cookies(self):
                cm = CookieManager.getInstance()
                cm.removeAllCookies(None); cm.flush()

            @run_on_ui_thread
            def show(self):
                if self._wv: self._wv.setVisibility(0)   # VISIBLE

            @run_on_ui_thread
            def hide(self):
                if self._wv: self._wv.setVisibility(4)   # INVISIBLE

        ANDROID_OK = True

    except Exception as e:
        print("Android init error:", e)
        ANDROID_OK = False
        def create_notif_channel(): pass
        def send_notif(t, b, nid=100, channel=None): pass
        def vibrate(p=None): pass
        def play_notif_sound(): pass
        def play_ringtone(): pass
        def get_fcm_token_android(cb): Clock.schedule_once(lambda dt: cb(""), 0.1)
        def open_gallery_picker(cb): cb(None)

        class AndroidWebView(Widget):
            current_url = StringProperty("")
            can_back    = BooleanProperty(False)
            can_fwd     = BooleanProperty(False)
            on_title    = None; on_url = None
            def load(self, url): pass
            def run_js(self, js): pass
            def back(self): pass
            def reload(self): pass
            def clear_cookies(self): pass
            def show(self): pass
            def hide(self): pass

else:
    ANDROID_OK = False
    def create_notif_channel(): pass
    def send_notif(t, b, nid=100, channel=None): print(f"NOTIF [{nid}]: {t} — {b}")
    def vibrate(p=None): pass
    def play_notif_sound(): pass
    def play_ringtone(): pass
    def get_fcm_token_android(cb): Clock.schedule_once(lambda dt: cb(""), 0.1)
    def open_gallery_picker(cb): cb(None)

    class AndroidWebView(Widget):
        current_url = StringProperty("")
        can_back    = BooleanProperty(False)
        can_fwd     = BooleanProperty(False)
        on_title    = None; on_url = None
        def load(self, url): pass
        def run_js(self, js): pass
        def back(self): pass
        def reload(self): pass
        def clear_cookies(self): pass
        def show(self): pass
        def hide(self): pass

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
        if self.count <= 0: return
        with self.canvas:
            Color(*MS_BADGE)
            Ellipse(pos=self.pos, size=self.size)
        lbl = Label(text=str(min(self.count,99)), font_size=sp(8),
                    color=(1,1,1,1), size=self.size, pos=self.pos,
                    halign='center', valign='middle')
        lbl.texture_update()
        if lbl.texture:
            with self.canvas:
                Color(1,1,1,1)
                Rectangle(
                    texture=lbl.texture,
                    pos=(self.x+(self.width-lbl.texture.width)/2,
                         self.y+(self.height-lbl.texture.height)/2),
                    size=lbl.texture.size)

# ── NavItem ───────────────────────────────────────────────────────────────────

class NavItem(FloatLayout):
    def __init__(self, icon, label, callback, has_badge=False, **kwargs):
        super().__init__(**kwargs)
        self._cb = callback
        inner = BoxLayout(orientation='vertical',
                          padding=[0,dp(5),0,dp(3)], spacing=dp(2),
                          size_hint=(1,1))
        self._icon = Label(text=icon, font_size=sp(20), color=MS_DIM,
                           size_hint_y=None, height=dp(26), halign='center')
        self._lbl  = Label(text=label, font_size=sp(10), color=MS_DIM,
                           size_hint_y=None, height=dp(14), halign='center')
        inner.add_widget(self._icon); inner.add_widget(self._lbl)
        self.add_widget(inner)
        if has_badge:
            self.badge = Badge()
            self.badge.pos_hint = {'center_x':0.65,'center_y':0.72}
            self.add_widget(self.badge)
        else:
            self.badge = None

    def set_active(self, v):
        c = MS_ACCENT2 if v else MS_DIM
        self._icon.color = c; self._lbl.color = c

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self._cb: self._cb()
            return True
        return super().on_touch_up(touch)

# ── Bottom Nav ────────────────────────────────────────────────────────────────

class BottomNav(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)
        self.app = app
        self.size_hint_y = None
        self.height = dp(60)
        self._items  = {}
        self._active = 'home'
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*MS_NAVBAR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))
        tabs = [
            ('home',    'Accueil',  HOME_URL,    False),
            ('chat',    'Messages', CHAT_URL,    True),
            ('notifs',  'Notifs',   NOTIF_URL,   True),
            ('profile', 'Profil',   PROFILE_URL, False),
        ]
        icons = {'home':'o','chat':'M','notifs':'N','profile':'P'}
        for key, label, url, badge in tabs:
            item = NavItem(icons[key], label,
                           callback=lambda k=key,u=url: self._tap(k,u),
                           has_badge=badge, size_hint=(1,1))
            if key == self._active: item.set_active(True)
            self._items[key] = item
            self.add_widget(item)

    def _tap(self, key, url):
        self._active = key
        for k, item in self._items.items(): item.set_active(k==key)
        if not is_logged_in():
            self.app.webview.load(LOGIN_URL)
        elif key == 'chat':
            self.app.show_compose()   # ← page compose native
        else:
            self.app.webview.load(url)
        if key in ('chat','notifs'): self.set_badge(key, 0)

    def set_active_by_url(self, url):
        key = None
        if '/chat' in url:            key = 'chat'
        elif '/notification' in url:  key = 'notifs'
        elif '/profile' in url:       key = 'profile'
        elif url.rstrip('/') == HOME_URL.rstrip('/'): key = 'home'
        if key:
            self._active = key
            for k, item in self._items.items(): item.set_active(k==key)

    def set_badge(self, key, n):
        item = self._items.get(key)
        if item and item.badge: item.badge.count = n

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
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))
        inner = BoxLayout(padding=[dp(10),dp(8),dp(10),dp(8)], spacing=dp(8))

        self.btn_back = Button(
            text='<', font_size=sp(20), bold=True,
            size_hint=(None,None), size=(dp(40),dp(38)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_back.bind(on_press=lambda *a: self.app.go_back())

        self.title_lbl = Label(
            text='MoodSync', font_size=sp(16), bold=True,
            color=MS_TEXT, size_hint_x=1, halign='left', valign='middle')
        self.title_lbl.bind(size=self.title_lbl.setter('text_size'))

        self.typing_lbl = Label(
            text='', font_size=sp(11), color=MS_ACCENT2,
            size_hint=(None,None), size=(dp(80),dp(20)))

        self.btn_rel = Button(
            text='R', font_size=sp(16), bold=True,
            size_hint=(None,None), size=(dp(40),dp(38)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_rel.bind(on_press=lambda *a: self.app.reload_page())

        self.av_btn = Button(
            text='?', font_size=sp(13), bold=True,
            size_hint=(None,None), size=(dp(34),dp(34)),
            background_normal='', background_color=MS_DIM, color=(1,1,1,1))
        self.av_btn.bind(on_press=lambda *a: self.app.toggle_account())

        inner.add_widget(self.btn_back)
        inner.add_widget(self.title_lbl)
        inner.add_widget(self.typing_lbl)
        inner.add_widget(self.btn_rel)
        inner.add_widget(self.av_btn)
        self.add_widget(inner)

    def set_title(self, t):
        self.title_lbl.text = t[:26]+('...' if len(t)>26 else '')

    def set_back(self, v):
        self.btn_back.color = MS_TEXT if v else MS_DIM

    def show_typing(self, name):
        self.typing_lbl.text = name + ' ecrit...'
        Clock.schedule_once(lambda dt: setattr(self.typing_lbl,'text',''), 3)

    def update_av(self):
        u = get_username()
        if u:
            p = u.strip().split()
            self.av_btn.text = (p[0][0]+(p[-1][0] if len(p)>1 else '')).upper()
            self.av_btn.background_color = MS_ACCENT
        else:
            self.av_btn.text = '?'
            self.av_btn.background_color = MS_DIM

# ── Compose page native ───────────────────────────────────────────────────────

class BubbleMsg(BoxLayout):
    """Une bulle de message dans la compose page."""
    def __init__(self, text, is_mine, **kwargs):
        super().__init__(size_hint_y=None, **kwargs)
        self.padding = [dp(8), dp(4)]
        lbl = Label(
            text=text,
            font_size=sp(14),
            color=MS_TEXT,
            size_hint_x=None,
            halign='left',
            valign='middle',
            text_size=(Window.width * 0.65, None),
        )
        lbl.texture_update()
        lbl.size = lbl.texture_size
        self.height = lbl.height + dp(20)

        with self.canvas.before:
            Color(*(MS_BUBBLE_OUT if is_mine else MS_BUBBLE_IN))
            RoundedRectangle(
                pos=(lbl.x - dp(8), lbl.y - dp(6)),
                size=(lbl.width + dp(16), lbl.height + dp(12)),
                radius=[dp(14)])

        if is_mine:
            self.add_widget(Widget())
            self.add_widget(lbl)
        else:
            self.add_widget(lbl)
            self.add_widget(Widget())


class ComposePage(FloatLayout):
    """Page native pour composer et envoyer un message."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app         = app
        self._conv_id    = None
        self._conv_name  = ''
        self._messages   = []
        self._typing_timer = None
        self._visible    = False
        self.opacity     = 0
        self._build()

    def _build(self):
        # Fond
        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        main = BoxLayout(orientation='vertical', size_hint=(1,1))

        # ── Header compose ────────────────────────────────────────────────────
        hdr = BoxLayout(
            size_hint_y=None, height=dp(54),
            padding=[dp(8),dp(8)], spacing=dp(8))
        with hdr.canvas.before:
            Color(*MS_TOOL)
            self._hbg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda *a: setattr(self._hbg,'pos',hdr.pos),
                 size=lambda *a: setattr(self._hbg,'size',hdr.size))

        btn_close = Button(
            text='X', font_size=sp(16), bold=True,
            size_hint=(None,None), size=(dp(38),dp(38)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        btn_close.bind(on_press=lambda *a: self.hide())

        self._hdr_title = Label(
            text='Messages', font_size=sp(15), bold=True,
            color=MS_TEXT, size_hint_x=1, halign='left', valign='middle')
        self._hdr_title.bind(size=self._hdr_title.setter('text_size'))

        self._typing_indicator = Label(
            text='', font_size=sp(11), color=MS_ACCENT2,
            size_hint=(None,None), size=(dp(120),dp(20)))

        hdr.add_widget(btn_close)
        hdr.add_widget(self._hdr_title)
        hdr.add_widget(self._typing_indicator)
        main.add_widget(hdr)

        # ── Liste conversations ────────────────────────────────────────────────
        self._conv_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None, spacing=dp(2))
        self._conv_list.bind(
            minimum_height=self._conv_list.setter('height'))

        self._conv_scroll = ScrollView(size_hint=(1,1))
        self._conv_scroll.add_widget(self._conv_list)
        main.add_widget(self._conv_scroll)

        # ── Zone messages ─────────────────────────────────────────────────────
        self._msg_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None, spacing=dp(4),
            padding=[dp(8),dp(8)])
        self._msg_container.bind(
            minimum_height=self._msg_container.setter('height'))

        self._msg_scroll = ScrollView(size_hint=(1,1))
        self._msg_scroll.add_widget(self._msg_container)
        self._msg_scroll.opacity = 0
        main.add_widget(self._msg_scroll)

        # ── Barre saisie ──────────────────────────────────────────────────────
        input_bar = BoxLayout(
            size_hint_y=None, height=dp(58),
            padding=[dp(8),dp(6)], spacing=dp(6))
        with input_bar.canvas.before:
            Color(0.08, 0.08, 0.11, 1)
            self._ibg = Rectangle(pos=input_bar.pos, size=input_bar.size)
        input_bar.bind(
            pos=lambda *a: setattr(self._ibg,'pos',input_bar.pos),
            size=lambda *a: setattr(self._ibg,'size',input_bar.size))

        # Bouton galerie
        btn_gallery = Button(
            text='IMG', font_size=sp(11), bold=True,
            size_hint=(None,None), size=(dp(42),dp(42)),
            background_normal='', background_color=MS_SURFACE,
            color=MS_TEXT)
        btn_gallery.bind(on_press=lambda *a: self._pick_file())

        self._txt = TextInput(
            hint_text='Ecrire un message...',
            hint_text_color=MS_DIM,
            foreground_color=MS_TEXT,
            background_color=(0.12,0.12,0.16,1),
            cursor_color=MS_ACCENT,
            font_size=sp(14),
            size_hint=(1,None),
            height=dp(42),
            multiline=False,
            padding=[dp(10),dp(10)],
        )
        self._txt.bind(text=self._on_typing)
        self._txt.bind(on_text_validate=lambda *a: self._send())

        btn_send = Button(
            text='>', font_size=sp(18), bold=True,
            size_hint=(None,None), size=(dp(42),dp(42)),
            background_normal='', background_color=MS_ACCENT,
            color=(1,1,1,1))
        btn_send.bind(on_press=lambda *a: self._send())

        input_bar.add_widget(btn_gallery)
        input_bar.add_widget(self._txt)
        input_bar.add_widget(btn_send)
        main.add_widget(input_bar)

        self.add_widget(main)

    # ── Affichage ─────────────────────────────────────────────────────────────

    def show(self):
        self._visible = True
        self.opacity  = 1
        self._conv_id = None
        self._hdr_title.text = 'Messages'
        self._conv_scroll.opacity = 1
        self._msg_scroll.opacity  = 0
        self._load_conversations()

    def hide(self):
        self._visible = False
        self.opacity  = 0

    # ── Conversations ─────────────────────────────────────────────────────────

    def _load_conversations(self):
        self._conv_list.clear_widgets()
        lbl = Label(text='Chargement...', color=MS_DIM,
                    font_size=sp(13), size_hint_y=None, height=dp(40))
        self._conv_list.add_widget(lbl)

        def _fetch():
            import urllib.request
            try:
                r = urllib.request.urlopen(API_CONVS, timeout=6)
                d = json.loads(r.read().decode())
                Clock.schedule_once(lambda dt: self._show_convs(d), 0)
            except Exception as e:
                Clock.schedule_once(
                    lambda dt: self._show_convs_error(str(e)), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_convs(self, data):
        self._conv_list.clear_widgets()
        convs = data.get('conversations', [])
        if not convs:
            lbl = Label(text='Aucune conversation', color=MS_DIM,
                        font_size=sp(13), size_hint_y=None, height=dp(40))
            self._conv_list.add_widget(lbl)
            return
        for c in convs:
            row = BoxLayout(size_hint_y=None, height=dp(62),
                            padding=[dp(12),dp(8)], spacing=dp(10))
            with row.canvas.before:
                Color(*MS_SURFACE)
                RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])
            row.bind(pos=lambda *a, r=row: self._upd_row(r),
                     size=lambda *a, r=row: self._upd_row(r))

            # Avatar initiales
            av = Label(
                text=(c.get('username','?')[:1]).upper(),
                font_size=sp(16), bold=True, color=(1,1,1,1),
                size_hint=(None,None), size=(dp(40),dp(40)))
            with av.canvas.before:
                Color(*MS_ACCENT)
                Ellipse(pos=av.pos, size=av.size)
            av.bind(pos=lambda *a, l=av: setattr(l.canvas.before.children[1],'pos',l.pos))

            info = BoxLayout(orientation='vertical', size_hint_x=1)
            name_lbl = Label(
                text=c.get('username',''),
                font_size=sp(14), bold=True, color=MS_TEXT,
                halign='left', valign='middle', size_hint_y=None, height=dp(22))
            name_lbl.bind(size=name_lbl.setter('text_size'))
            prev = c.get('last_message','')
            prev_lbl = Label(
                text=prev[:40]+('...' if len(prev)>40 else ''),
                font_size=sp(11), color=MS_DIM,
                halign='left', valign='middle', size_hint_y=None, height=dp(18))
            prev_lbl.bind(size=prev_lbl.setter('text_size'))
            info.add_widget(name_lbl); info.add_widget(prev_lbl)

            row.add_widget(av); row.add_widget(info)
            cid    = c.get('chat_id')
            cname  = c.get('username','')
            row_ref = row

            def _open(touch, cid=cid, cname=cname, row=row_ref):
                if row.collide_point(*touch.pos):
                    self._open_conv(cid, cname)
                    return True

            row.bind(on_touch_up=lambda w,t,cid=cid,cn=cname:
                     self._open_conv(cid,cn) if w.collide_point(*t.pos) else None)
            self._conv_list.add_widget(row)

    def _show_convs_error(self, err):
        self._conv_list.clear_widgets()
        lbl = Label(text=f'Erreur: {err}', color=MS_RED,
                    font_size=sp(12), size_hint_y=None, height=dp(40))
        self._conv_list.add_widget(lbl)

    def _upd_row(self, row):
        row.canvas.before.clear()
        with row.canvas.before:
            Color(*MS_SURFACE)
            RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])

    # ── Ouvrir conversation ────────────────────────────────────────────────────

    def _open_conv(self, chat_id, username):
        self._conv_id   = chat_id
        self._conv_name = username
        self._hdr_title.text = username
        self._conv_scroll.opacity = 0
        self._msg_scroll.opacity  = 1
        self._msg_container.clear_widgets()
        self._load_messages()
        # Polling msgs toutes les 3s quand conversation ouverte
        Clock.schedule_interval(self._poll_messages, 3)

    def _load_messages(self):
        if not self._conv_id: return
        def _fetch():
            import urllib.request
            try:
                url = f"{HOME_URL}/api/messages.php?chat_id={self._conv_id}&limit=30"
                r = urllib.request.urlopen(url, timeout=6)
                d = json.loads(r.read().decode())
                Clock.schedule_once(lambda dt: self._show_msgs(d), 0)
            except: pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _show_msgs(self, data):
        self._msg_container.clear_widgets()
        msgs = data.get('messages', [])
        me   = get_username()
        for m in msgs:
            is_mine = m.get('username') == me
            body    = m.get('message','')
            if not body: continue
            bbl = Label(
                text=body,
                font_size=sp(13),
                color=MS_TEXT,
                size_hint_y=None,
                halign='right' if is_mine else 'left',
                valign='middle',
            )
            bbl.text_size = (Window.width * 0.65, None)
            bbl.texture_update()
            bbl.height = bbl.texture_size[1] + dp(20)

            row = BoxLayout(size_hint_y=None, height=bbl.height+dp(8),
                            padding=[dp(6),dp(2)])
            with row.canvas.before:
                Color(*(MS_BUBBLE_OUT if is_mine else MS_BUBBLE_IN))
                RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(12)])
            row.bind(pos=lambda *a,r=row,m=is_mine: self._upd_row(r),
                     size=lambda *a,r=row,m=is_mine: self._upd_row(r))

            if is_mine:
                row.add_widget(Widget()); row.add_widget(bbl)
            else:
                row.add_widget(bbl); row.add_widget(Widget())

            self._msg_container.add_widget(row)

        Clock.schedule_once(lambda dt:
            self._msg_scroll.scroll_to(self._msg_container.children[0]
                                        if self._msg_container.children
                                        else self._msg_container), 0.1)

    def _poll_messages(self, dt):
        if not self._visible or not self._conv_id:
            Clock.unschedule(self._poll_messages)
            return
        self._load_messages()

    # ── Envoi message ─────────────────────────────────────────────────────────

    def _send(self):
        txt = self._txt.text.strip()
        if not txt or not self._conv_id: return
        self._txt.text = ''
        me = get_username()

        # Afficher bulle localement immédiatement
        bbl = Label(text=txt, font_size=sp(13), color=MS_TEXT,
                    size_hint_y=None, halign='right', valign='middle')
        bbl.text_size = (Window.width * 0.65, None)
        bbl.texture_update()
        bbl.height = bbl.texture_size[1] + dp(20)
        row = BoxLayout(size_hint_y=None, height=bbl.height+dp(8),
                        padding=[dp(6),dp(2)])
        with row.canvas.before:
            Color(*MS_BUBBLE_OUT)
            RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(12)])
        row.bind(pos=lambda *a,r=row: self._upd_row(r),
                 size=lambda *a,r=row: self._upd_row(r))
        row.add_widget(Widget()); row.add_widget(bbl)
        self._msg_container.add_widget(row)
        Clock.schedule_once(lambda dt:
            self._msg_scroll.scroll_to(row), 0.1)

        # Envoyer en background
        def _do():
            import urllib.request, urllib.parse
            try:
                body = urllib.parse.urlencode({
                    'chat_id': self._conv_id,
                    'message': txt,
                }).encode()
                urllib.request.urlopen(API_SEND, body, timeout=5)
            except Exception as e:
                print("Send msg error:", e)
        threading.Thread(target=_do, daemon=True).start()

    # ── Indicateur de frappe ──────────────────────────────────────────────────

    def _on_typing(self, instance, value):
        """Envoyer signal de frappe au serveur."""
        if not self._conv_id or not value: return
        if self._typing_timer:
            Clock.unschedule(self._typing_timer)
        self._typing_timer = Clock.schedule_once(
            lambda dt: self._send_typing(), 0.8)

    def _send_typing(self):
        def _do():
            import urllib.request, urllib.parse
            try:
                body = urllib.parse.urlencode({
                    'chat_id': self._conv_id,
                    'action':  'typing',
                }).encode()
                urllib.request.urlopen(API_TYPING, body, timeout=3)
            except: pass
        threading.Thread(target=_do, daemon=True).start()

    def show_typing_indicator(self, name):
        self._typing_indicator.text = f'{name} ecrit...'
        Clock.schedule_once(
            lambda dt: setattr(self._typing_indicator,'text',''), 3)

    # ── Galerie / fichier ─────────────────────────────────────────────────────

    def _pick_file(self):
        open_gallery_picker(self._on_file_picked)

    def _on_file_picked(self, uri):
        if not uri or not self._conv_id: return
        # Afficher aperçu et envoyer via chat.php WebView
        url = f"{CHAT_URL}?chat_id={self._conv_id}"
        self.app.webview.load(url)
        self.hide()

# ── Call overlay ──────────────────────────────────────────────────────────────

class CallOverlay(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app      = app
        self._visible = False
        self.opacity  = 0
        self._ringing = False
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0, 0, 0, 0.88)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        panel = BoxLayout(
            orientation='vertical',
            size_hint=(None,None), size=(dp(270),dp(290)),
            pos_hint={'center_x':0.5,'center_y':0.5},
            spacing=dp(14), padding=dp(22))
        with panel.canvas.before:
            Color(0.12,0.12,0.17,1)
            self._pbg = RoundedRectangle(
                pos=panel.pos, size=panel.size, radius=[dp(18)])
        panel.bind(pos=lambda *a: setattr(self._pbg,'pos',panel.pos),
                   size=lambda *a: setattr(self._pbg,'size',panel.size))

        self._av = Label(text='?', font_size=sp(36),
                         color=(1,1,1,1), size_hint_y=None, height=dp(58),
                         halign='center')
        self._name = Label(text='Appel entrant', font_size=sp(17),
                           bold=True, color=MS_TEXT,
                           size_hint_y=None, height=dp(28), halign='center')
        self._type_lbl = Label(text='Appel audio', font_size=sp(12),
                               color=MS_DIM,
                               size_hint_y=None, height=dp(20), halign='center')

        btns = BoxLayout(size_hint_y=None, height=dp(64),
                         spacing=dp(40), padding=[dp(28),0])
        b_no = Button(text='X', size_hint=(None,None), size=(dp(58),dp(58)),
                      background_normal='', background_color=MS_RED,
                      font_size=sp(20), color=(1,1,1,1), bold=True)
        b_yes= Button(text='OK', size_hint=(None,None), size=(dp(58),dp(58)),
                      background_normal='', background_color=MS_GREEN,
                      font_size=sp(16), color=(1,1,1,1), bold=True)
        b_no.bind(on_press=lambda *a: self.decline())
        b_yes.bind(on_press=lambda *a: self.accept())
        btns.add_widget(b_no); btns.add_widget(b_yes)

        for w in (self._av, self._name, self._type_lbl, btns):
            panel.add_widget(w)
        self.add_widget(panel)
        self._call_url = ''

    def show(self, caller, call_type='audio', url=''):
        self._call_url  = url
        self._av.text   = (caller[:1].upper() if caller else '?')
        self._name.text = caller
        self._type_lbl.text = 'Appel video' if call_type=='video' else 'Appel audio'
        self._visible   = True
        self.opacity    = 1
        # Sonnerie + vibration
        play_ringtone()
        vibrate([0, 500, 300, 500])
        send_notif(f'Appel de {caller}',
                   'Appuyez pour repondre', 102,
                   channel='moodsync_call' if ANDROID_OK else None)
        self._ringing = True

    def accept(self):
        self._visible = False
        self.opacity  = 0
        self._ringing = False
        if self._call_url:
            self.app.webview.load(self._call_url)

    def decline(self):
        self._visible = False
        self.opacity  = 0
        self._ringing = False
        self.app.webview.run_js(
            "if(window.__activePeerCall) window.__activePeerCall.close();")

# ── Account panel ─────────────────────────────────────────────────────────────

class AccountPanel(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app; self._visible = False; self.opacity = 0
        self.size_hint = (None,None); self.size = (dp(240),dp(230))
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0.13,0.13,0.17,0.97)
            self._bg = RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(14)])
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))
        lay = BoxLayout(orientation='vertical',padding=dp(14),spacing=dp(8),size_hint=(1,1))
        self._user_lbl = Label(text='Non connecte',font_size=sp(13),
                               color=MS_DIM,size_hint_y=None,height=dp(22),halign='center')
        lay.add_widget(self._user_lbl)
        self._btn_login   = self._btn('Se connecter',MS_ACCENT,self.app.do_login)
        self._btn_profile = self._btn('Mon profil',(0.15,0.15,0.2,1),self.app.open_profile)
        self._btn_logout  = self._btn('Deconnexion',(0.3,0.1,0.1,1),self.app.do_logout)
        self._btn_profile.opacity=0; self._btn_profile.disabled=True
        self._btn_logout.opacity=0;  self._btn_logout.disabled=True
        btn_close = Button(text='Fermer',size_hint_y=None,height=dp(32),
                           background_normal='',background_color=(0,0,0,0),
                           color=MS_DIM,font_size=sp(12))
        btn_close.bind(on_press=lambda *a: self.hide())
        for w in (self._user_lbl,self._btn_login,self._btn_profile,
                  self._btn_logout,btn_close,Widget()):
            lay.add_widget(w)
        self.add_widget(lay)

    def _btn(self,txt,col,fn):
        b=Button(text=txt,size_hint_y=None,height=dp(40),
                 background_normal='',background_color=col,
                 color=(1,1,1,1),font_size=sp(13))
        b.bind(on_press=lambda *a:(fn(),self.hide())); return b

    def refresh(self):
        logged = is_logged_in()
        self._user_lbl.text  = get_username() if logged else 'Non connecte'
        self._user_lbl.color = MS_TEXT if logged else MS_DIM
        self._btn_login.opacity   = 0 if logged else 1
        self._btn_login.disabled  = logged
        self._btn_profile.opacity = 1 if logged else 0
        self._btn_profile.disabled= not logged
        self._btn_logout.opacity  = 1 if logged else 0
        self._btn_logout.disabled = not logged

    def show(self): self.refresh(); self._visible=True; self.opacity=1
    def hide(self): self._visible=False; self.opacity=0
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
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        self.wv  = AndroidWebView(size_hint=(1,1),pos_hint={'x':0,'y':0})
        self.wv.on_title = self._on_title
        self.wv.on_url   = self._on_url
        self.add_widget(self.wv)

        self.tb  = Toolbar(app,size_hint=(1,None),pos_hint={'x':0,'top':1})
        self.add_widget(self.tb)

        self.nav = BottomNav(app,size_hint=(1,None),pos_hint={'x':0,'y':0})
        self.add_widget(self.nav)

        self.compose    = ComposePage(app,size_hint=(1,1),pos_hint={'x':0,'y':0})
        self.add_widget(self.compose)

        self.call_ov    = CallOverlay(app,size_hint=(1,1))
        self.add_widget(self.call_ov)

        self.acc_panel  = AccountPanel(app)
        self.add_widget(self.acc_panel)

        Clock.schedule_once(self._adjust, 0.3)
        self.tb.bind(height=self._adjust)
        self.nav.bind(height=self._adjust)

    def _adjust(self, *a):
        th = self.tb.height; nh = self.nav.height
        h  = self.height - th - nh
        if h > 0:
            self.wv.size_hint = (1,None); self.wv.height = h; self.wv.y = nh
            self.compose.size_hint = (1,None)
            self.compose.height = h; self.compose.y = nh

    def on_size(self, *a):
        self._adjust(); self._pos_panel()

    def _pos_panel(self):
        self.acc_panel.pos = (
            self.width - self.acc_panel.width - dp(8),
            self.height - self.tb.height - self.acc_panel.height - dp(4))

    def _on_title(self, title):
        if title.startswith('__USER__:'):
            name = title.split(':',1)[1].strip()
            if name and not is_logged_in():
                save_account(name, get_fcm_token_s())
                Clock.schedule_once(lambda dt: self.app._after_login(name), 0)
            return
        if title.startswith('__CALL__:'):
            parts = title.split(':')
            caller    = parts[1] if len(parts)>1 else 'Inconnu'
            call_type = parts[2] if len(parts)>2 else 'audio'
            call_url  = parts[3] if len(parts)>3 else ''
            Clock.schedule_once(
                lambda dt: self.call_ov.show(caller, call_type, call_url), 0)
            return
        if title.startswith('__TYPING__:'):
            name = title.split(':',1)[1].strip()
            Clock.schedule_once(
                lambda dt: self._show_typing(name), 0)
            return
        self.tb.set_title(title)

    def _on_url(self, url):
        self.tb.set_back(self.wv.can_back)
        self.nav.set_active_by_url(url)

    def _show_typing(self, name):
        self.tb.show_typing(name)
        if self.compose._visible:
            self.compose.show_typing_indicator(name)

# ── Polling ───────────────────────────────────────────────────────────────────

class Poller:
    def __init__(self, app):
        self.app = app; self._run = False
        self._last_msgs = 0; self._last_notifs = 0

    def start(self):
        if self._run: return
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self): self._run = False

    def _loop(self):
        import urllib.request
        while self._run:
            if is_logged_in():
                for url,attr,key,nid,title in [
                    (API_MSGS,  '_last_msgs',  'chat',  101,'MoodSync Messages'),
                    (API_NOTIFS,'_last_notifs','notifs',103,'MoodSync'),
                ]:
                    try:
                        r = urllib.request.urlopen(url, timeout=5)
                        n = int(json.loads(r.read().decode()).get('count',0))
                        if n != getattr(self,attr):
                            setattr(self,attr,n)
                            Clock.schedule_once(
                                lambda dt,k=key,c=n: self.app.set_badge(k,c),0)
                            if n > 0:
                                body = (f'{n} nouveau(x) message(s)'
                                        if key=='chat'
                                        else f'{n} nouvelle(s) notification(s)')
                                Clock.schedule_once(
                                    lambda dt,t=title,b=body,i=nid:
                                    (send_notif(t,b,i),
                                     play_notif_sound(),
                                     vibrate([0,150,80,150])),0)
                    except: pass
            time.sleep(15)

def register_fcm(token):
    def _do():
        import urllib.request, urllib.parse
        try:
            body = urllib.parse.urlencode({
                'token':get_fcm_token_s(),'username':get_username(),'platform':'android'
            }).encode()
            urllib.request.urlopen(API_FCM_REG, body, timeout=5)
        except Exception as e: print("FCM reg:", e)
    threading.Thread(target=_do, daemon=True).start()

# ── App ───────────────────────────────────────────────────────────────────────

# JS injecté dans la WebView pour intercepter PeerJS + frappe
BRIDGE_JS = """
(function(){
  if(window.__ms_bridge)return;
  window.__ms_bridge=true;
  // Intercepter PeerJS appels entrants
  var _P=window.Peer;
  if(_P){
    var _on=_P.prototype.on;
    _P.prototype.on=function(ev,cb){
      if(ev==='call'){
        return _on.call(this,ev,function(call){
          window.__activePeerCall=call;
          var isVideo=call.metadata&&call.metadata.video;
          var chatUrl=window.location.href;
          document.title='__CALL__:'+
            (call.metadata&&call.metadata.from_name||call.peer)+':'+
            (isVideo?'video':'audio')+':'+chatUrl;
          cb(call);
        });
      }
      return _on.call(this,ev,cb);
    };
  }
  // Indicateur de frappe — écouter événements input des autres
  // (simulé via polling serveur côté Python)
  console.log('[MoodSync Bridge] OK');
})();
"""


class MoodSyncApp(App):
    def build(self):
        Window.clearcolor = MS_BG
        if platform == 'android':
            Window.fullscreen = True
            create_notif_channel()

        self.layout = Root(self)
        self.poller = Poller(self)

        get_fcm_token_android(self._on_fcm)

        if is_logged_in():
            self.poller.start()
            self.layout.tb.update_av()

        Clock.schedule_interval(self._detect_login, 5)
        Clock.schedule_interval(self._inject_bridge, 8)

        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_key_down=self._key_down)
            except Exception as e:
                print("key bind:", e)

        return self.layout

    @property
    def webview(self): return self.layout.wv

    def go_back(self):
        if self.layout.compose._visible:
            self.layout.compose.hide()
        else:
            self.layout.wv.back()

    def reload_page(self):   self.layout.wv.reload()
    def set_badge(self,k,n): self.layout.nav.set_badge(k,n)

    def show_compose(self):
        self.layout.compose.show()

    def toggle_account(self):
        self.layout._pos_panel()
        self.layout.acc_panel.toggle()

    def do_login(self):    self.layout.wv.load(LOGIN_URL)
    def open_profile(self):self.layout.wv.load(PROFILE_URL)

    def do_logout(self):
        clear_account()
        self.layout.tb.update_av()
        self.poller.stop()
        self.layout.wv.clear_cookies()
        self.layout.wv.load(LOGIN_URL)

    def _after_login(self, name):
        self.layout.tb.update_av()
        self.layout.acc_panel.refresh()
        self.poller.start()
        tok = get_fcm_token_s()
        if tok: register_fcm(tok)

    def _on_fcm(self, token):
        if not token: return
        save_fcm_token(token)
        if is_logged_in(): register_fcm(token)

    def _detect_login(self, dt):
        url = self.layout.wv.current_url
        if 'moodsync' not in url and 'alwaysdata' not in url: return
        self.layout.wv.run_js(
            "(function(){"
            "var m=document.querySelector('meta[name=\"username\"]');"
            "if(m&&m.content){document.title='__USER__:'+m.content;return;}"
            "var d=document.querySelector('[data-username]');"
            "if(d)document.title='__USER__:'+d.getAttribute('data-username');"
            "})()")

    def _inject_bridge(self, dt):
        url = self.layout.wv.current_url
        if 'moodsync' in url or 'alwaysdata' in url:
            self.layout.wv.run_js(BRIDGE_JS)

    def _key_down(self, keycode, *a):
        if keycode == 27:
            if self.layout.call_ov._visible:
                self.layout.call_ov.decline(); return True
            if self.layout.acc_panel._visible:
                self.layout.acc_panel.hide(); return True
            if self.layout.compose._visible:
                self.layout.compose.hide(); return True
            if self.layout.wv.can_back:
                self.layout.wv.back(); return True
        return False

    def on_stop(self): self.poller.stop()


if __name__ == '__main__':
    MoodSyncApp().run()
