[app]

# ─── اطلاعات اصلی برنامه ─────────────────────────────────────
title           = NOVA Music Player
package.name    = novamusicplayer
package.domain  = org.nova

# نام فایل اصلی (بدون پسوند .py)
source.main      = music_player

# پوشه سورس (نقطه = همین دایرکتوری)
source.dir       = .

# پسوندهایی که باید در APK قرار بگیرند
source.include_exts = py,png,jpg,kv,atlas,json,mp3,wav,ogg,flac,m4a,aac,ttf,otf

# پسوندهایی که باید نادیده گرفته شوند
source.exclude_exts = spec,pyc,pyo,__pycache__

# پوشه‌هایی که باید نادیده گرفته شوند
source.exclude_dirs = tests,bin,venv,.venv,.git,__pycache__

# ─── نسخه برنامه ─────────────────────────────────────────────
version         = 1.0.0

# ─── نیازمندی‌های پایتون ──────────────────────────────────────
# همه کتابخانه‌های مورد نیاز پروژه
requirements    = python3,\
                  kivy==2.3.0,\
                  pygame,\
                  mutagen,\
                  kivymd,\
                  android,\
                  pyjnius,\
                  pillow

# ─── تنظیمات پنجره / صفحه ────────────────────────────────────
orientation     = portrait
fullscreen       = 0

# ─── آیکون و splash screen ───────────────────────────────────
# اگر فایل icon.png دارید، مسیر آن را اینجا بنویسید
# icon.filename = %(source.dir)s/icon.png

# اگر فایل presplash.png دارید:
# presplash.filename = %(source.dir)s/presplash.png

# رنگ پس‌زمینه splash (همان C_BG تم NOVA)
presplash.color = #0F0F17

# ─── مجوزهای اندروید ─────────────────────────────────────────
android.permissions = android.permission.READ_EXTERNAL_STORAGE,\
                      android.permission.WRITE_EXTERNAL_STORAGE,\
                      android.permission.READ_MEDIA_AUDIO,\
                      android.permission.INTERNET,\
                      android.permission.FOREGROUND_SERVICE

# ─── API و SDK اندروید ───────────────────────────────────────
android.minapi  = 21
android.api     = 33
android.ndk     = 25b
android.sdk     = 33

# اگر NDK و SDK از قبل نصب‌اند، مسیر را uncomment کنید:
# android.ndk_path = /path/to/android-ndk
# android.sdk_path = /path/to/android-sdk

# NDK API (باید >= minapi باشد)
android.ndk_api = 21

# آرکیتکچرها: arm64-v8a برای دستگاه‌های مدرن، armeabi-v7a برای قدیمی
android.archs   = arm64-v8a, armeabi-v7a

# ─── تنظیمات Gradle / Build ──────────────────────────────────
android.gradle_dependencies = com.google.android.material:material:1.9.0

# نسخه tools اندروید
android.build_tools_version = 33.0.0

# AAB به جای APK (برای Google Play توصیه می‌شود - برای تست False بگذارید)
android.release_artifact = apk

# امکان private data storage
android.private_storage = True

# accept-sdk-licenses
android.accept_sdk_license = True

# ─── تنظیمات p4a (python-for-android) ───────────────────────
p4a.branch      = master
p4a.local_recipes =

# اگر نسخه خاصی از p4a می‌خواهید:
# p4a.branch = releases/2024.01.21

# Bootstrap پیش‌فرض برای Kivy
p4a.bootstrap   = sdl2

# ─── تنظیمات iOS (در صورت نیاز) ─────────────────────────────
# ios.kivy_ios_url = https://github.com/kivy/kivy-ios
# ios.kivy_ios_branch = master
# ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
# ios.ios_deploy_branch = 1.10.0

# ─── تنظیمات buildozer ───────────────────────────────────────
[buildozer]

# سطح log: 0=error  1=info  2=debug
log_level       = 2

# warn اگر buildozer با root اجرا شود
warn_on_root    = 1

# مسیر کش دانلود SDK/NDK
# build_dir = ./.buildozer
# bin_dir   = ./bin
