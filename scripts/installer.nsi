; NSIS script to create "XNOR chat service installer"
; This installer will copy the built executable into Program Files and optionally install Python and required packages.

!define APPNAME "XNOR Chat Service"
!define APP_EXE "XNOR LOMOMELEDOR.exe"
!define OUTFILE "xnor-chat-service-installer.exe"

; request admin
RequestExecutionLevel admin

Name "${APPNAME} Installer"
OutFile "${OUTFILE}"
InstallDir "$PROGRAMFILES\\XNOR Chat Service"

Section "Install"
    ; create directory
    SetOutPath "$INSTDIR"

    ; extract bundled files
    File "dist\\${APP_EXE}"
    File "requirements.txt"

    ; check for python - if missing, download and run installer via PowerShell with checksum verification
    ; NOTE: Update PYTHON_URL and PYTHON_SHA256 when bumping Python version
    nsExec::ExecToLog 'powershell -NoProfile -Command "$pythonUrl = 'https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe'; $expected = 'INSERT_SHA256_HERE'; if ((Get-Command python -ErrorAction SilentlyContinue) -eq $null) { Write-Host \"Python not found; downloading installer\"; $t=Join-Path $env:TEMP \"python-installer.exe\"; Invoke-WebRequest -Uri $pythonUrl -OutFile $t; if ([string]::IsNullOrWhiteSpace($expected) -or $expected -eq 'INSERT_SHA256_HERE') { Write-Host \"Skipping checksum verification (expected checksum not set)\"; Start-Process -FilePath $t -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait; if ($LASTEXITCODE -ne 0) { Write-Host \"Python installer failed with exit code $LASTEXITCODE\"; Exit 1 } } else { $hash = (Get-FileHash -Path $t -Algorithm SHA256).Hash; if ($hash -ne $expected) { Write-Host \"Python installer checksum mismatch: $hash\"; Exit 1 } else { Write-Host \"Checksum verified\"; Start-Process -FilePath $t -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait; if ($LASTEXITCODE -ne 0) { Write-Host \"Python installer failed with exit code $LASTEXITCODE\"; Exit 1 } } } } else { Write-Host \"Python found\" }"'

    ; try installing required packages if python available
    nsExec::ExecToLog 'powershell -NoProfile -Command "if (Get-Command python -ErrorAction SilentlyContinue) { python -m pip install --upgrade pip; python -m pip install -r requirements.txt } else { Write-Host \"Skipping pip install: python missing\" }"'

    ; create a start menu shortcut
    CreateDirectory "$SMPROGRAMS\\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk" "$INSTDIR\\${APP_EXE}"

    ; create a Desktop shortcut
    CreateShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\${APP_EXE}"

    ; offer to register as a Windows Service (best-effort)
    MessageBox MB_YESNO "Register \"${APPNAME}\" as a Windows Service (start automatically)?" IDYES register_service
    goto done_register
    register_service:
        ; sc requires admin; this is best-effort and may fail depending on executable behavior
        ; note: sc syntax: sc create <ServiceName> binPath= <exe path> start= auto DisplayName= "Name"
        nsExec::ExecToLog 'sc create "XNOR Chat Service" binPath= ""$INSTDIR\\${APP_EXE}"" start= auto DisplayName= "${APPNAME}"'
        Pop $0
        ; $0 contains the return code; 0 usually means success
        MessageBox MB_OK "Service registration attempted (return code: $0). Check Windows Services to verify."
    done_register:

    ; notify finish
    MessageBox MB_OK "${APPNAME} installed to $INSTDIR"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\${APP_EXE}"
    Delete "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\\${APPNAME}"
    RMDir "$INSTDIR"
SectionEnd