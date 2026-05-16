# TGTG Yellow Cow

A minimal desktop monitor for nearby Too Good To Go surprise bags.

## What it does

- Logs in with your Too Good To Go e-mail link and stores the returned access token, refresh token, and cookie in the app config file with private file permissions where supported.
- Lists nearby Too Good To Go store bags for a latitude, longitude, and radius.
- Lets you select one store bag, click **Start**, and poll that item until a bag is available.
- Pops up a confirmation prompt when availability appears.
- If you click **Buy**, the app creates a reservation for one bag. The unofficial Python client cannot complete payment, so finish checkout in the official Too Good To Go mobile app.
- If you click **Skip**, no reservation is created.

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

If Windows cannot find the script for any reason, run the module directly:

```powershell
python -m tgtg_yellow_cow.app
```

Then:

1. Click **Login / refresh credentials**.
2. Enter the e-mail address for your Too Good To Go account.
3. Approve the login from the e-mail Too Good To Go sends you.
4. Enter your latitude, longitude, radius, and polling interval.
5. Click **Load stores**.
6. Select a store bag and click **Start**.


### Manual credentials instead of e-mail login

If `Login / refresh credentials` is blocked by HTTP 403 captcha protection, do not keep retrying the e-mail login endpoint. If you already have credentials from a legitimate existing Too Good To Go session, click **Paste credentials JSON** and paste:

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

If the API/e-mail login path keeps failing with HTTP 403 captcha protection, use the official Android app instead:

1. Install Android Studio or another Android emulator.
2. Install the official Too Good To Go app in the emulator and log in manually.
3. Confirm ADB can see the emulator:

```powershell
adb devices
```

4. Start the ADB monitor UI:

```powershell
tgtg-yellow-cow-android
```

5. Click **Launch official app**, navigate inside the official app to the store/bag screen you care about, adjust the available/sold-out keywords if needed, then click **Start monitoring current screen**.

This mode does not call the unofficial API, does not try to bypass captcha, and does not auto-purchase. It reads visible/accessibility text from the already logged-in official app through `adb shell uiautomator dump`; when the configured availability words match and sold-out words do not match, it notifies you to review the emulator and act manually.

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
