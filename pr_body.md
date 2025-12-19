### Summary
This PR cleans up style and tooling, adds documentation, and hardens the Windows installer.

**Key changes**
- Ran and applied ruff autofixes (style issues resolved).
- Fixed small runtime bugs and removed unused imports.
- Added README.md, LICENSE (MIT) and a .gitignore.
- Hardened `scripts/installer.nsi`:
  - Adds SHA256 verification for the Python installer (skips verification if checksum placeholder not set and warns).
  - Better error handling for download/installer failure.
- Added small CI/workflow fixes to make the Release step robust.
- Added unit test for Tor control-port behavior, and all tests pass locally.

### Why
- Improve code quality and maintainability (linters + tests).
- Provide clear docs and license for publishing to GitHub.
- Make installer behavior safer (checksum verification, clearer failure modes) to reduce risk when provisioning Python on target systems.

### How to test (local)
1. Install dev deps:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m ruff check .
   python -m pytest -q
2. Smoke build:
   pyinstaller --noconfirm --onefile "XNOR LOMOMELEDOR.py" → verify `dist/XNOR LOMOMELEDOR.exe`
3. Installer (optional, requires `makensis`):
   makensis scripts/installer.nsi (set SHA256 in the script before using the download feature)

### Files changed (high level)
- Modified: `XNOR LOMOMELEDOR.py` (style fixes, better Tor handling)
- Modified: `scripts/installer.nsi` (SHA256 verification + improved checks)
- Modified: `.github/workflows/build_windows.yml` (create_release id + installer check step)
- Added: `README.md`, `LICENSE`, `.gitignore`
- Added: `tests/test_tor.py`

### Reviewer checklist ✅
- [ ] Code changes are logical and well-scoped
- [ ] Tests pass locally (pytest)
- [ ] Ruff/linters show no new errors
- [ ] NSIS installer behavior reviewed (especially Python download/verification)
- [ ] README + LICENSE look acceptable for public release

### Release notes (short)
- Improve code quality & tests; add documentation and license.
- Harden Windows installer by adding (optional) checksum verification for downloaded Python installer.

### Notes & follow-ups (suggestions)
- CI: add a job to compute the Python installer SHA256 automatically and store it as an artifact or file the `.nsi` script can consume.
- Security: consider bundling the Python installer or the embeddable distribution or add signed checksum verification.
