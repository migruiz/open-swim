# Flutter Android Deployment Plan - Containerized Build & Distribution

## Overview

- **CI/CD**: GitHub Actions (free, containerized)
- **Distribution**: GitHub Releases (public APK downloads)
- **Update notifications**: In-app update checker
- **Repo**: Public (no PAT needed - GitHub Releases API is public)
- **Signing**: Generate new keystore

---

## Implementation Status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Generate signing keystore | **MANUAL** |
| 2 | Update Gradle signing config | Done |
| 3 | Create GitHub Actions workflow | Done |
| 4 | Configure GitHub Secrets | **MANUAL** |
| 5 | Update .gitignore | Done |
| 6 | Add UpdateService | Done |
| 7 | Add Update UI | Done |
| 8 | Add dependencies | Done |
| 9 | Add Android permissions | Done |
| 10 | Set GitHub username in code | **MANUAL** |

---

## Manual Steps Required

### Step 1: Set Your GitHub Username

Edit `lib/services/update_service.dart` line 7:

```dart
const String githubOwner = 'YOUR_GITHUB_USERNAME';  // <-- Change this
const String githubRepo = 'open-swim';               // <-- Change if different
```

This is needed for the in-app update checker to find your releases.

---

### Step 2: Generate Android Signing Keystore

Open a terminal in the `client/` folder and run:

```bash
keytool -genkey -v -keystore open-swim-release.keystore -alias open-swim -keyalg RSA -keysize 2048 -validity 10000
```

You'll be prompted for:
- **Keystore password**: Choose a strong password (save it!)
- **Key password**: Can be same as keystore password
- **Name, Organization, etc.**: Can use defaults or your info

This creates `open-swim-release.keystore` in the current folder.

---

### Step 3: Create Local Keystore Properties

Create file `android/app/keystore.properties`:

```properties
storeFile=../../open-swim-release.keystore
storePassword=YOUR_KEYSTORE_PASSWORD
keyAlias=open-swim
keyPassword=YOUR_KEY_PASSWORD
```

This file is gitignored - it's only for local release builds.

---

### Step 4: Configure GitHub Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name | Value |
|-------------|-------|
| `KEYSTORE_BASE64` | Base64-encoded keystore (see below) |
| `KEYSTORE_PASSWORD` | Your keystore password |
| `KEY_ALIAS` | `open-swim` |
| `KEY_PASSWORD` | Your key password |

**To get the base64 value:**

```bash
# On Linux/Mac/Git Bash:
base64 -w 0 open-swim-release.keystore

# On PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("open-swim-release.keystore"))
```

Copy the entire output (long string) as the `KEYSTORE_BASE64` secret value.

---

### Step 5: Test Local Build (Optional)

```bash
fvm flutter build apk --release
```

The signed APK will be at: `build/app/outputs/flutter-apk/app-release.apk`

---

### Step 6: Create Your First Release

```bash
# Commit your changes
git add .
git commit -m "Add Android deployment with in-app updates"

# Push to GitHub
git push origin main

# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will automatically:
1. Build the APK in a containerized environment
2. Create a GitHub Release with the APK attached
3. Your app will detect the update on next launch

---

## How It Works

### No PAT Required

- **GitHub Releases API** is public for public repos
- **GitHub Actions** uses built-in `GITHUB_TOKEN` (automatic, no setup needed)
- **In-app update checker** fetches releases anonymously

### Release Flow

```
git tag v1.0.1 && git push origin v1.0.1
        ↓
GitHub Actions builds APK (containerized Ubuntu)
        ↓
Creates GitHub Release with APK attached
        ↓
App checks api.github.com/repos/{owner}/{repo}/releases/latest
        ↓
Shows "Update available" banner with download button
        ↓
Downloads APK and prompts user to install
```

---

## Files Modified (Automated)

| File | Change |
|------|--------|
| `.github/workflows/build-android.yml` | Created - CI/CD workflow |
| `android/app/build.gradle.kts` | Modified - signing config |
| `lib/services/update_service.dart` | Created - update checker |
| `lib/main.dart` | Modified - update banner UI |
| `pubspec.yaml` | Modified - added dependencies |
| `android/app/src/main/AndroidManifest.xml` | Modified - install permission |
| `.gitignore` | Modified - exclude keystores |

---

## Troubleshooting

### "No releases found" in app
- Check that `githubOwner` and `githubRepo` are correct in `update_service.dart`
- Ensure you pushed a tag (not just a commit)
- Wait a few minutes for GitHub Actions to complete

### GitHub Actions fails
- Check that all 4 secrets are configured correctly
- Verify base64 encoding has no line breaks
- Check Actions tab for error logs

### APK won't install
- Enable "Install from unknown sources" in Android settings
- The app needs `REQUEST_INSTALL_PACKAGES` permission (already added)
