# TGTG Yellow Cow

A minimal desktop monitor for nearby Too Good To Go surprise bags. The default mode now uses an Android emulator and the official Too Good To Go app for real login, then watches visible app text through ADB.

## What it does

- Opens the official Too Good To Go Android app in an emulator/device so you can log in normally there.
- Reads the current official app screen with ADB/uiautomator; it does not call the unofficial login API.
- Lets you navigate manually to a store/bag screen and click **Start monitoring current screen**.
- Pops up a notification when the screen text matches available-bag keywords and does not match sold-out keywords.
- Does not bypass captcha/bot-protection and does not auto-purchase; review and reserve manually in the official app.
- Keeps the older unofficial API monitor available as `tgtg-yellow-cow-api` for experiments only.

## Install on Windows

Open **PowerShell** in the cloned project folder, then run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

If PowerShell blocks activation scripts, you can bypass the policy only for the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

Or run PowerShell as your user and allow local venv scripts more permanently:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Or use Command Prompt instead:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .
```

## Install on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Run

After activating the virtual environment, run:

```powershell
tgtg-yellow-cow
```

`tgtg-yellow-cow` launches the Android emulator monitor. If Windows cannot find the script for any reason, run the module directly:

```powershell
python -m tgtg_yellow_cow.android_app
```

Then:

1. Start your Android emulator/device.
2. Click **Open official app / login**.
3. Log in normally inside the official Too Good To Go app in the emulator.
4. Navigate manually to the store/bag screen you want to monitor.
5. Click **Check login/screen once** to confirm the tool can read the screen.
6. Adjust available/sold-out/login keywords if the visible text uses different words.
7. Click **Start monitoring current screen**.


### Legacy API mode and manual credentials

The old unofficial API monitor is still available with `tgtg-yellow-cow-api`, but the Android emulator mode above is the recommended path. If `Login / refresh credentials` is blocked by HTTP 403 captcha protection, do not keep retrying the e-mail login endpoint. If you already have credentials from a legitimate existing Too Good To Go session, click **Paste credentials JSON** and paste:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "cookie": "..."
}
```

This app then saves those credentials to its local config and uses them on the next launch instead of calling `authByEmail` again. For the current `tgtg` client, `access_token`, `refresh_token`, and `cookie` are required; `user_id` by itself is not enough. Treat these values like passwords and do not share them.

To upgrade the unofficial client library before trying again, run inside the activated virtual environment:

```powershell
python -m pip install -U tgtg
```

If the latest library still receives HTTP 403 captcha responses, that is a Too Good To Go risk-control block on the login endpoint, not something this app can safely bypass.


## Android emulator UI automation mode

This is the primary supported mode because the API/e-mail login path can be blocked by HTTP 403 captcha protection. Use the official Android app instead:

1. Install Android Studio or another Android emulator.
2. Install the official Too Good To Go app in the emulator and log in manually.
3. Confirm ADB can see the emulator:

```powershell
adb devices
```

4. Start the ADB monitor UI:

```powershell
tgtg-yellow-cow
```

`tgtg-yellow-cow-android` also works as an explicit alias.

5. Click **Open official app / login**, complete real login inside the official app, navigate to the store/bag screen you care about, adjust the available/sold-out/login keywords if needed, then click **Start monitoring current screen**.

This mode does not call the unofficial API, does not try to bypass captcha, and does not auto-purchase. It reads visible/accessibility text from the official app through `adb shell uiautomator dump`; when login/onboarding words are detected it reminds you to finish login, and when configured availability words match without sold-out words it notifies you to review the emulator and act manually.

The default Android package name is `com.app.tgtg`. If the official app package differs on your emulator, change the Package field in the Android monitor window.

## Test on Windows

Install the test dependencies and run the automated tests:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src tests
```

These tests use a fake Too Good To Go client, so they do not require your real account or live API access.


## Captcha / HTTP 403 login blocks

If login fails with an HTTP 403 message that mentions `geo.captcha-delivery.com`, Too Good To Go is returning an in-browser captcha/bot-protection challenge before the unofficial Python client can complete e-mail login. This app cannot and will not bypass that protection.

Legitimate options are:

- Continue using the official Too Good To Go mobile app for login, browsing, and purchases.
- Retry later from the same normal home/mobile network if you believe it was a temporary risk check.
- Avoid VPNs, proxies, datacenter networks, or aggressive repeated login attempts, which can make bot-protection more likely.
- Watch for updates to the unofficial `tgtg` package in case it supports a compliant login flow in the future.

Do not try to evade Too Good To Go captcha, bot-protection, rate limits, or terms of service.

## Notes and safety improvements

- Polling faster than every 15 seconds is blocked to avoid hammering the service.
- The app requires a human confirmation before reserving anything.
- A reservation is not a completed purchase; payment still needs the official mobile app.
- This app uses the unofficial `tgtg` Python client. Use it responsibly and follow Too Good To Go's terms.
