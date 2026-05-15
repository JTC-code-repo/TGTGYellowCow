# TGTG Yellow Cow

A minimal desktop monitor for nearby Too Good To Go surprise bags.

## What it does

- Logs in with your Too Good To Go e-mail link and stores the returned access token, refresh token, and cookie in `~/.tgtg-yellow-cow/config.json` with private file permissions.
- Lists nearby Too Good To Go store bags for a latitude, longitude, and radius.
- Lets you select one store bag, click **Start**, and poll that item until a bag is available.
- Pops up a confirmation prompt when availability appears.
- If you click **Buy**, the app creates a reservation for one bag. The unofficial Python client cannot complete payment, so finish checkout in the official Too Good To Go mobile app.
- If you click **Skip**, no reservation is created.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
tgtg-yellow-cow
```

Then:

1. Click **Login / refresh credentials**.
2. Enter the e-mail address for your Too Good To Go account.
3. Approve the login from the e-mail Too Good To Go sends you.
4. Enter your latitude, longitude, radius, and polling interval.
5. Click **Load stores**.
6. Select a store bag and click **Start**.

## Notes and safety improvements

- Polling faster than every 15 seconds is blocked to avoid hammering the service.
- The app requires a human confirmation before reserving anything.
- A reservation is not a completed purchase; payment still needs the official mobile app.
- This app uses the unofficial `tgtg` Python client. Use it responsibly and follow Too Good To Go's terms.
