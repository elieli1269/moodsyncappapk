#!/usr/bin/env python3
"""MoodSync Mobile v5 — crash logger intégré"""

# === CRASH LOGGER — DOIT ETRE EN PREMIER =====================================
import sys, traceback, os

_LOG_DIR = os.path.join(os.path.expanduser("~"), ".moodsync")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "crash.txt")

def _crash(et, ev, tb):
    try:
        with open(_LOG_FILE, 'w') as f:
            f.write("=== MOODSYNC CRASH ===\n")
            traceback.print_exception(et, ev, tb, file=f)
    except: pass
    sys.__excepthook__(et, ev, tb)

sys.excepthook = _crash

def _log(tag, msg):
    try:
        with open(_LOG_FILE, 'a') as f:
            f.write(f"[{tag}] {msg}\n")
    except: pass

_log("START", "main.py loading...")

# === IMPORTS KIVY =============================================================
try:
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
    from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse
    from kivy.metrics import dp, sp
    from kivy.clock import Clock
    from kivy.properties import StringProperty, BooleanProperty, NumericProperty
    _log("KIVY", "OK")
except Exception as e:
    _log("KIVY", f"ERREUR: {e}")
    raise

import json, threading, time

# === CONFIG ===================================================================
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
MS_BUB_OUT = (0.380, 0.270, 0.760, 1)
MS_BUB_IN  = (0.165, 0.165, 0.210, 1)

ACCOUNT_FILE = os.path.join(_LOG_DIR, "account.json")

def load_account():
    try:
        if os.path.exists(ACCOUNT_FILE):
            return json.loads(open(ACCOUNT_FILE).read())
    except: pass
    return {}

def save_account(username, token=""):
    d = load_account(); d["username"] = username
    if token: d["fcm_token"] = token
    open(ACCOUNT_FILE, 'w').write(json.dumps(d))

def save_token(token):
    d = load_account(); d["fcm_token"] = token
    open(ACCOUNT_FILE, 'w').write(json.dumps(d))

def clear_account():
    try: os.remove(ACCOUNT_FILE)
    except: pass

def is_logged():  return bool(load_account().get("username"))
def get_user():   return load_account().get("username", "")
def get_token():  return load_account().get("fcm_token", "")

# === ANDROID — imports isolés =================================================
_log("ANDROID", "loading platform modules...")

_rut = None
try:
    from android.runnable import run_on_ui_thread as _rut
    _log("ANDROID", "run_on_ui_thread OK")
except Exception as e:
    _log("ANDROID", f"run_on_ui_thread ERREUR: {e}")

_jnius_ok = False
autoclass = None
jcast     = None
try:
    from jnius import autoclass, cast as jcast
    _jnius_ok = True
    _log("ANDROID", "jnius OK")
except Exception as e:
    _log("ANDROID", f"jnius ERREUR: {e}")

def _cls(name):
    if not _jnius_ok: return None
    try:
        c = autoclass(name)
        _log("CLASS", f"OK: {name.split('.')[-1]}")
        return c
    except Exception as e:
        _log("CLASS", f"ERREUR {name.split('.')[-1]}: {e}")
        return None

_PA    = _cls("org.kivy.android.PythonActivity")
_WV    = _cls("android.webkit.WebView")
_WVC   = _cls("android.webkit.WebViewClient")
_WCC   = _cls("android.webkit.WebChromeClient")
_CM    = _cls("android.webkit.CookieManager")
_LP    = _cls("android.view.ViewGroup$LayoutParams")
_CJ    = _cls("android.graphics.Color")
_Build = _cls("android.os.Build")
_NC    = _cls("androidx.core.app.NotificationCompat")
_NCH   = _cls("android.app.NotificationChannel")
_NM    = _cls("android.app.NotificationManager")
_PI    = _cls("android.app.PendingIntent")
_INT   = _cls("android.content.Intent")
_Vib   = _cls("android.os.Vibrator")
_VibFX = _cls("android.os.VibrationEffect")
_RM    = _cls("android.media.RingtoneManager")
_FM    = _cls("com.google.firebase.messaging.FirebaseMessaging")

_wv_ok    = bool(_PA and _WV and _LP and _rut)
_notif_ok = bool(_PA and _NC and _PI and _INT)
_log("ANDROID", f"wv_ok={_wv_ok} notif_ok={_notif_ok} fcm={bool(_FM)}")

CHANNEL_ID   = "moodsync_msg"
CHANNEL_CALL = "moodsync_call"

def create_channels():
    if not _notif_ok: return
    try:
        act = _PA.mActivity
        if _Build and _Build.VERSION.SDK_INT >= 26:
            nm = jcast("android.app.NotificationManager",
                       act.getSystemService("notification"))
            for cid, cname, imp in [
                (CHANNEL_ID,   "MoodSync",        _NM.IMPORTANCE_HIGH),
                (CHANNEL_CALL, "Appels MoodSync",  _NM.IMPORTANCE_MAX),
            ]:
                ch = _NCH(cid, cname, imp)
                ch.enableVibration(True)
                nm.createNotificationChannel(ch)
        _log("CHANNELS", "OK")
    except Exception as e:
        _log("CHANNELS", f"ERREUR: {e}")

