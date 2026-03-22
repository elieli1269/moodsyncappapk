[app]
title           = MoodSync
package.name    = moodsync
package.domain  = net.alwaysdata
source.dir      = .
source.include_exts = py,png,jpg,json,kv,ttf
version         = 1.0
source.main     = main.py

requirements = python3,kivy==2.3.1,android,pyjnius

android.permissions = \
    INTERNET,\
    ACCESS_NETWORK_STATE,\
    ACCESS_WIFI_STATE,\
    CAMERA,\
    RECORD_AUDIO,\
    MODIFY_AUDIO_SETTINGS,\
    VIBRATE,\
    WAKE_LOCK

android.api             = 34
android.minapi          = 21
android.ndk             = 25b
android.ndk_api         = 21
android.sdk             = 34
android.accept_sdk_license = True
android.archs           = arm64-v8a, armeabi-v7a

android.entrypoint  = org.kivy.android.PythonActivity
android.apptheme    = @android:style/Theme.NoTitleBar
orientation         = portrait
presplash.color     = #161619

p4a.branch = develop

[buildozer]
log_level    = 2
warn_on_root = 1