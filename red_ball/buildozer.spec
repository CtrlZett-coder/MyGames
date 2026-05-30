[app]

title = Red Ball
package.name = redball
package.domain = com.ctrlzett
source.dir = .
source.include_exts = py,json,png,jpg,wav,ogg
version = 1.0

requirements = python3,pygame

orientation = landscape
fullscreen = 1

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.build_tools_version = 33.0.0
android.accept_sdk_license = True

android.permissions = VIBRATE

[buildozer]
log_level = 2
warn_on_root = 0
