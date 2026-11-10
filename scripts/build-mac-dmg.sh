#!/usr/bin/env bash
# Build Internet's Dream.app and an unsigned .dmg on macOS.
# Runs on GitHub Actions macos-15 runner; artifacts are unsigned
# (Gatekeeper will warn — right-click → Open on first launch).
set -euo pipefail
cd "$(dirname "$0")/.."

APP_NAME="Internet's Dream"
BIN_NAME="InternetDream"
BUILD_DIR="build-mac"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
DMG="$BUILD_DIR/$APP_NAME.dmg"

rm -rf "$BUILD_DIR"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

echo "==> Compiling SwiftUI sources"
xcrun swiftc -O \
  -parse-as-library \
  -framework SwiftUI \
  desktop-mac/Sources/InternetDreamApp.swift \
  -o "$APP_BUNDLE/Contents/MacOS/$BIN_NAME"

cat > "$APP_BUNDLE/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Internet's Dream</string>
  <key>CFBundleDisplayName</key><string>Internet's Dream</string>
  <key>CFBundleIdentifier</key><string>com.internetdream.memory</string>
  <key>CFBundleVersion</key><string>0.1.0</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundleExecutable</key><string>InternetDream</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# Ad-hoc signature so the app launches locally without an Apple ID cert
codesign --force --deep --sign - "$APP_BUNDLE" || true

echo "==> Creating DMG"
mkdir -p "$BUILD_DIR/dmg-root"
cp -R "$APP_BUNDLE" "$BUILD_DIR/dmg-root/"
ln -s /Applications "$BUILD_DIR/dmg-root/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$BUILD_DIR/dmg-root" \
  -ov -format UDZO "$DMG"

echo "==> Done: $DMG"
ls -lh "$DMG"
