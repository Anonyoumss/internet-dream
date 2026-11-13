# Store Submission Guide — Internet's Dream

Everything below needs **your** accounts — I can't create accounts or accept
ToS on your behalf. All assets and metadata are already prepared in this repo.

## 1. GitHub Releases — ✅ DONE
Nightly alpha workflow publishes APK/DMG/deb/AppImage/extension ZIP to a
rolling `nightly` prerelease + dated releases. Live now.

## 2. F-Droid
F-Droid builds from source — it does NOT accept APK uploads.

1. Create account: https://gitlab.com/users/sign_up
2. Fork https://gitlab.com/fdroid/fdroiddata
3. Copy `store/fdroid/metadata.yml` → `metadata/com.internetdream.internet_dream.yml`
   (adjust: F-Droid needs a build recipe — `build:`/`gradle:` block pointing at
   the Flutter project, or wrap the fastlane metadata once a signed release
   exists. The debug-signed APK is NOT submittable; produce a release-signed
   build first via `keytool` + `flutter build apk --release` with
   `android/key.properties`.)
4. Open MR. Review takes days–weeks. Reproducible-build verification required.

## 3. Firefox Add-ons (AMO)
1. Account: https://addons.mozilla.org/developers/
2. `cd extension && zip -r ../internet-dream-extension.zip .`
   (CI artifact `internet-dream-extension.zip` on the nightly release works)
3. Submit → "On your website" distribution or listed. Listing text:
   `store/amo/listing.md`. Self-distributed (unlisted) needs no review.

## 4. Obtainium / AltStore-style
Add repo URL `https://github.com/Anonyoumss/internet-dream/releases` —
GitHub Releases are natively supported. App manifest for Obtainium:
see `store/obtainium/` (app id `com.internetdream.internet_dream`).

## 5. Other free channels (manual, ~15 min each)
- **Aptoide / APKPure**: developer account → upload the nightly APK.
- **SourceHut / Codeberg**: mirror repo for visibility.
- **Product Hunt / BetaList / AlternativeTo**: launch listings — use
  `marketing/COPY.md` descriptions + `assets/store/` graphics.
- **r/androidapps, r/selfhosted, r/opensource**: post the Reddit copy.

## 6. Email + social accounts — needs you
- Email: pick a provider (Proton free / Gmail). I can't verify phone/email.
- Socials (X, Mastodon, LinkedIn, Instagram, YouTube, Discord server):
  create accounts, then use `marketing/COPY.md` post templates verbatim.
  All graphics are in `assets/store/` and `downloads/assets/`.
