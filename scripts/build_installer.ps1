# PowerShell script to build a Windows executable using PyInstaller and zip the dist
# Usage: Open an elevated PowerShell in the repo root and run: .\scripts\build_installer.ps1

param(
    [string]$python = "python",
    [string]$spec = "XNOR LOMOMELEDOR.spec",
    [string]$out = "dist"
)

# Install PyInstaller if missing
& $python -m pip install --upgrade pip
& $python -m pip install pyinstaller --quiet

# Build one-folder exe
& $python -m PyInstaller --noconfirm --onefile "XNOR LOMOMELEDOR.py"

# Zip resulting executable
$exe = Join-Path -Path "dist" -ChildPath "XNOR LOMOMELEDOR.exe"
if (Test-Path $exe) {
    $zip = "release-XNOR-windows.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory("dist", $zip)
    Write-Host "Built and zipped: $zip"
} else {
    Write-Error "Expected $exe not found"
}
