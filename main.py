#!/usr/bin/env python3
"""MoodSync Browser — WebView simple"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty

HOME_URL  = "https://moodsync.alwaysdata.net"
LOGIN_URL = HOME_URL + "/login.php"

MS_BG   = (0.086, 0.086, 0.102, 1)
MS_TOOL = (0.090, 0.090, 0.118, 1)
MS_TEXT = (0.910, 0.902, 0.941, 1)
MS_DIM  = (0.533, 0.502, 0.627, 1)

# ── WebView Android ───────────────────────────────────────────────────────────

if platform == "android":
    try:
        from android.runnable import run_on_ui_thread
        from jnius import autoclass

        PythonActivity  = autoclass("org.kivy.android.PythonActivity")
        WebView         = autoclass("android.webkit.WebView")
        WebViewClient   = autoclass("android.webkit.WebViewClient")
        WebChromeClient = autoclass("android.webkit.WebChromeClient")
        CookieManager   = autoclass("android.webkit.CookieManager")
        LayoutParams    = autoclass("android.view.ViewGroup$LayoutParams")
        Color_java      = autoclass("android.graphics.Color")

        class SimpleClient(WebViewClient):
            def __init__(self, w):
                super().__init__()
                self._w = w
            def onPageFinished(self, wv, url):
                self._w.current_url = url or ""
                self._w.can_back = wv.canGoBack()
            def shouldOverrideUrlLoading(self, wv, url):
                return False

        class MSWebView(Widget):
            current_url = StringProperty("")
            can_back    = BooleanProperty(False)

            def __init__(self, **kw):
                super().__init__(**kw)
                self._wv = None
                Clock.schedule_once(self._create, 0)
                self.bind(pos=self._upd, size=self._upd)

            @run_on_ui_thread
            def _create(self, *a):
                act = PythonActivity.mActivity
                CookieManager.getInstance().setAcceptCookie(True)
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
                s.setUserAgentString(
                    s.getUserAgentString() + " MoodSyncBrowser/1.0")
                self._wv.setWebViewClient(SimpleClient(self))
                self._wv.setWebChromeClient(WebChromeClient())
                self._wv.setBackgroundColor(Color_java.parseColor("#161619"))
                act.addContentView(self._wv,
                    LayoutParams(LayoutParams.MATCH_PARENT,
                                 LayoutParams.MATCH_PARENT))
                self._wv.loadUrl(HOME_URL)
                Clock.schedule_once(self._upd, 0.2)

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
            def back(self):
                if self._wv and self._wv.canGoBack():
                    self._wv.goBack()

            @run_on_ui_thread
            def reload(self):
                if self._wv: self._wv.reload()

    except Exception as e:
        print("Android error:", e)

        class MSWebView(Widget):
            current_url = StringProperty("")
            can_back    = BooleanProperty(False)
            def load(self, url): pass
            def back(self): pass
            def reload(self): pass

else:
    class MSWebView(Widget):
        current_url = StringProperty("")
        can_back    = BooleanProperty(False)
        def load(self, url): pass
        def back(self): pass
        def reload(self): pass

# ── Toolbar ───────────────────────────────────────────────────────────────────

class Toolbar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.app = app
        self.size_hint_y = None
        self.height = dp(52)
        with self.canvas.before:
            Color(*MS_TOOL)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        inner = BoxLayout(padding=[dp(10),dp(7),dp(10),dp(7)], spacing=dp(6))

        self.btn_back = Button(
            text='<', font_size=sp(20), bold=True,
            size_hint=(None,None), size=(dp(40),dp(38)),
            background_normal='', background_color=(0,0,0,0),
            color=MS_DIM)
        self.btn_back.bind(on_press=lambda *a: self.app.go_back())

        self.title = Label(
            text='MoodSync', font_size=sp(16), bold=True,
            color=MS_TEXT, size_hint_x=1,
            halign='left', valign='middle')
        self.title.bind(size=self.title.setter('text_size'))

        self.btn_home = Button(
            text='H', font_size=sp(14), bold=True,
            size_hint=(None,None), size=(dp(40),dp(38)),
            background_normal='', background_color=(0,0,0,0),
            color=MS_DIM)
        self.btn_home.bind(on_press=lambda *a: self.app.go_home())

        self.btn_rel = Button(
            text='R', font_size=sp(16), bold=True,
            size_hint=(None,None), size=(dp(40),dp(38)),
            background_normal='', background_color=(0,0,0,0),
            color=MS_DIM)
        self.btn_rel.bind(on_press=lambda *a: self.app.reload_page())

        inner.add_widget(self.btn_back)
        inner.add_widget(self.title)
        inner.add_widget(self.btn_home)
        inner.add_widget(self.btn_rel)
        self.add_widget(inner)

    def set_title(self, t):
        self.title.text = t[:28]+('...' if len(t)>28 else '')
    def set_back(self, v):
        self.btn_back.color = MS_TEXT if v else MS_DIM

# ── Root ──────────────────────────────────────────────────────────────────────

class Root(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

        self.wv = MSWebView(size_hint=(1,1), pos_hint={'x':0,'y':0})
        self.add_widget(self.wv)

        self.tb = Toolbar(app, size_hint=(1,None), pos_hint={'x':0,'top':1})
        self.add_widget(self.tb)

        Clock.schedule_once(self._adj, 0.3)
        self.tb.bind(height=self._adj)

    def _adj(self, *a):
        th = self.tb.height
        h  = self.height - th
        if h > 0:
            self.wv.size_hint = (1,None)
            self.wv.height    = h
            self.wv.y         = 0

    def on_size(self, *a):
        self._adj()

# ── App ───────────────────────────────────────────────────────────────────────

class MoodSyncApp(App):
    def build(self):
        Window.clearcolor = MS_BG
        if platform == 'android':
            Window.fullscreen = True

        self.layout = Root(self)

        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_key_down=self._key_down)
            except Exception as e:
                print("key bind:", e)

        return self.layout

    @property
    def webview(self): return self.layout.wv

    def go_back(self):    self.layout.wv.back()
    def go_home(self):    self.layout.wv.load(HOME_URL)
    def reload_page(self):self.layout.wv.reload()

    def _key_down(self, keycode, *a):
        if keycode == 27:
            if self.layout.wv.can_back:
                self.layout.wv.back()
                return True
        return False


if __name__ == '__main__':
    MoodSyncApp().run()