def push_notif(title, body, nid=100, ch=CHANNEL_ID):
    if not _notif_ok: return
    try:
        act   = _PA.mActivity
        flags = _PI.FLAG_UPDATE_CURRENT
        if _Build and _Build.VERSION.SDK_INT >= 23:
            flags |= _PI.FLAG_IMMUTABLE
        intent = _INT(act, _PA)
        intent.setFlags(_INT.FLAG_ACTIVITY_SINGLE_TOP)
        pi = _PI.getActivity(act, nid, intent, flags)
        b  = _NC.Builder(act, ch)
        b.setSmallIcon(act.getApplicationInfo().icon)
        b.setContentTitle(title); b.setContentText(body)
        b.setAutoCancel(True); b.setPriority(_NC.PRIORITY_HIGH)
        b.setContentIntent(pi)
        nm = jcast("android.app.NotificationManager",
                   act.getSystemService("notification"))
        nm.notify(nid, b.build())
    except Exception as e:
        _log("NOTIF", f"ERREUR: {e}")

def vibrate(ms=200):
    if not _Vib or not _PA: return
    try:
        v = jcast("android.os.Vibrator",
                  _PA.mActivity.getSystemService("vibrator"))
        if _Build and _Build.VERSION.SDK_INT >= 26 and _VibFX:
            v.vibrate(_VibFX.createOneShot(ms, -1))
        else:
            v.vibrate(ms)
    except Exception as e:
        _log("VIBRATE", f"ERREUR: {e}")

def play_sound(ring=False):
    if not _RM or not _PA: return
    try:
        act = _PA.mActivity
        uri = _RM.getDefaultUri(_RM.TYPE_RINGTONE if ring else _RM.TYPE_NOTIFICATION)
        _RM.getRingtone(act, uri).play()
    except Exception as e:
        _log("SOUND", f"ERREUR: {e}")

def get_fcm_token_android(cb):
    if not _FM:
        _log("FCM", "Firebase non disponible")
        Clock.schedule_once(lambda dt: cb(""), 0.1)
        return
    try:
        from jnius import PythonJavaClass, java_method
        class L(PythonJavaClass):
            __javainterfaces__ = ['com/google/android/gms/tasks/OnSuccessListener']
            __javacontext__    = 'app'
            @java_method('(Ljava/lang/Object;)V')
            def onSuccess(self, result):
                _log("FCM", f"token OK: {str(result)[:20]}...")
                def _f(dt):
                    try:
                        cb(str(result))
                    except Exception as e:
                        _log("FCM", f"onSuccess callback error: {e}")
                Clock.schedule_once(_f, 0)
        _FM.getInstance().getToken().addOnSuccessListener(L())
    except Exception as e:
        _log("FCM", f"ERREUR: {e}")
        Clock.schedule_once(lambda dt: cb(""), 0.1)

def open_gallery(cb):
    try:
        from android import activity as am
        i = _INT(_INT.ACTION_PICK); i.setType("*/*")
        class R:
            def on_result(self, req, res, data):
                if res == -1 and data:
                    u = data.getData()
                    if u: Clock.schedule_once(lambda dt: cb(str(u.toString())), 0)
                am.unbind(on_activity_result=self.on_result)
        r = R(); am.bind(on_activity_result=r.on_result)
        _PA.mActivity.startActivityForResult(i, 42)
    except Exception as e:
        _log("GALLERY", f"ERREUR: {e}"); cb(None)

# === WEBVIEW ==================================================================

if _wv_ok:
    _log("WV", "Creating WebViewClient class...")
    try:
        class _MSClient(_WVC):
            def __init__(self, w):
                super().__init__(); self._w = w
            def onPageStarted(self, wv, url, fav):
                self._w.current_url = url or ""
                if self._w.on_url:
                    def _cb(dt):
                        try:
                            self._w.on_url(url or "")
                        except Exception as e:
                            _log("WV", f"on_url callback error: {e}")
                    Clock.schedule_once(_cb, 0)
            def onPageFinished(self, wv, url):
                self._w.current_url = url or ""
                self._w.can_back = wv.canGoBack()
                self._w.can_fwd  = wv.canGoForward()
                t = wv.getTitle()
                if t and self._w.on_title:
                    def _cb(dt):
                        try:
                            self._w.on_title(str(t))
                        except Exception as e:
                            _log("WV", f"on_title callback error: {e}")
                    Clock.schedule_once(_cb, 0)
                try:
                    wv.evaluateJavascript(
                        "(function(){"
                        "var m=document.querySelector('meta[name=\"username\"]');"
                        "if(m&&m.content){document.title='__U:'+m.content;return;}"
                        "var d=document.querySelector('[data-username]');"
                        "if(d)document.title='__U:'+d.getAttribute('data-username');"
                        "})()", None)
                except Exception as e:
                    _log("WV", f"evaluateJavascript error: {e}")
            def shouldOverrideUrlLoading(self, wv, url): return False
        _log("WV", "WebViewClient OK")
    except Exception as e:
        _log("WV", f"WebViewClient ERREUR: {e}")
        _wv_ok = False


