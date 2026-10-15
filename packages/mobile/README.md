# Ourogen — Mobile (Expo)

Chat with your coworker, approve its actions from a push notification, see your day, and watch or take over live calls.

## Run it locally

```bash
cd packages/mobile
npm install --legacy-peer-deps
EXPO_PUBLIC_API_URL=http://<your-computer-ip>:5000 npx expo start
```

Push notifications need a physical device and a build with an EAS project ID (below). Expo Go is fine for everything else.

## Release: TestFlight and Google Play internal testing

You need:
- an [Expo account](https://expo.dev/signup);
- an [Apple Developer Program](https://developer.apple.com/programs/) membership;
- a [Google Play Console](https://play.google.com/console) account.

1. **Link the project.** This is interactive and done once.

   ```bash
   npx eas login
   npx eas init                 # creates the EAS project; note its project ID
   ```

   Put the ID in `EAS_PROJECT_ID`. `app.config.js` reads it, so nothing per-environment is committed. Set it in your shell, or as an [EAS environment variable](https://docs.expo.dev/eas/environment-variables/) for cloud builds.

2. **Set up push.**
   - **iOS:** `npx eas credentials` creates the APNs key for you.
   - **Android:** create a Firebase project and upload its service-account key with `npx eas credentials` (FCM V1).
   - **Backend:** set `EXPO_ACCESS_TOKEN` (expo.dev → Access tokens) so the backend can send push notifications.

3. **Build.**

   ```bash
   npx eas build --platform ios --profile production
   npx eas build --platform android --profile production
   ```

   Production builds use `EXPO_PUBLIC_API_URL=https://chat.ourogen.ai` (see `eas.json`).

4. **Submit for testing.**

   ```bash
   npx eas submit --platform ios       # lands in TestFlight; add testers in App Store Connect
   npx eas submit --platform android   # Play Console internal testing track
   ```

   The first Android upload has to be done by hand in the Play Console. After that, `eas submit` works.

5. **Store listing and privacy.** The app collects:
   - account email;
   - message content from the user's connected email, Slack and calendar, shown in the app but not stored on the device;
   - push tokens.

   It doesn't track users across apps, and nothing is sold. Use the [privacy policy](https://ourogen.ai/privacy) URL. `ITSAppUsesNonExemptEncryption` is `false` (standard HTTPS only), so no export-compliance prompt appears.

The app is named **Ourogen**, with bundle ID / package `ai.ourogen.app`. The icons are generated from `assets/ourogen-icon-black.png`: `icon.png` (1024², opaque), `adaptive-icon.png`, `splash.png`, and `notification-icon.png` (white on transparent, for Android).
