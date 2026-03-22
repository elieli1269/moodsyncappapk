#!/usr/bin/env python3
"""MoodSync Browser v6"""

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import BooleanProperty

HOME_URL = "https://moodsync.alwaysdata.net"
MS_BG   = (0.086, 0.086, 0.102, 1)
MS_TOOL = (0.090, 0.090, 0.118, 1)
MS_TEXT = (0.910, 0.902, 0.941, 1)
MS_DIM  = (0.533, 0.502, 0.627, 1)

if platform == "android":
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    PA   = autoclass("org.kivy.android.PythonActivity")
    WV   = autoclass("android.webkit.WebView")
    WVC  = autoclass("android.webkit.WebViewClient")
    WCC  = autoclass("android.webkit.WebChromeClient")
    CM   = autoclass("android.webkit.CookieManager")
    LP   = autoclass("android.view.ViewGroup$LayoutParams")
    CJ   = autoclass("android.graphics.Color")
    DM   = autoclass("android.util.DisplayMetrics")

    def get_screen_size():
        """Taille réelle de l'écran en pixels Android."""
        act = PA.mActivity
        dm  = DM()
        act.getWindowManager().getDefaultDisplay().getMetrics(dm)
        return int(dm.widthPixels), int(dm.heightPixels)

    def get_toolbar_px():
        """Hauteur toolbar en pixels Android réels."""
        act  = PA.mActivity
        dm   = DM()
        act.getWindowManager().getDefaultDisplay().getMetrics(dm)
        return int(56 * dm.density)  # 56dp en pixels

    class _Client(WVC):
        def __init__(self, cb):
            super().__init__()
            self._cb = cb
        def onPageFinished(self, wv, url):
            Clock.schedule_once(
                lambda dt: self._cb(url, wv.canGoBack()), 0)
        def shouldOverrideUrlLoading(self, wv, url):
            return False

    class AndroidWV:
        def __init__(self, on_page_cb):
            self._cb  = on_page_cb
            self._wv  = None
            Clock.schedule_once(self._create, 0)

        @run_on_ui_thread
        def _create(self, *a):
            act = PA.mActivity
            CM.getInstance().setAcceptCookie(True)
            self._wv = WV(act)
            s = self._wv.getSettings()
            s.setJavaScriptEnabled(True)
            s.setDomStorageEnabled(True)
            s.setLoadWithOverviewMode(True)
            s.setUseWideViewPort(True)
            s.setBuiltInZoomControls(True)
            s.setDisplayZoomControls(False)
            s.setMediaPlaybackRequiresUserGesture(False)
            s.setMixedContentMode(0)
            s.setAllowFileAccess(True)
            s.setUserAgentString(
                s.getUserAgentString() + " MoodSyncApp/1.0")
            self._wv.setWebViewClient(_Client(self._cb))
            self._wv.setWebChromeClient(WCC())
            self._wv.setBackgroundColor(CJ.parseColor("#161619"))
            # Ajouter FULL SCREEN d'abord
            act.addContentView(
                self._wv, LP(LP.MATCH_PARENT, LP.MATCH_PARENT))
            # Positionner + charger après 1s
            Clock.schedule_once(self._place, 1.0)

        @run_on_ui_thread
        def _place(self, *a):
            if not self._wv: return
            sw, sh = get_screen_size()
            th = get_toolbar_px()
            # WebView sous la toolbar
            self._wv.setX(0)
            self._wv.setY(th)
            lp = self._wv.getLayoutParams()
            lp.width  = sw
            lp.height = sh - th
            self._wv.setLayoutParams(lp)
            self._wv.requestLayout()
            self._wv.loadUrl(HOME_URL)

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

else:
    class AndroidWV:
        def __init__(self, cb): pass
        def load(self, url): pass
        def back(self): pass
        def reload(self): pass

# ── Toolbar ───────────────────────────────────────────────────────────────────

class Toolbar(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.app = app
        self.size_hint_y = None
        self.height = dp(56)
        with self.canvas.before:
            Color(*MS_TOOL)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos',  self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        inner = BoxLayout(
            padding=[dp(10), dp(8), dp(10), dp(8)], spacing=dp(6))
        self.btn_back = Button(
            text='<', font_size=sp(22), bold=True,
            size_hint=(None, None), size=(dp(44), dp(40)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_back.bind(on_press=lambda *a: app.go_back())
        self.lbl = Label(
            text='MoodSync', font_size=sp(16), bold=True,
            color=MS_TEXT, size_hint_x=1, halign='left', valign='middle')
        self.lbl.bind(size=self.lbl.setter('text_size'))
        self.btn_home = Button(
            text='H', font_size=sp(16), bold=True,
            size_hint=(None, None), size=(dp(44), dp(40)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_home.bind(on_press=lambda *a: app.go_home())
        self.btn_r = Button(
            text='R', font_size=sp(18), bold=True,
            size_hint=(None, None), size=(dp(44), dp(40)),
            background_normal='', background_color=(0,0,0,0), color=MS_DIM)
        self.btn_r.bind(on_press=lambda *a: app.do_reload())
        inner.add_widget(self.btn_back)
        inner.add_widget(self.lbl)
        inner.add_widget(self.btn_home)
        inner.add_widget(self.btn_r)
        self.add_widget(inner)

    def set_back(self, v):
        self.btn_back.color = MS_TEXT if v else MS_DIM
    def set_title(self, t):
        self.lbl.text = t[:28]+('...' if len(t)>28 else '')

# ── Root ──────────────────────────────────────────────────────────────────────

class Root(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*MS_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg,'pos',self.pos),
                  size=lambda *a: setattr(self._bg,'size',self.size))

# ── App ───────────────────────────────────────────────────────────────────────

class MoodSyncApp(App):
    def build(self):
        Window.clearcolor = MS_BG
        if platform == 'android':
            Window.fullscreen = True

        self._can_back = False
        self.root_w    = Root()

        self.tb = Toolbar(self, size_hint=(1, None),
                          pos_hint={'x': 0, 'top': 1})
        self.root_w.add_widget(self.tb)

        self._wv = AndroidWV(self._on_page)

        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_key_down=self._key_down)
            except: pass

        return self.root_w

    def _on_page(self, url, can_back):
        self._can_back = can_back
        self.tb.set_back(can_back)
        try:
            from urllib.parse import urlparse
            p = urlparse(url).path.strip('/').split('/')[-1]
            t = p.replace('.php','').replace('_',' ').capitalize() or 'MoodSync'
            self.tb.set_title(t)
        except:
            self.tb.set_title('MoodSync')

    def go_back(self):    self._wv.back()
    def go_home(self):    self._wv.load(HOME_URL)
    def do_reload(self):  self._wv.reload()

    def _key_down(self, keycode, *a):
        if keycode == 27 and self._can_back:
            self.go_back(); return True
        return False


if __name__ == '__main__':
    MoodSyncApp().run()
