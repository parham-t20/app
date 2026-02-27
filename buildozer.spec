[app]

# (str) عنوان برنامه
title = Video Downloader

# (str) نام پکیج
package.name = videodownloader

# (str) دامنه پکیج (منحصر به فرد)
package.domain = org.mydomain

# (str) دایرکتوری کد منبع
source.dir = .

# (list) الگوی فایل‌های منبع
source.include_exts = py,png,jpg,kv,atlas,ttf

# (list) فایل‌هایی که باید exclude شوند
source.exclude_exts = spec

# (str) نسخه برنامه
version = 1.0.0

# (list) نیازمندی‌های برنامه
# فقط پکیج‌های ضروری را اضافه کنید
requirements = python3,kivy==2.2.1,android,yt-dlp,certifi,brotli,mutagen,pycryptodomex,websockets,urllib3,charset-normalizer,idna,requests

# (str) آیکون برنامه (اختیاری)
#icon.filename = %(source.dir)s/data/icon.png

# (str) تصویر Splash (اختیاری)
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) رنگ پس‌زمینه Presplash
#presplash.color = #FFFFFF

# (list) مجوزهای اندروید
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE,MANAGE_EXTERNAL_STORAGE

# (bool) نمایش اطلاعیه کپی‌رایت
android.skip_update = False

# (int) Target API level
android.api = 33

# (int) Minimum API level
android.minapi = 21

# (int) Android SDK version
android.sdk = 33

# (str) Android NDK version
android.ndk = 25b

# (bool) Use --private data storage
android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
android.skip_update = False

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (str) Android entry point
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class
#android.activity_class_name = org.kivy.android.PythonActivity

# (str) Extra xml to write directly inside the <manifest> element
#android.extra_manifest_xml = 

# (str) Extra xml to write directly inside the <application> element
android.extra_manifest_application_xml = %(source.dir)s/extra_manifest.xml

# (list) Pattern to whitelist for the whole project
#android.whitelist =

# (str) Path to a custom whitelist file
#android.whitelist_src =

# (str) Path to a custom blacklist file
#android.blacklist_src =

# (list) List of Java .jar files to add to the libs
#android.add_jars = foo.jar,bar.jar,path/to/more/*.jar

# (list) List of Java files to add to the APK
#android.add_src =

# (list) Android AAR archives to add
#android.add_aars =

# (list) Put these files or directories in the apk assets directory
#android.add_assets =

# (list) Put these files or directories in the apk res directory
#android.add_resources =

# (list) Gradle dependencies to add
#android.gradle_dependencies =

# (bool) Enable AndroidX support
android.enable_androidx = True

# (list) Android application meta-data to set
#android.meta_data =

# (list) Android library project to add (will be added in the automatically)
#android.library_references =

# (list) Android shared libraries
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# (str) python-for-android branch to use
#p4a.branch = master

# (str) python-for-android git clone directory
#p4a.source_dir =

# (str) The directory in which python-for-android should look for your own build recipes
#p4a.local_recipes =

# (str) Filename to the hook for p4a
#p4a.hook =

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument
#p4a.port =

# (bool) Use --private data storage
#android.private_storage = True

# (str) Argument to pass to the build
#p4a.extra_args =

# (str) XML file for additional android manifest entries
#android.manifest.intent_filters =

# (str) launchMode to set for the main activity
#android.manifest.launch_mode = standard

# (list) Permissions to request at runtime (Android 6.0+)
android.runtime_permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (list) Architectures to build for
android.archs = arm64-v8a,armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode (aab or apk)
# android.release_artifact = aab

# (str) The format used to package the app for debug mode (apk or aab)
# android.debug_artifact = apk

#
# Python for android (p4a) specific
#

# (str) python-for-android URL to use for checkout
#p4a.url =

# (str) python-for-android fork to use
#p4a.fork = kivy

# (str) python-for-android branch to use
#p4a.branch = develop

# (str) python-for-android specific commit to use
#p4a.commit = HEAD

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
#p4a.source_dir =

# (str) The directory in which python-for-android should look for your own build recipes (if any)
#p4a.local_recipes =

# (str) Filename to the hook for p4a
#p4a.hook =

# (str) Bootstrap to use for android builds
# p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument (eg for bootstrap flask)
#p4a.port =

# Control passing the --use-setup-py vs --ignore-setup-py to p4a
# "in the future" --use-setup-py is going to be the default behaviour in p4a, right now it is not
# Setting this to false will pass --ignore-setup-py, true will pass --use-setup-py
# NOTE: this is general setuptools integration, having pyproject.toml is enough, no need to generate
# setup.py if you're using Poetry, but you need to add "toml" to source.include_exts.
#p4a.setup_py = false

# (str) extra arguments to pass to p4a (eg: --node-recipe)
#p4a.extra_args =


#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
#ios.kivy_ios_dir = ../kivy-ios

# (str) Name of the certificate to use for signing the debug version
#ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) Name of the certificate to use for signing the release version
#ios.codesign.release = %(ios.codesign.debug)s


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin

#    -----------------------------------------------------------------------------
#    List as sections
#
#    You can define all the "list" as [section:key].
#    Each line will be considered as a option to the list.
#    Let's take [app] / source.exclude_patterns.
#    Instead of doing:
#
#[app]
#source.exclude_patterns = license,data/audio/*.wav,data/images/original/*
#
#    This can be translated into:
#
#[app:source.exclude_patterns]
#license
#data/audio/*.wav
#data/images/original/*
#

#    -----------------------------------------------------------------------------
#    Profiles
#
#    You can extend section / key with a profile
#    For example, you want to deploy a demo version of your application without
#    HD content. You could first change the title to add "(demo)" in the name
#    and extend the excluded directories to remove the HD content.
#
#[app@demo]
#title = My Application (demo)
#
#[app:source.exclude_patterns@demo]
#images/hd/*
#
#    Then, invoke the command line with the "demo" profile:
#
#buildozer --profile demo android debug
