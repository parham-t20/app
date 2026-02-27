[app]
title = Video Downloader
package.name = videodownloader
package.domain = org.mydomain
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,xml
source.exclude_exts = spec
version = 1.0.0
requirements = python3,kivy==2.2.1,android,yt-dlp,certifi,brotli,mutagen,pycryptodomex,websockets,urllib3,charset-normalizer,idna,requests
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.skip_update = False
android.accept_sdk_license = True
android.enable_androidx = True
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.private_storage = True
fullscreen = 0
orientation = portrait
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
