# CART3R

CART3R is a small Windows desktop application written in Python. It demonstrates local system monitoring, a local app login, local device-registration bookkeeping, and a local activity history.

## Current features

- A local password screen for the CART3R app
- CPU, memory, and disk usage display
- A local device information and registration tab
- A local activity log with timestamps
- A security tab for changing the CART3R app password

## Important: what this version does not do

This version runs locally on the computer where it is opened. It does **not** connect to another computer, stream another person's screen, or provide remote mouse or keyboard control. Device registration is only a local record; it does not establish a network connection.

The CART3R password is an app-level convenience, not a replacement for your Windows account security. Anyone with access to the computer and its files may be able to alter or remove the app's local data.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- The Python package listed in `requirements.txt` (`psutil`)

Tkinter is included with most standard Windows Python installations.

## Setup

1. Download or clone this repository.
2. Open Command Prompt in the folder that contains `main.py`.
3. Install the required package:

   ```cmd
   py -m pip install -r requirements.txt
   ```

4. Start CART3R:

   ```cmd
   py main.py
   ```

On the first launch, CART3R asks you to create a local app password. On later launches, enter that password to open the dashboard.

## Local data and privacy

CART3R creates these files beside `main.py` when it runs:

- `cart3r_auth.json` — local password salt and password hash
- `cart3r_device.json` — local device information and registration status
- `cart3r_activity.jsonl` — local activity history

These files are computer-specific and are excluded by `.gitignore`. Do not commit or share them. Do not put passwords, access tokens, private keys, or other personal information in this repository.

## Consent and responsible use

Only install or run CART3R on computers you own or where the owner has clearly agreed to its installation and use. Any future remote-support capability should be visible to the computer's owner, require their approval for each session, and provide an obvious way to end the session.

## Project status

This is an early learning project. The current release is a local system-monitoring demo, not a secure remote-support product.
