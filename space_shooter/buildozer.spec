[app]

title = Space Shooter
package.name = spaceshooter
package.domain = com.ctrlzett
source.dir = .
source.include_exts = py,json,png,jpg,wav,ogg
version = 1.0

# Python + pygame-ce (community edition — best Android support)
requirements = python3==3.11.0,pygame-ce

orientation = landscape
fullscreen = 1

# Android settings
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

android.permissions = VIBRATE

# Internet needed only for pygbag (web build); native APK doesn't need it
# android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 0
