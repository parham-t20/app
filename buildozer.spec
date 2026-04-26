[app]
title = Action Notch
package.name = actionnotch
package.domain = org.actionnotch
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 2.1.0
requirements = python3,kivy==2.2.1,pyjnius,android
android.permissions = SYSTEM_ALERT_WINDOW,RECEIVE_BOOT_COMPLETED,FOREGROUND_SERVICE,VIBRATE,CAMERA,FLASHLIGHT,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_CONTACTS,CALL_PHONE,CHANGE_WIFI_STATE,ACCESS_WIFI_STATE,BLUETOOTH,BLUETOOTH_ADMIN,MODIFY_AUDIO_SETTINGS,INTERNET,ACCESS_NETWORK_STATE,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,WAKE_LOCK
android.api = 33
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
orientation = portrait
fullscreen = 0
android.accept_sdk_license = True
android.wakelock = True
services = Actionnotchservice:main.py:foreground:sticky
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
