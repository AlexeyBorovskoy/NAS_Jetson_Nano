# Тесты Android-клиента / Android Client Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Devices Supported

- Xiaomi Redmi Note (MIUI) -- primary test device
- Requirement: connected to home WiFi (192.168.0.x network)

---

## Apps Under Test

| App | Version | Source | Status |
|---|---|---|---|
| Immich | latest | Play Store | Installed, configured |
| Nextcloud | latest | Play Store | Installed |
| DAVx5 | v4.5.14 | APK | Installed |

---

## Test Cases

### T6.1: Immich Login (Local Network)

1. Open Immich app
2. Enter server URL: `http://192.168.0.50:2283`
3. Enter credentials: admin / (from config/.env)
4. Expected: login succeeds, photo library loads

### T6.2: Immich Login (Via VPS)

1. Switch to mobile data or use external URL
2. Enter server URL: `http://95.163.176.103:2283`
3. Expected: login succeeds (may be slower via VPS)

### T6.3: Immich Backup

1. Navigate to Immich app settings
2. Check "Backup" section
3. Expected: background backup is enabled, queue shows photos pending

### T6.4: Nextcloud Login (HTTPS)

1. Open Nextcloud app
2. Enter server URL: `https://95.163.176.103:8443`
3. Accept self-signed certificate warning
4. Enter credentials: admin / (from config/.env NEXTCLOUD_ADMIN_PASSWORD)
5. Expected: login succeeds, files visible

### T6.5: DAVx5 Calendar/Contacts Sync

1. Open DAVx5
2. Add account: `https://95.163.176.103:8443/remote.php/dav`
3. Accept self-signed certificate
4. Select calendars and contacts to sync
5. Expected: sync completes without errors

---

## ADB Read-Only Check (Optional)

If ADB is available for debugging:

```bash
# Safe read-only check only
tests/android/adb_readonly_check.sh
```

This script performs ONLY:
- `adb devices` -- list connected devices
- `adb shell getprop ro.build.version.release` -- Android version
- `adb shell pm list packages -3` -- installed user apps

It does NOT and MUST NOT:
- Install or uninstall apps
- Pull personal data (photos, contacts)
- Read IMEI, serial numbers, accounts
- Trigger reboots

---

## MIUI-Specific Notes

- MIUI Battery Saver may kill background sync. Disable battery optimization for Immich and Nextcloud.
- Path: Settings -> Apps -> Immich -> Battery -> No restrictions
- Auto-start permission may be required on MIUI for background backup.
- MIUI may block self-signed certificates in some versions. Use HTTP for local access.

---

## Expected Results

| Test | Expected | Actual | Pass? |
|---|---|---|---|
| Immich local login | success | | |
| Immich VPS login | success | | |
| Immich backup active | yes | | |
| Nextcloud HTTPS login | success | | |
| DAVx5 sync | success | | |
| Battery optimization disabled | yes | | |

---

## Reporting Format

When logging results, do NOT include:
- Device IMEI or MEID
- Phone number
- Google Account email
- WiFi passwords
- Personal photo content

Only log: app version, login success/fail, sync status, error messages.
