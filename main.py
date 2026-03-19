#!/usr/bin/env python3
"""
MoodSync Mobile v1.0
Firebase project : moodsync-adf98
Package         : net.alwaysdata.moodsync
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
import json, os, threading, time, urllib.request, urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────

BASE         = "https://moodsync.alwaysdata.net"
HOME_URL     = BASE
LOGIN_URL    = BASE + "/login.php"
CHAT_URL     = BASE + "/chat.php"
NOTIF_URL    = BASE + "/notifications.php"
PROFILE_URL  = BASE + "/profile.php"
API_ME       = BASE + "/api/me.php"
API_MSGS     = BASE + "/api/messages_count.php"
API_NOTIFS   = BASE + "/api/notifications_count.php"
API_FCM_REG  = BASE + "/api/fcm_register.php"

FIREBASE_PROJECT = "moodsync-adf98"
FIREBASE_APP_ID  = "1:764322061858:android:8be4793191ed1b166db47b"
FIREBASE_API_KEY = "AIzaSyAUVnXEtMDLyTQQrAx9GovHUSrecraQ9ys"

DATA_DIR     = os.path.join(os.path.expanduser("~"), ".moodsync")
os.makedirs(DATA_DIR, exist_ok=True)
ACCOUNT_FILE = os.path.join(DATA_DIR, "account.json")

# ── Couleurs ──────────────────────────────────────────────────────────────────

MS_BG       = (0.086, 0.086, 0.102, 1)
MS_SURFACE  = (0.122, 0.122, 0.157, 1)
MS_TOOLBAR  = (0.090, 0.090, 0.118, 1)
MS_NAVBAR   = (0.078, 0.078, 0.098, 1)
MS_ACCENT   = (0.486, 0.361, 0.988, 1)
MS_ACCENT2  = (0.655, 0.545, 0.988, 1)
MS_TEXT     = (0.910, 0.902, 0.941, 1)
MS_TEXT_DIM = (0.533, 0.502, 0.627, 1)
MS_GREEN    = (0.506, 0.788, 0.584, 1)
MS_RED      = (0.949, 0.545, 0.510, 1)
MS_BADGE    = (0.949, 0.333, 0.333, 1)
MS_BORDER   = (0.180, 0.180, 0.220, 1)

# ── Account ───────────────────────────────────────────────────────────────────

class Account:
    _d = {}

    @classmethod
    def load(cls):
        try:
            if os.path.exists(ACCOUNT_FILE):
                cls._d = json.loads(open(ACCOUNT_FILE).read())
        except:
            cls._d = {}

    @classmethod
    def save(cls):
        open(ACCOUNT_FILE, 'w').write(json.dumps(cls._d))

    @classmethod
    def set(cls, username, fcm_token=""):
        cls._d = {"username": username, "fcm_token": fcm_token}
        cls.save()

    @classmethod
    def set_token(cls, token):
        cls._d["fcm_token"] = token
        cls.save()

    @classmethod
    def clear(cls):
        cls._d = {}
        cls.save()

    @classmethod
    def logged(cls):    return bool(cls._d.get("username"))
    @classmethod
    def username(cls):  return cls._d.get("username", "")
    @classmethod
    def fcm_token(cls): return cls._d.get("fcm_token", "")
    @classmethod
    def initials(cls):
        u = cls.username()
        if not u: return "?"
        p = u.strip().split()
        return (p[0][0] + (p[-1][0] if len(p) > 1 else "")).upper()

Account.load()

# ── Android WebView + FCM ─────────────────────────────────────────────────────

if platform == "android":
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, cast, PythonJavaClass, java_method

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

    def _create_channel():
        try:
            activity = PythonActivity.mActivity
            if Build.VERSION.SDK_INT >= 26:
                ch = NotifChannel(
                    CHANNEL_ID, "MoodSync", NotifManager.IMPORTANCE_HIGH)
                ch.setDescription("Notifications MoodSync")
                ch.enableVibration(True)
                nm = cast("android.app.NotificationManager",
                    activity.getSystemService(Context.NOTIFICATION_SERVICE))
                nm.createNotificationChannel(ch)
        except Exception as e:
            print("Channel:", e)

    def _notify(title, body, nid=100):
        try:
            activity = PythonActivity.mActivity
            intent = Intent(activity, PythonActivity)
            intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            flags = PendingIntent.FLAG_UPDATE_CURRENT
            if Build.VERSION.SDK_INT >= 23:
                flags |= PendingIntent.FLAG_IMMUTABLE
            pi = PendingIntent.getActivity(activity, nid, intent, flags)
            b = NotifCompat.Builder(activity, CHANNEL_ID)
            b.setSmallIcon(activity.getApplicationInfo().icon)
            b.setContentTitle(title)
            b.setContentText(body)
            b.setAutoCancel(True)
            b.setPriority(NotifCompat.PRIORITY_HIGH)
            b.setContentIntent(pi)
            nm = cast("android.app.NotificationManager",
                activity.getSystemService(Context.NOTIFICATION_SERVICE))
            nm.notify(nid, b.build())
        except Exception as e:
            print("Notif:", e)

    def _get_fcm_token(cb):
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
            print("FCM token:", e)
            cb("")

    class _MSWebViewClient(WebViewClient):
        def __init__(self, w):
            super().__init__()
            self._w = w

        def onPageFinished(self, wv, url):
            self._w.current_url = url or ""
            self._w.can_back = wv.canGoBack()
            self._w.can_fwd  = wv.canGoForward()
            t = wv.getTitle()
            if t and self._w.on_title:
                Clock.schedule_once(
                    lambda dt, _t=str(t): self._w.on_title(_t), 0)
            if self._w.on_url:
                Clock.schedule_once(
                    lambda dt, _u=url: self._w.on_url(_u or ""), 0)
            # Détecter user connecté
            wv.evaluateJavascript(
                "(function(){"
                "var m=document.querySelector("
                "'meta[name=\"username\"],meta[name=\"user-name\"]');"
                "if(m&&m.content)return m.content;"
                "var d=document.querySelector('[data-username]');"
                "if(d)return d.getAttribute('data-username');"
                "return '';})())", None)

        def shouldOverrideUrlLoading(self, wv, url):
            return False

    class AndroidWebView(Widget):
        current_url = StringProperty("")
        can_back    = BooleanProperty(False)
        can_fwd     = BooleanProperty(False)
        on_title    = None
        on_url      = None

        def __init__(self, **kw):
            super().__init__(**kw)
            self._wv = None
            Clock.schedule_once(self._create, 0)
            self.bind(pos=self._upd, size=self._upd)

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
            s.setMediaPlaybackRequiresUserGesture(False)
            s.setMixedContentMode(0)
            ua = s.getUserAgentString()
            s.setUserAgentString(ua + " MoodSyncApp/1.0")
            self._wv.setWebViewClient(_MSWebViewClient(self))
            self._wv.setWebChromeClient(WebChromeClient())
            self._wv.setBackgroundColor(Color_java.parseColor("#161619"))
            act.addContentView(self._wv, LayoutParams(
                LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
            self._wv.loadUrl(HOME_URL)
            Clock.schedule_once(self._upd, 0.1)

        @run_on_ui_thread
        def _upd(self, *a):
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
            cm.removeAllCookies(None)
            cm.flush()

else:
    class AndroidWebView(Widget):
        current_url = StringProperty("")
        can_back    = BooleanProperty(False)
        can_fwd     = BooleanProperty(False)
        on_title    = None
        on_url      = None
        def load(self, url): self.current_url = url
        def run_js(self, js): pass
        def back(self): pass
        def reload(self): pass
        def clear_cookies(self): pass

    def _create_channel(): pass
    def _notify(title, body, nid=100): print(f"NOTIF: {title} — {body}")
    def _get_fcm_token(cb): Clock.schedule_once(lambda dt: cb(""), 0.1)

# ── Badge ─────────────────────────────────────────────────────────────────────

class Badge(Widget):
    count = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (dp(17), dp(17))
        self.bind(count=self._draw, pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        if self.count <= 0: return
        with self.canvas:
            Color(*MS_BADGE)
            Ellipse(pos=self.pos, size=self.size)
        lbl = Label(
            text=str(min(self.count, 99)),
            font_size=sp(9), color=(1,1,1,1),
            size=self.size, pos=self.pos,
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

# ── NavButton ─────────────────────────────────────────────────────────────────

class NavButton(FloatLayout):
    active = BooleanProperty(False)

    def __init__(self, icon, label, badge=False, **kw):
        super().__init__(**kw)
        self._icon   = icon
        self._label  = label
        self._has_badge = badge
        self._cb = None
        self._build()
        self.bind(active=self._refresh)

    def _build(self):
        inner = BoxLayout(
            orientation='vertical', size_hint=(1,1),
            spacing=dp(2), padding=[0, dp(5), 0, dp(3)])
        self._lbl_icon = Label(
            text=self._icon, font_size=sp(22),
            color=MS_TEXT_DIM, size_hint_y=None, height=dp(28),
            halign='center')
        self._lbl_txt = Label(
            text=self._label, font_size=sp(10),
            color=MS_TEXT_DIM, size_hint_y=None, height=dp(14),
            halign='center')
        inner.add_widget(self._lbl_icon)
        inner.add_widget(self._lbl_txt)
        self.add_widget(inner)
        if badge:
            self.badge = Badge()
            self.badge.pos_hint = {'center_x': 0.65, 'center_y': 0.72}
            self.add_widget(self.badge)
        else:
            self.badge = None

    def _refresh(self, *a):
        c = MS_ACCENT2 if self.active else MS_TEXT_DIM
        self._lbl_icon.color = c
        self._lbl_txt.color  = c
        self.canvas.before.clear()
        if self.active:
            with self.canvas.before:
                Color(*MS_ACCENT, 0.13)
                RoundedRectangle(
                    pos=(self.x+dp(6), self.y+dp(3)),
                    size=(self.width-dp(12), self.height-dp(6)),
                    radius=[dp(10)])

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self._cb: self._cb()
            return True
        return super().on_touch_up(touch)

# ── Bottom Nav ────────────────────────────────────────────────────────────────

class BottomNav(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.app = app
        self.size_hint_y = None
        self.height = dp(60)
        self._btns = {}
        self._active = 'home'
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*MS_NAVBAR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*MS_BORDER)
            self._line = Line(width=1)
        self.bind(pos=self._upd, size=self._upd)
        for key, icon, lbl, badge in [
            ('home',   '🏠', 'Accueil',  False),
            ('chat',   '💬', 'Messages', True),
            ('notifs', '🔔', 'Notifs',   True),
            ('profil', '👤', 'Profil',   False),
        ]:
            b = NavButton(icon, lbl, badge=badge, size_hint=(1,1))
            b._cb = lambda k=key: self._tap(k)
            if key == self._active: b.active = True
            self._btns[key] = b
            self.add_widget(b)

    def _upd(self, *a):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        self._line.points = [self.x, self.top, self.right, self.top]

    def _tap(self, key):
        if key == self._active: return
        self._active = key
        for k, b in self._btns.items():
            b.active = (k == key)
        self.app.nav_to(key)

    def set_active(self, key):
        self._active = key
        for k, b in self._btns.items():
            b.active = (k == key)

    def set_badge(self, key, n):
        b = self._btns.get(key)
        if b and b.badge: b.badge.count = n

# ── Toolbar ───────────────────────────────────────────────────────────────────

class Toolbar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.app = app
        self.size_hint_y = None
        self.height = dp(54)
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*MS_TOOLBAR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        lay = BoxLayout(
            padding=[dp(10), dp(7), dp(10), dp(7)],
            spacing=dp(6))

        # Retour
        self.btn_back = self._ibtn('‹', self.app.go_back, size=dp(38))
        self.btn_back.opacity = 0.35
        lay.add_widget(self.btn_back)

        # Titre
        self.title = Label(
            text='MoodSync', font_size=sp(16), bold=True,
            color=MS_TEXT, size_hint_x=1,
            halign='left', valign='middle')
        self.title.bind(size=self.title.setter('text_size'))
        lay.add_widget(self.title)

        # Reload
        self.btn_rel = self._ibtn('↻', self.app.reload_page)
        lay.add_widget(self.btn_rel)

        # Avatar
        self.av = Button(
            text=Account.initials(),
            size_hint=(None,None), size=(dp(36),dp(36)),
            background_normal='', background_color=MS_ACCENT,
            font_size=sp(14), bold=True, color=(1,1,1,1))
        self.av.bind(on_press=lambda *a: self.app.toggle_account())
        lay.add_widget(self.av)
        self.add_widget(lay)

    def _ibtn(self, t, fn, size=dp(36)):
        b = Button(text=t, size_hint=(None,None), size=(size,size),
                   background_normal='', background_color=(0,0,0,0),
                   color=MS_TEXT_DIM, font_size=sp(20))
        b.bind(on_press=lambda *a: fn())
        return b

    def set_title(self, t):
        self.title.text = t[:30] + ('…' if len(t)>30 else '')

    def set_back(self, v):
        self.btn_back.opacity = 1.0 if v else 0.35

    def update_av(self):
        self.av.text = Account.initials()
        self.av.background_color = MS_ACCENT if Account.logged() else MS_TEXT_DIM

# ── Call overlay ──────────────────────────────────────────────────────────────

class CallOverlay(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.opacity = 0
        self._visible = False
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0, 0, 0, 0.88)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        panel = BoxLayout(
            orientation='vertical',
            size_hint=(None,None), size=(dp(270),dp(300)),
            pos_hint={'center_x':0.5,'center_y':0.5},
            spacing=dp(14), padding=dp(24))
        with panel.canvas.before:
            Color(0.12,0.12,0.17,1)
            self._pbg = RoundedRectangle(
                pos=panel.pos, size=panel.size, radius=[dp(18)])
        panel.bind(pos=self._upd_p, size=self._upd_p)

        self._av = Label(text='?', font_size=sp(36), color=(1,1,1,1),
                         size_hint_y=None, height=dp(60), halign='center')
        self._name = Label(text='Appel entrant', font_size=sp(17),
                           bold=True, color=MS_TEXT,
                           size_hint_y=None, height=dp(28), halign='center')
        self._type = Label(text='Appel audio', font_size=sp(12),
                           color=MS_TEXT_DIM,
                           size_hint_y=None, height=dp(20), halign='center')

        btns = BoxLayout(size_hint_y=None, height=dp(62),
                         spacing=dp(40), padding=[dp(30),0])
        b_no = Button(text='✕', size_hint=(None,None), size=(dp(58),dp(58)),
                      background_normal='', background_color=MS_RED,
                      font_size=sp(24), color=(1,1,1,1))
        b_yes= Button(text='✓', size_hint=(None,None), size=(dp(58),dp(58)),
                      background_normal='', background_color=MS_GREEN,
                      font_size=sp(24), color=(1,1,1,1))
        b_no.bind(on_press=lambda *a: self.decline())
        b_yes.bind(on_press=lambda *a: self.accept())
        btns.add_widget(b_no)
        btns.add_widget(b_yes)

        for w in (self._av, self._name, self._type, btns):
            panel.add_widget(w)
        self.add_widget(panel)
        self._panel = panel
        self._call_url = ''

    def _upd_p(self, *a):
        self._pbg.pos  = self._panel.pos
        self._pbg.size = self._panel.size

    def show(self, caller, call_type='audio', url=''):
        self._call_url   = url
        self._av.text    = (caller[0].upper() if caller else '?')
        self._name.text  = caller
        self._type.text  = 'Appel vidéo' if call_type=='video' else 'Appel audio'
        self._visible    = True
        self.opacity     = 1
        _notify(f'Appel de {caller}', 'Appuyez pour répondre', 102)

    def accept(self):
        self.opacity = 0; self._visible = False
        if self._call_url:
            self.app.webview.load(self._call_url)

    def decline(self):
        self.opacity = 0; self._visible = False
        self.app.webview.run_js(
            "if(window.__activePeerCall) window.__activePeerCall.close();")

# ── Account panel ─────────────────────────────────────────────────────────────

class AccountPanel(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.opacity = 0
        self._visible = False
        self.size_hint = (None,None)
        self.size = (dp(250), dp(280))
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0.13,0.13,0.17,0.97)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        lay = BoxLayout(orientation='vertical', padding=dp(16),
                        spacing=dp(10), size_hint=(1,1))

        self._title = Label(text='MoodSync', font_size=sp(16), bold=True,
                            color=MS_ACCENT2, size_hint_y=None, height=dp(30))
        self._user = Label(text='Non connecté', font_size=sp(12),
                           color=MS_TEXT_DIM, size_hint_y=None, height=dp(22))
        lay.add_widget(self._title)
        lay.add_widget(self._user)

        self._btn_login   = self._btn('🔑  Se connecter', MS_ACCENT, self.app.do_login)
        self._btn_profile = self._btn('👤  Mon profil',    MS_SURFACE, self.app.open_profile)
        self._btn_logout  = self._btn('🚪  Déconnexion',  (0.3,0.1,0.1,1), self.app.do_logout)
        self._btn_profile.opacity = 0; self._btn_profile.disabled = True
        self._btn_logout.opacity  = 0; self._btn_logout.disabled  = True

        self._fcm_lbl = Label(text='', font_size=sp(10), color=MS_TEXT_DIM,
                              size_hint_y=None, height=dp(18), halign='center')

        btn_close = Button(text='Fermer', size_hint_y=None, height=dp(32),
                           background_normal='', background_color=(0,0,0,0),
                           color=MS_TEXT_DIM, font_size=sp(12))
        btn_close.bind(on_press=lambda *a: self.hide())

        for w in (self._btn_login, self._btn_profile, self._btn_logout,
                  self._fcm_lbl, btn_close, Widget()):
            lay.add_widget(w)
        self.add_widget(lay)

    def _btn(self, txt, col, fn):
        b = Button(text=txt, size_hint_y=None, height=dp(40),
                   background_normal='', background_color=col,
                   color=(1,1,1,1), font_size=sp(13))
        b.bind(on_press=lambda *a: (fn(), self.hide()))
        return b

    def refresh(self):
        if Account.logged():
            self._user.text             = Account.username()
            self._user.color            = MS_TEXT
            self._btn_login.opacity     = 0
            self._btn_login.disabled    = True
            self._btn_profile.opacity   = 1
            self._btn_profile.disabled  = False
            self._btn_logout.opacity    = 1
            self._btn_logout.disabled   = False
            tok = Account.fcm_token()
            self._fcm_lbl.text  = '🔔 Notifs push actives' if tok else '🔕 Notifs push inactives'
            self._fcm_lbl.color = MS_GREEN if tok else MS_TEXT_DIM
        else:
            self._user.text             = 'Non connecté'
            self._user.color            = MS_TEXT_DIM
            self._btn_login.opacity     = 1
            self._btn_login.disabled    = False
            self._btn_profile.opacity   = 0
            self._btn_profile.disabled  = True
            self._btn_logout.opacity    = 0
            self._btn_logout.disabled   = True
            self._fcm_lbl.text = ''

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

# ── JS Bridge injecté dans la WebView ─────────────────────────────────────────

BRIDGE_JS = """
(function(){
    if(window.__ms_bridge) return;
    window.__ms_bridge = true;

    // Intercepter PeerJS pour appels entrants
    var _P = window.Peer;
    if(_P){
        var _on = _P.prototype.on;
        _P.prototype.on = function(ev, cb){
            if(ev === 'call'){
                return _on.call(this, ev, function(call){
                    window.__activePeerCall = call;
                    var isVideo = call.metadata && call.metadata.video;
                    // Signaler à l'app via le titre
                    document.title = '__CALL__:' + call.peer +
                        ':' + (isVideo ? 'video' : 'audio');
                    cb(call);
                });
            }
            return _on.call(this, ev, cb);
        };
    }
    console.log('[MoodSync Bridge] OK');
})();
"""

# ── Poller ────────────────────────────────────────────────────────────────────

class Poller:
    def __init__(self, app):
        self.app = app
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
        while self._run:
            if Account.logged():
                self._poll()
            time.sleep(15)

    def _poll(self):
        for url, attr, key, nid, ntitle in [
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
                        lambda dt, k=key, c=n: self.app.set_badge(k, c), 0)
                    if n > 0:
                        body = f'{n} nouveau(x) message(s)' if key=='chat' \
                               else f'{n} nouvelle(s) notification(s)'
                        Clock.schedule_once(
                            lambda dt, t=ntitle, b=body, i=nid:
                                _notify(t, b, i), 0)
            except:
                pass

# ── Layout ────────────────────────────────────────────────────────────────────

class Root(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        # WebView
        self.wv = AndroidWebView(size_hint=(1,1), pos_hint={'x':0,'y':0})
        self.wv.on_title = self._on_title
        self.wv.on_url   = self._on_url
        self.add_widget(self.wv)

        # Toolbar
        self.tb = Toolbar(app, size_hint=(1,None), pos_hint={'x':0,'top':1})
        self.add_widget(self.tb)

        # Bottom nav
        self.nav = BottomNav(app, size_hint=(1,None), pos_hint={'x':0,'y':0})
        self.add_widget(self.nav)

        # Panels flottants
        self.call_ov = CallOverlay(app, size_hint=(1,1))
        self.add_widget(self.call_ov)
        self.acc_pnl = AccountPanel(app)
        self.add_widget(self.acc_pnl)

        Clock.schedule_once(self._adjust, 0.2)
        self.tb.bind(height=self._adjust)
        self.nav.bind(height=self._adjust)

    def _adjust(self, *a):
        th = self.tb.height
        nh = self.nav.height
        h  = self.height - th - nh
        if h > 0:
            self.wv.size_hint = (1,None)
            self.wv.height    = h
            self.wv.y         = nh

    def on_size(self, *a):
        self._adjust()
        self._pos_panel()

    def _pos_panel(self):
        self.acc_pnl.pos = (
            self.width - self.acc_pnl.width - dp(8),
            self.height - self.tb.height - self.acc_pnl.height - dp(4))

    def _on_title(self, title):
        # Détecter appel entrant via titre
        if title.startswith('__CALL__:'):
            parts = title.split(':')
            caller    = parts[1] if len(parts) > 1 else 'Inconnu'
            call_type = parts[2] if len(parts) > 2 else 'audio'
            Clock.schedule_once(
                lambda dt: self.call_ov.show(caller, call_type), 0)
            return
        self.tb.set_title(title)

    def _on_url(self, url):
        self.tb.set_back(self.wv.can_back)
        if '/chat'          in url: self.nav.set_active('chat')
        elif '/notification' in url: self.nav.set_active('notifs')
        elif '/profile'      in url: self.nav.set_active('profil')
        elif url in (HOME_URL, HOME_URL+'/'): self.nav.set_active('home')

# ── App ───────────────────────────────────────────────────────────────────────

class MoodSyncApp(App):
    def build(self):
        Window.clearcolor = MS_BG
        if platform == 'android':
            Window.fullscreen = True
            _create_channel()

        self.root_layout = Root(self)
        self.poller = Poller(self)

        # FCM token
        _get_fcm_token(self._on_fcm)

        if Account.logged():
            self.poller.start()
            self.root_layout.tb.update_av()

        Clock.schedule_interval(self._detect_login, 5)
        Clock.schedule_interval(self._inject_bridge, 8)

        if platform == 'android':
            from android import activity
            activity.bind(on_key_down=self._key_down)

        return self.root_layout

    @property
    def webview(self): return self.root_layout.wv

    # ── Navigation ────────────────────────────────────────────────────────────

    def nav_to(self, key):
        urls = {'home': HOME_URL, 'chat': CHAT_URL,
                'notifs': NOTIF_URL, 'profil': PROFILE_URL}
        if key in urls:
            self.webview.load(urls[key])
        if key in ('chat','notifs'):
            self.set_badge(key, 0)

    def go_back(self):      self.webview.back()
    def reload_page(self):  self.webview.reload()

    def set_badge(self, key, n):
        self.root_layout.nav.set_badge(key, n)

    # ── Compte ────────────────────────────────────────────────────────────────

    def toggle_account(self):
        pnl = self.root_layout.acc_pnl
        self.root_layout._pos_panel()
        pnl.toggle()

    def do_login(self):
        self.webview.load(LOGIN_URL)

    def do_logout(self):
        Account.clear()
        self.root_layout.tb.update_av()
        self.poller.stop()
        self.webview.clear_cookies()
        self.webview.load(HOME_URL)

    def open_profile(self):
        self.webview.load(PROFILE_URL)

    # ── FCM ───────────────────────────────────────────────────────────────────

    def _on_fcm(self, token):
        if not token: return
        Account.set_token(token)
        if Account.logged():
            self._register_fcm(token)

    def _register_fcm(self, token):
        def _do():
            try:
                body = urllib.parse.urlencode({
                    'token':    token,
                    'username': Account.username(),
                    'platform': 'android',
                }).encode()
                urllib.request.urlopen(API_FCM_REG, body, timeout=5)
            except Exception as e:
                print("FCM register:", e)
        threading.Thread(target=_do, daemon=True).start()

    # ── Détection login ───────────────────────────────────────────────────────

    def _detect_login(self, dt):
        url = self.webview.current_url
        if 'moodsync' not in url and 'alwaysdata' not in url: return
        self.webview.run_js(
            "(function(){"
            "var m=document.querySelector('meta[name=\"username\"]');"
            "if(m&&m.content){"
            "  document.title='__USER__:'+m.content;return;}"
            "var d=document.querySelector('[data-username]');"
            "if(d)document.title='__USER__:'+d.getAttribute('data-username');"
            "})()"
        )

    # ── Bridge JS ─────────────────────────────────────────────────────────────

    def _inject_bridge(self, dt):
        url = self.webview.current_url
        if 'moodsync' in url or 'alwaysdata' in url:
            self.webview.run_js(BRIDGE_JS)

    # Appelé via _on_title quand __USER__: est détecté
    def on_user_detected(self, name):
        if name and not Account.logged():
            Account.set(name.strip(), Account.fcm_token())
            self.root_layout.tb.update_av()
            self.poller.start()
            tok = Account.fcm_token()
            if tok: self._register_fcm(tok)

    # ── Retour Android ────────────────────────────────────────────────────────

    def _key_down(self, keycode, *a):
        if keycode == 27:
            if self.root_layout.acc_pnl._visible:
                self.root_layout.acc_pnl.hide(); return True
            if self.root_layout.call_ov._visible:
                self.root_layout.call_ov.decline(); return True
            if self.webview.can_back:
                self.webview.back(); return True
        return False

    def on_stop(self):
        self.poller.stop()


if __name__ == '__main__':
    MoodSyncApp().run()