class MSWebView(Widget):
    current_url = StringProperty("")
    can_back    = BooleanProperty(False)
    can_fwd     = BooleanProperty(False)
    on_title    = None
    on_url      = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wv = None
        _log("WV", f"MSWebView init, wv_ok={_wv_ok}")
        if _wv_ok:
            Clock.schedule_once(self._create, 0)
            self.bind(pos=self._upd, size=self._upd)
        else:
            lbl = Label(text="WebView non disponible.\nVérifiez les permissions et l'installation.", color=MS_RED, halign='center', valign='middle', font_size=sp(16))
            self.add_widget(lbl)

    def _create(self, *a):
        if not _wv_ok: return
        @_rut
        def _do():
            try:
                _log("WV", "Creating WebView...")
                act = _PA.mActivity
                _CM.getInstance().setAcceptCookie(True)
                self._wv = _WV(act)
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
                s.setUserAgentString(s.getUserAgentString() + " MoodSyncApp/1.0")
                self._wv.setWebViewClient(_MSClient(self))
                self._wv.setWebChromeClient(_WCC())
                if _CJ:
                    self._wv.setBackgroundColor(_CJ.parseColor("#161619"))
                act.addContentView(self._wv, _LP(_LP.MATCH_PARENT, _LP.MATCH_PARENT))
                url = HOME_URL if is_logged() else LOGIN_URL
                _log("WV", f"Loading: {url}")
                self._wv.loadUrl(url)
                Clock.schedule_once(self._upd, 0.2)
                _log("WV", "WebView created OK")
            except Exception as e:
                _log("WV", f"CREATE ERREUR: {e}\n{traceback.format_exc()}")
        _do()

    def _upd(self, *a):
        if not self._wv: return
        @_rut
        def _do():
            try:
                from kivy.core.window import Window as W
                self._wv.setX(int(self.x))
                self._wv.setY(int(W.height - self.y - self.height))
                lp = self._wv.getLayoutParams()
                lp.width = int(self.width)
                lp.height = int(self.height)
                self._wv.setLayoutParams(lp)
                self._wv.requestLayout()
            except Exception as e:
                _log("WV", f"UPD ERREUR: {e}")
        _do()

    def load(self, url):
        if not self._wv: return
        @_rut
        def _do():
            try: self._wv.loadUrl(url)
            except Exception as e: _log("WV", f"load ERREUR: {e}")
        _do()

    def run_js(self, js):
        if not self._wv: return
        @_rut
        def _do():
            try: self._wv.evaluateJavascript(js, None)
            except: pass
        _do()

    def back(self):
        if not self._wv: return
        @_rut
        def _do():
            try:
                if self._wv.canGoBack(): self._wv.goBack()
            except: pass
        _do()

    def reload(self):
        if not self._wv: return
        @_rut
        def _do():
            try: self._wv.reload()
            except: pass
        _do()

    def clear_cookies(self):
        if not _CM: return
        @_rut
        def _do():
            try:
                cm = _CM.getInstance()
                cm.removeAllCookies(None); cm.flush()
            except: pass
        _do()

# === Badge ====================================================================

class Badge(Widget):
    count = NumericProperty(0)
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None); self.size = (dp(16), dp(16))
        self.bind(count=self._d, pos=self._d, size=self._d)
    def _d(self, *a):
        self.canvas.clear()
        if self.count <= 0: return
        with self.canvas:
            Color(*MS_BADGE); Ellipse(pos=self.pos, size=self.size)
        l = Label(text=str(min(self.count, 99)), font_size=sp(8),
                  color=(1,1,1,1), size=self.size, pos=self.pos,
                  halign='center', valign='middle')
        l.texture_update()
        if l.texture:
            with self.canvas:
                Color(1,1,1,1)
                Rectangle(texture=l.texture,
                    pos=(self.x+(self.width-l.texture.width)/2,
                         self.y+(self.height-l.texture.height)/2),
                    size=l.texture.size)

# === NavItem ==================================================================

class NavItem(FloatLayout):
    def __init__(self, icon, label, cb, badge=False, **kw):
        super().__init__(**kw); self._cb = cb
        box = BoxLayout(orientation='vertical', padding=[0,dp(5),0,dp(3)],
                        spacing=dp(2), size_hint=(1,1))
        self._ic = Label(text=icon, font_size=sp(20), color=MS_DIM,
                         size_hint_y=None, height=dp(26), halign='center')
        self._lb = Label(text=label, font_size=sp(10), color=MS_DIM,
                         size_hint_y=None, height=dp(14), halign='center')
        box.add_widget(self._ic); box.add_widget(self._lb)
        self.add_widget(box)
        if badge:
            self.badge = Badge()
            self.badge.pos_hint = {'center_x': .65, 'center_y': .72}
            self.add_widget(self.badge)
        else: self.badge = None
    def set_active(self, v):
        c = MS_ACCENT2 if v else MS_DIM
        self._ic.color = c; self._lb.color = c
    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self._cb: self._cb()
            return True
        return super().on_touch_up(touch)

# === BottomNav ================================================================

