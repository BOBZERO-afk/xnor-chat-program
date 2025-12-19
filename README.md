XNOR Chat Service

Simple encrypted chat service with a Tkinter UI and optional Tor hidden service support.

Features
- End-to-end message protection (XOR keystream + HMAC + Fernet)
- Optional XNOR preprocessing integration (safe loader)
- Non-blocking GUI and threaded networking
- Optional Tor onion creation (requires Tor + stem)
- Windows installer (NSIS) that can attempt to install Python and pip packages when absent

Quick Start — Download & Install

- Download the latest release from GitHub Releases (look for `release-XNOR-windows.zip` or `xnor-chat-service-installer.exe`).
- If you downloaded the installer (`xnor-chat-service-installer.exe`), run it and follow prompts. The installer may offer to install Python and required packages if Python is not present (admin rights required for that step).
- If you downloaded the one-file EXE, run `dist\XNOR LOMOMELEDOR.exe` to start the GUI.

Run from source (development)

1. Create a virtual environment and install dependencies:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2. Run the program:
   python "XNOR LOMOMELEDOR.py"

3. Run tests and linters:
   python -m ruff check .
   python -m pytest -q

Usage (GUI)

- Host: set the destination IP (or host:port) to send messages.
- User: sender display name.
- Send: type a message and press Send — messages are sent to the host:port via the handshake + encrypted payload.
- Toggle TOR: switches to use a SOCKS5 proxy (Tor) for outgoing connections (Tor must be running on localhost:9050).
- Create XNOR Onion: attempts to use Tor control port (127.0.0.1:9051) to create an ephemeral hidden service and display the .onion address (requires Tor + stem and ControlPort enabled).
- The app persists seen message IDs and the XNOR preprocessing preference in `state.json.enc` (encrypted with the app seed).

Building the EXE and Installer

- Build EXE locally (PyInstaller):
  pyinstaller --noconfirm --onefile "XNOR LOMOMELEDOR.py"
  -> Result: `dist\XNOR LOMOMELEDOR.exe`

- Build NSIS installer (requires NSIS/makensis on PATH):
  makensis scripts\installer.nsi

Installer notes & security

- The NSIS script can attempt to download the official Python installer if Python is missing. By default you should set `PYTHON_SHA256` in the script to a known-good checksum to enable verification.
- The installer’s service registration step (`sc create`) is best-effort and requires admin privileges and a proper service wrapper for reliable behavior.

Logs & troubleshooting

- Log file: `logs/xnor.log` (rotating, UTF-8). Check this for errors and troubleshooting details.
- Common issues:
  - "Tor control port not available": Tor is not running or ControlPort disabled; start Tor or enable ControlPort.
  - "Cannot connect after N attempts": destination host unreachable or port closed.

Contributing & license

- Please open an issue or PR. Ensure tests pass and ruff is run.
- Licensed under the MIT License (see `LICENSE`).
