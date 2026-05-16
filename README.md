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

## Test on Windows

Install the test dependencies and run the automated tests:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src tests
```

These tests use a fake Too Good To Go client, so they do not require your real account or live API access.

## Notes and safety improvements

- Polling faster than every 15 seconds is blocked to avoid hammering the service.
- The app requires a human confirmation before reserving anything.
- A reservation is not a completed purchase; payment still needs the official mobile app.
- This app uses the unofficial `tgtg` Python client. Use it responsibly and follow Too Good To Go's terms.