class BottomNav(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.app = app; self.size_hint_y = None; self.height = dp(60)
        self._items = {}; self._active = 'home'; self._build()
    def _build(self):
        with self.canvas.before:
            Color(*MS_NAVBAR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        for key, label, url, bdg in [
            ('home',    'Accueil',  HOME_URL,    False),
            ('chat',    'Messages', CHAT_URL,    True),
            ('notifs',  'Notifs',   NOTIF_URL,   True),
            ('profile', 'Profil',   PROFILE_URL, False),
        ]:
            icons = {'home': 'o', 'chat': 'M', 'notifs': 'N', 'profile': 'P'}
            item = NavItem(icons[key], label,
                           cb=lambda k=key, u=url: self._tap(k, u),
                           badge=bdg, size_hint=(1, 1))
            if key == 'home': item.set_active(True)
            self._items[key] = item; self.add_widget(item)
    def _tap(self, key, url):
        self._active = key
        for k, i in self._items.items(): i.set_active(k == key)
        if key == 'chat': self.app.show_compose()
        elif not is_logged(): self.app.webview.load(LOGIN_URL)
        else: self.app.webview.load(url)
        if key in ('chat', 'notifs'): self.set_badge(key, 0)
    def set_by_url(self, url):
        k = None
        if '/chat' in url:            k = 'chat'
        elif '/notification' in url:  k = 'notifs'
        elif '/profile' in url:       k = 'profile'
        elif url.rstrip('/') == HOME_URL.rstrip('/'): k = 'home'
        if k:
            self._active = k
            for ki, i in self._items.items(): i.set_active(ki == k)
    def set_badge(self, key, n):
        i = self._items.get(key)
        if i and i.badge: i.badge.count = n

# === Toolbar ==================================================================

class Toolbar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.app = app; self.size_hint_y = None; self.height = dp(54)
        self._build()
    def _build(self):
        with self.canvas.before:
            Color(*MS_TOOL)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        inner = BoxLayout(padding=[dp(10),dp(8),dp(10),dp(8)], spacing=dp(8))
        self.btn_back = Button(text='<', font_size=sp(20), bold=True,
            size_hint=(None,None), size=(dp(40),dp(38)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_back.bind(on_press=lambda *a: self.app.go_back())
        self.title = Label(text='MoodSync', font_size=sp(16), bold=True,
            color=MS_TEXT, size_hint_x=1, halign='left', valign='middle')
        self.title.bind(size=self.title.setter('text_size'))
        self.typing = Label(text='', font_size=sp(11), color=MS_ACCENT2,
            size_hint=(None,None), size=(dp(100),dp(20)))
        self.btn_r = Button(text='R', font_size=sp(16), bold=True,
            size_hint=(None,None), size=(dp(38),dp(38)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_r.bind(on_press=lambda *a: self.app.reload_page())
        self.av = Button(text='?', font_size=sp(13), bold=True,
            size_hint=(None,None), size=(dp(34),dp(34)),
            background_normal='', background_color=MS_DIM, color=(1,1,1,1))
        self.av.bind(on_press=lambda *a: self.app.toggle_account())
        for w in (self.btn_back, self.title, self.typing, self.btn_r, self.av):
            inner.add_widget(w)
        self.add_widget(inner)
    def set_title(self, t): self.title.text = t[:26]+('...' if len(t)>26 else '')
    def set_back(self, v): self.btn_back.color = MS_TEXT if v else MS_DIM
    def show_typing(self, name):
        self.typing.text = name+' ecrit...'
        Clock.unschedule(self._ct); Clock.schedule_once(self._ct, 3)
    def _ct(self, *a): self.typing.text = ''
    def update_av(self):
        u = get_user()
        if u:
            p = u.strip().split()
            self.av.text = (p[0][0]+(p[-1][0] if len(p)>1 else '')).upper()
            self.av.background_color = MS_ACCENT
        else:
            self.av.text = '?'; self.av.background_color = MS_DIM

# === ComposePage ==============================================================

class ComposePage(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app; self._cid = None; self._cname = ''
        self._vis = False; self.opacity = 0; self._build()
    def _build(self):
        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        main = BoxLayout(orientation='vertical', size_hint=(1,1))
        # header
        hdr = BoxLayout(size_hint_y=None, height=dp(54),
                        padding=[dp(8),dp(8)], spacing=dp(8))
        with hdr.canvas.before:
            Color(*MS_TOOL)
            self._hbg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda *a: setattr(self._hbg, 'pos', hdr.pos),
                 size=lambda *a: setattr(self._hbg, 'size', hdr.size))
        bx = Button(text='X', font_size=sp(16), bold=True,
            size_hint=(None,None), size=(dp(38),dp(38)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        bx.bind(on_press=lambda *a: self.hide())
        self._ht = Label(text='Messages', font_size=sp(15), bold=True,
            color=MS_TEXT, size_hint_x=1, halign='left', valign='middle')
        self._ht.bind(size=self._ht.setter('text_size'))
        self._ty = Label(text='', font_size=sp(11), color=MS_ACCENT2,
            size_hint=(None,None), size=(dp(120),dp(20)))
        hdr.add_widget(bx); hdr.add_widget(self._ht); hdr.add_widget(self._ty)
        main.add_widget(hdr)
        # conversations
        self._cvbox = BoxLayout(orientation='vertical', size_hint_y=None,
                                spacing=dp(2), padding=[dp(6),dp(6)])
        self._cvbox.bind(minimum_height=self._cvbox.setter('height'))
        self._cvscroll = ScrollView(size_hint=(1,1))
        self._cvscroll.add_widget(self._cvbox)
        main.add_widget(self._cvscroll)
        # messages
        self._mbox = BoxLayout(orientation='vertical', size_hint_y=None,
                               spacing=dp(4), padding=[dp(8),dp(8)])
        self._mbox.bind(minimum_height=self._mbox.setter('height'))
        self._mscroll = ScrollView(size_hint=(1,1))
        self._mscroll.add_widget(self._mbox)
        self._mscroll.opacity = 0
        main.add_widget(self._mscroll)
        # input
        ibar = BoxLayout(size_hint_y=None, height=dp(58),
                         padding=[dp(8),dp(6)], spacing=dp(6))
        with ibar.canvas.before:
            Color(0.08,0.08,0.11,1)
            self._ibg = Rectangle(pos=ibar.pos, size=ibar.size)
        ibar.bind(pos=lambda *a: setattr(self._ibg, 'pos', ibar.pos),
                  size=lambda *a: setattr(self._ibg, 'size', ibar.size))
        bimg = Button(text='IMG', font_size=sp(11), bold=True,
            size_hint=(None,None), size=(dp(42),dp(42)),
            background_normal='', background_color=MS_SURFACE, color=MS_TEXT)
        bimg.bind(on_press=lambda *a: self._pick_file())
        self._inp = TextInput(hint_text='Ecrire...', hint_text_color=MS_DIM,
            foreground_color=MS_TEXT, background_color=(0.12,0.12,0.16,1),
            cursor_color=MS_ACCENT, font_size=sp(14),
            size_hint=(1,None), height=dp(42), multiline=False,
            padding=[dp(10),dp(10)])
        self._inp.bind(on_text_validate=lambda *a: self._send())
        bsend = Button(text='>', font_size=sp(18), bold=True,
            size_hint=(None,None), size=(dp(42),dp(42)),
            background_normal='', background_color=MS_ACCENT, color=(1,1,1,1))
        bsend.bind(on_press=lambda *a: self._send())
        ibar.add_widget(bimg); ibar.add_widget(self._inp); ibar.add_widget(bsend)
        main.add_widget(ibar)
        self.add_widget(main)

    def show(self):
        self._vis = True; self.opacity = 1
        self._cid = None; self._ht.text = 'Messages'
        self._cvscroll.opacity = 1; self._mscroll.opacity = 0
        self._load_convs()
    def hide(self):
        self._vis = False; self.opacity = 0; Clock.unschedule(self._poll)
    def show_typing(self, name):
        self._ty.text = name+' ecrit...'
        Clock.schedule_once(lambda dt: setattr(self._ty, 'text', ''), 3)

    def _load_convs(self):
        self._cvbox.clear_widgets()
        self._cvbox.add_widget(Label(text='Chargement...', color=MS_DIM,
            font_size=sp(13), size_hint_y=None, height=dp(40)))
        def _f():
            import urllib.request
            try:
                r = urllib.request.urlopen(API_CONVS, timeout=6)
                d = json.loads(r.read().decode())
                Clock.schedule_once(lambda dt: self._show_convs(d), 0)
            except Exception as e:
                Clock.schedule_once(
                    lambda dt: self._show_convs({'error': str(e)}), 0)
        threading.Thread(target=_f, daemon=True).start()

    def _show_convs(self, data):
        self._cvbox.clear_widgets()
        if 'error' in data:
            self._cvbox.add_widget(Label(text='Erreur: '+data['error'],
                color=MS_RED, font_size=sp(12), size_hint_y=None, height=dp(40)))
            return
        convs = data.get('conversations', [])
        if not convs:
            self._cvbox.add_widget(Label(text='Aucune conversation',
                color=MS_DIM, font_size=sp(13), size_hint_y=None, height=dp(40)))
            return
        for c in convs: self._add_row(c)

    def _add_row(self, c):
        cid = c.get('chat_id'); cname = c.get('username','')
        prev = c.get('last_message','')
        row = BoxLayout(size_hint_y=None, height=dp(64),
                        padding=[dp(12),dp(8)], spacing=dp(10))
        def _upd(*a):
            row.canvas.before.clear()
            with row.canvas.before:
                Color(*MS_SURFACE)
                RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])
        _upd(); row.bind(pos=_upd, size=_upd)
        av = Widget(size_hint=(None,None), size=(dp(40),dp(40)))
        def _dav(*a):
            av.canvas.clear()
            with av.canvas:
                Color(*MS_ACCENT); Ellipse(pos=av.pos, size=av.size)
            l = Label(text=cname[:1].upper() if cname else '?',
                      font_size=sp(16), bold=True, color=(1,1,1,1),
                      size=av.size, pos=av.pos, halign='center', valign='middle')
            l.texture_update()
            if l.texture:
                with av.canvas:
                    Color(1,1,1,1)
                    Rectangle(texture=l.texture,
                        pos=(av.x+(av.width-l.texture.width)/2,
                             av.y+(av.height-l.texture.height)/2),
                        size=l.texture.size)
        av.bind(pos=_dav, size=_dav)
        info = BoxLayout(orientation='vertical', size_hint_x=1)
        nl = Label(text=cname, font_size=sp(14), bold=True, color=MS_TEXT,
                   halign='left', valign='middle', size_hint_y=None, height=dp(22))
        nl.bind(size=nl.setter('text_size'))
        pl = Label(text=prev[:40]+('...' if len(prev)>40 else ''),
                   font_size=sp(11), color=MS_DIM,
                   halign='left', valign='middle', size_hint_y=None, height=dp(18))
        pl.bind(size=pl.setter('text_size'))
        info.add_widget(nl); info.add_widget(pl)
        row.add_widget(av); row.add_widget(info)
        row.bind(on_touch_up=lambda w, t, ci=cid, cn=cname:
                 self._open_conv(ci, cn) if w.collide_point(*t.pos) else None)
        self._cvbox.add_widget(row)

    def _open_conv(self, cid, cname):
        self._cid = cid; self._cname = cname
        self._ht.text = cname
        self._cvscroll.opacity = 0; self._mscroll.opacity = 1
        self._mbox.clear_widgets(); self._load_msgs()
        Clock.schedule_interval(self._poll, 4)

    def _load_msgs(self):
        if not self._cid: return
        def _f():
            import urllib.request
            try:
                r = urllib.request.urlopen(
                    f"{HOME_URL}/api/messages.php?chat_id={self._cid}&limit=30",
                    timeout=6)
                d = json.loads(r.read().decode())
                Clock.schedule_once(lambda dt: self._show_msgs(d), 0)
            except: pass
        threading.Thread(target=_f, daemon=True).start()

    def _show_msgs(self, data):
        self._mbox.clear_widgets(); me = get_user()
        for m in data.get('messages', []):
            txt = m.get('message', '')
            if txt: self._add_bubble(txt, m.get('username') == me)
        Clock.schedule_once(lambda dt: setattr(self._mscroll, 'scroll_y', 0), 0.1)

    def _add_bubble(self, text, mine):
        lbl = Label(text=text, font_size=sp(13), color=MS_TEXT,
                    size_hint_y=None,
                    halign='right' if mine else 'left', valign='middle')
        lbl.text_size = (Window.width*.65, None); lbl.texture_update()
        lbl.height = lbl.texture_size[1] + dp(20)
        row = BoxLayout(size_hint_y=None, height=lbl.height+dp(10),
                        padding=[dp(6),dp(2)])
        def _upd(*a):
            row.canvas.before.clear()
            with row.canvas.before:
                Color(*(MS_BUB_OUT if mine else MS_BUB_IN))
                RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(12)])
        _upd(); row.bind(pos=_upd, size=_upd)
        if mine: row.add_widget(Widget()); row.add_widget(lbl)
        else:    row.add_widget(lbl);     row.add_widget(Widget())
        self._mbox.add_widget(row)

    def _poll(self, dt):
        if not self._vis or not self._cid:
            Clock.unschedule(self._poll); return
        self._load_msgs()

    def _send(self):
        txt = self._inp.text.strip()
        if not txt or not self._cid: return
        self._inp.text = ''
        self._add_bubble(txt, True)
        Clock.schedule_once(lambda dt: setattr(self._mscroll, 'scroll_y', 0), 0.1)
        def _f():
            import urllib.request, urllib.parse
            try:
                urllib.request.urlopen(API_SEND,
                    urllib.parse.urlencode(
                        {'chat_id': self._cid, 'message': txt}).encode(),
                    timeout=5)
            except Exception as e: _log("SEND", f"ERREUR: {e}")
        threading.Thread(target=_f, daemon=True).start()

    def _pick_file(self):
        try: open_gallery(self._on_file)
        except: pass
    def _on_file(self, uri):
        if not uri or not self._cid: return
        self.app.webview.load(f"{CHAT_URL}?chat_id={self._cid}"); self.hide()

# === CallOverlay ==============================================================

class CallOverlay(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app; self._vis = False; self.opacity = 0; self._build()
    def _build(self):
        with self.canvas.before:
            Color(0,0,0,.88)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        panel = BoxLayout(orientation='vertical',
            size_hint=(None,None), size=(dp(270),dp(280)),
            pos_hint={'center_x':.5, 'center_y':.55},
            spacing=dp(12), padding=dp(20))
        with panel.canvas.before:
            Color(0.12,0.12,0.17,1)
            self._pbg = RoundedRectangle(pos=panel.pos, size=panel.size, radius=[dp(18)])
        panel.bind(pos=lambda *a: setattr(self._pbg, 'pos', panel.pos),
                   size=lambda *a: setattr(self._pbg, 'size', panel.size))
        self._av = Label(text='?', font_size=sp(34), color=(1,1,1,1),
                         size_hint_y=None, height=dp(56), halign='center')
        self._nm = Label(text='Appel entrant', font_size=sp(17), bold=True,
                         color=MS_TEXT, size_hint_y=None, height=dp(28), halign='center')
        self._kd = Label(text='Audio', font_size=sp(12), color=MS_DIM,
                         size_hint_y=None, height=dp(20), halign='center')
        btns = BoxLayout(size_hint_y=None, height=dp(62),
                         spacing=dp(36), padding=[dp(26),0])
        bno  = Button(text='X', size_hint=(None,None), size=(dp(56),dp(56)),
                      background_normal='', background_color=MS_RED,
                      font_size=sp(20), color=(1,1,1,1), bold=True)
        byes = Button(text='OK', size_hint=(None,None), size=(dp(56),dp(56)),
                      background_normal='', background_color=MS_GREEN,
                      font_size=sp(14), color=(1,1,1,1), bold=True)
        bno.bind(on_press=lambda *a: self.decline())
        byes.bind(on_press=lambda *a: self.accept())
        btns.add_widget(bno); btns.add_widget(byes)
        for w in (self._av, self._nm, self._kd, btns): panel.add_widget(w)
        self.add_widget(panel); self._url = ''
    def show(self, caller, kind='audio', url=''):
        self._url = url; self._vis = True; self.opacity = 1
        self._av.text = caller[:1].upper() if caller else '?'
        self._nm.text = caller
        self._kd.text = 'Video' if kind == 'video' else 'Audio'
        push_notif(f'Appel de {caller}', 'Repondre', 102, CHANNEL_CALL)
        play_sound(ring=True); vibrate(600)
    def accept(self):
        self._vis = False; self.opacity = 0
        if self._url: self.app.webview.load(self._url)
    def decline(self):
        self._vis = False; self.opacity = 0
        self.app.webview.run_js(
            "if(window.__activePeerCall)window.__activePeerCall.close();")

# === AccountPanel =============================================================

class AccountPanel(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app; self._vis = False; self.opacity = 0
        self.size_hint = (None,None); self.size = (dp(230),dp(220))
        self._build()
    def _build(self):
        with self.canvas.before:
            Color(0.13,0.13,0.17,.97)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        lay = BoxLayout(orientation='vertical', padding=dp(14),
                        spacing=dp(8), size_hint=(1,1))
        self._ul = Label(text='Non connecte', font_size=sp(13), color=MS_DIM,
                         size_hint_y=None, height=dp(22), halign='center')
        lay.add_widget(self._ul)
        self._bl = self._btn('Se connecter', MS_ACCENT, self.app.do_login)
        self._bp = self._btn('Mon profil', (0.15,0.15,0.2,1), self.app.open_profile)
        self._bo = self._btn('Deconnexion', (0.3,0.1,0.1,1), self.app.do_logout)
        self._bp.opacity = 0; self._bp.disabled = True
        self._bo.opacity = 0; self._bo.disabled = True
        bc = Button(text='Fermer', size_hint_y=None, height=dp(32),
                    background_normal='', background_color=(0,0,0,0),
                    color=MS_DIM, font_size=sp(12))
        bc.bind(on_press=lambda *a: self.hide())
        for w in (self._ul, self._bl, self._bp, self._bo, bc, Widget()):
            lay.add_widget(w)
        self.add_widget(lay)
    def _btn(self, t, c, fn):
        b = Button(text=t, size_hint_y=None, height=dp(40),
                   background_normal='', background_color=c,
                   color=(1,1,1,1), font_size=sp(13))
        b.bind(on_press=lambda *a: (fn(), self.hide())); return b
    def refresh(self):
        ok = is_logged()
        self._ul.text  = get_user() if ok else 'Non connecte'
        self._ul.color = MS_TEXT if ok else MS_DIM
        self._bl.opacity = 0 if ok else 1; self._bl.disabled = ok
        self._bp.opacity = 1 if ok else 0; self._bp.disabled = not ok
        self._bo.opacity = 1 if ok else 0; self._bo.disabled = not ok
    def show(self): self.refresh(); self._vis = True; self.opacity = 1
    def hide(self): self._vis = False; self.opacity = 0
    def toggle(self):
        if self._vis: self.hide()
        else: self.show()

# === Root =====================================================================

class Root(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw); self.app = app
        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        self.wv = MSWebView(size_hint=(1,1), pos_hint={'x':0,'y':0})
        self.wv.on_title = self._on_title
        self.wv.on_url   = self._on_url
        self.add_widget(self.wv)
        self.tb  = Toolbar(app, size_hint=(1,None), pos_hint={'x':0,'top':1})
        self.add_widget(self.tb)
        self.nav = BottomNav(app, size_hint=(1,None), pos_hint={'x':0,'y':0})
        self.add_widget(self.nav)
        self.compose  = ComposePage(app, size_hint=(1,1), pos_hint={'x':0,'y':0})
        self.add_widget(self.compose)
        self.call_ov  = CallOverlay(app, size_hint=(1,1))
        self.add_widget(self.call_ov)
        self.acc = AccountPanel(app)
        self.add_widget(self.acc)
        Clock.schedule_once(self._adj, 0.3)
        self.tb.bind(height=self._adj)
        self.nav.bind(height=self._adj)
    def _adj(self, *a):
        th = self.tb.height; nh = self.nav.height; h = self.height-th-nh
        if h > 0:
            self.wv.size_hint = (1,None); self.wv.height = h; self.wv.y = nh
            self.compose.size_hint = (1,None)
            self.compose.height = h; self.compose.y = nh
    def on_size(self, *a): self._adj(); self._pp()
    def _pp(self):
        self.acc.pos = (self.width-self.acc.width-dp(8),
                        self.height-self.tb.height-self.acc.height-dp(4))
    def _on_title(self, title):
        try:
            if title.startswith('__U:'):
                name = title[4:].strip()
                if name and not is_logged():
                    save_account(name, get_token())
                    Clock.schedule_once(lambda dt: self.app._after_login(name), 0)
            elif title.startswith('__CALL__:'):
                parts = title.split(':')
                caller = parts[1] if len(parts)>1 else 'Inconnu'
                kind   = parts[2] if len(parts)>2 else 'audio'
                url    = parts[3] if len(parts)>3 else ''
                Clock.schedule_once(
                    lambda dt: self.call_ov.show(caller, kind, url), 0)
            elif title.startswith('__TYPING__:'):
                name = title[11:].strip()
                Clock.schedule_once(lambda dt: self._typing(name), 0)
            else:
                self.tb.set_title(title)
        except Exception as e:
            _log("ROOT", f"_on_title error: {e}")
    def _on_url(self, url):
        try:
            self.tb.set_back(self.wv.can_back)
            self.nav.set_by_url(url)
        except Exception as e:
            _log("ROOT", f"_on_url error: {e}")
    def _typing(self, name):
        self.tb.show_typing(name)
        if self.compose._vis: self.compose.show_typing(name)

# === Poller ===================================================================

class Poller:
    def __init__(self, app):
        self.app = app; self._run = False; self._lm = 0; self._ln = 0
    def start(self):
        if self._run: return
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()
    def stop(self): self._run = False
    def _loop(self):
        import urllib.request
        while self._run:
            if is_logged():
                for url, attr, key, nid, title in [
                    (API_MSGS,   '_lm', 'chat',   101, 'MoodSync Messages'),
                    (API_NOTIFS, '_ln', 'notifs', 103, 'MoodSync'),
                ]:
                    try:
                        r = urllib.request.urlopen(url, timeout=5)
                        n = int(json.loads(r.read().decode()).get('count', 0))
                        if n != getattr(self, attr):
                            setattr(self, attr, n)
                            Clock.schedule_once(
                                lambda dt, k=key, c=n: self.app.set_badge(k, c), 0)
                            if n > 0:
                                body = (f'{n} message(s)' if key=='chat'
                                        else f'{n} notification(s)')
                                Clock.schedule_once(
                                    lambda dt, t=title, b=body, i=nid:
                                    (push_notif(t, b, i),
                                     play_sound(),
                                     vibrate(180)), 0)
                    except: pass
            time.sleep(15)

# === App ======================================================================

BRIDGE_JS = """(function(){
  if(window.__ms_bridge)return;window.__ms_bridge=true;
  var _P=window.Peer;
  if(_P){var _on=_P.prototype.on;_P.prototype.on=function(ev,cb){
    if(ev==='call'){return _on.call(this,ev,function(call){
      window.__activePeerCall=call;
      document.title='__CALL__:'+(call.metadata&&call.metadata.from_name||call.peer)+
        ':'+(call.metadata&&call.metadata.video?'video':'audio')+':'+window.location.href;
      cb(call);});}
    return _on.call(this,ev,cb);
  };}
})();"""

def _register_fcm():
    def _f():
        import urllib.request, urllib.parse
        try:
            urllib.request.urlopen(API_FCM_REG,
                urllib.parse.urlencode({
                    'token': get_token(),
                    'username': get_user(),
                    'platform': 'android'
                }).encode(), timeout=5)
        except Exception as e: _log("FCM_REG", f"ERREUR: {e}")
    threading.Thread(target=_f, daemon=True).start()


class MoodSyncApp(App):
    def build(self):
        _log("APP", "build() start")
        Window.clearcolor = MS_BG
        if platform == 'android':
            Window.fullscreen = True
        try: create_channels()
        except Exception as e: _log("APP", f"channels: {e}")
        _log("APP", "creating Root...")
        self.layout = Root(self)
        _log("APP", "creating Poller...")
        self.poller = Poller(self)
        _log("APP", "getting FCM token...")
        try: get_fcm_token_android(self._on_fcm)
        except Exception as e: _log("APP", f"fcm_init: {e}")
        if is_logged():
            _log("APP", f"already logged as {get_user()}, starting poller")
            self.poller.start()
            self.layout.tb.update_av()
        Clock.schedule_interval(self._detect_login, 5)
        Clock.schedule_interval(self._inject_bridge, 10)
        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_key_down=self._key_down)
                _log("APP", "key handler OK")
            except Exception as e: _log("APP", f"key_bind: {e}")
        _log("APP", "build() done")
        return self.layout

    @property
    def webview(self): return self.layout.wv
    def go_back(self):
        if self.layout.compose._vis: self.layout.compose.hide()
        else: self.layout.wv.back()
    def reload_page(self):    self.layout.wv.reload()
    def set_badge(self, k, n): self.layout.nav.set_badge(k, n)
    def show_compose(self):   self.layout.compose.show()
    def do_login(self):       self.layout.wv.load(LOGIN_URL)
    def open_profile(self):   self.layout.wv.load(PROFILE_URL)
    def toggle_account(self): self.layout._pp(); self.layout.acc.toggle()
    def do_logout(self):
        clear_account(); self.layout.tb.update_av(); self.poller.stop()
        self.layout.wv.clear_cookies(); self.layout.wv.load(LOGIN_URL)
    def _after_login(self, name):
        _log("APP", f"logged in as {name}")
        self.layout.tb.update_av(); self.layout.acc.refresh()
        self.poller.start()
        if get_token(): _register_fcm()
    def _on_fcm(self, token):
        try:
            if not token: return
            save_token(token)
            if is_logged(): _register_fcm()
        except Exception as e:
            _log("APP", f"_on_fcm error: {e}")
    def _detect_login(self, dt):
        url = self.layout.wv.current_url
        if 'moodsync' not in url and 'alwaysdata' not in url: return
        self.layout.wv.run_js(
            "(function(){var m=document.querySelector('meta[name=\"username\"]');"
            "if(m&&m.content){document.title='__U:'+m.content;return;}"
            "var d=document.querySelector('[data-username]');"
            "if(d)document.title='__U:'+d.getAttribute('data-username');})()")
    def _inject_bridge(self, dt):
        url = self.layout.wv.current_url
        if 'moodsync' in url or 'alwaysdata' in url:
            self.layout.wv.run_js(BRIDGE_JS)
    def _key_down(self, keycode, *a):
        if keycode == 27:
            if self.layout.call_ov._vis: self.layout.call_ov.decline(); return True
            if self.layout.acc._vis: self.layout.acc.hide(); return True
            if self.layout.compose._vis: self.layout.compose.hide(); return True
            if self.layout.wv.can_back: self.layout.wv.back(); return True
        return False
    def on_stop(self):
        _log("APP", "on_stop")
        self.poller.stop()


_log("APP", "MoodSyncApp defined, calling run()...")

if __name__ == '__main__':
    try:
        MoodSyncApp().run()
    except Exception as e:
        _log("FATAL", f"{e}\n{traceback.format_exc()}")
        raise
