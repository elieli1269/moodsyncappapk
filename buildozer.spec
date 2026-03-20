[app]
title           = MoodSync
package.name    = moodsync
package.domain  = net.alwaysdata.moodsync
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
    WAKE_LOCK,\
    POST_NOTIFICATIONS,\
    READ_EXTERNAL_STORAGE,\
    WRITE_EXTERNAL_STORAGE

android.api             = 34
android.minapi          = 26
android.ndk             = 25b
android.ndk_api         = 26
android.sdk             = 34
android.accept_sdk_license = True
android.archs           = arm64-v8a, armeabi-v7a

android.gradle_dependencies = \
    com.google.firebase:firebase-messaging:23.1.2,\
    androidx.core:core:1.9.0

android.gradle_plugins = com.google.gms:google-services:4.3.15

android.entrypoint  = org.kivy.android.PythonActivity
android.apptheme    = @android:style/Theme.NoTitleBar.Fullscreen
orientation         = portrait
presplash.color     = #161619

android.meta_data = \
    com.google.firebase.messaging.default_notification_channel_id=moodsync_channel

p4a.branch = develop

[buildozer]
log_level    = 2
warn_on_root = 1