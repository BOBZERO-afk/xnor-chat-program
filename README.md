XNOR Chat Service

Simple encrypted chat service with a Tkinter UI and optional Tor hidden service support.

Features
- End-to-end message protection (XOR keystream + HMAC + Fernet)
- Optional XNOR preprocessing integration (safe loader)
- Non-blocking GUI and threaded networking
- Optional Tor onion creation (requires Tor + stem)
- Installer (NSIS) that can attempt to install Python and pip packages when absent

Development

Requirements: Python 3.11+, virtualenv

1. Create a venv and install deps
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2. Run tests and linters
   python -m ruff check .
   python -m pytest -q

Building
- Build EXE (local): pyinstaller --noconfirm --onefile "XNOR LOMOMELEDOR.py"
- Build NSIS installer: makensis scripts\installer.nsi (requires NSIS / makensis in PATH)

Notes about the installer
- The NSIS script will attempt to download the official Python installer when Python is not present and will perform SHA256 verification if `PYTHON_SHA256` (in the script) is set; if not set, it will skip checksum verification but warn.
- Service registration is offered but is best-effort; it requires admin privileges and a consumer-ready service wrapper.

Contributing
- Open an issue or a pull request. Ensure tests pass and style checks run (ruff).
