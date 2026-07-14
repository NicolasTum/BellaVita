$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$PythonExe = ".\.venv\Scripts\python.exe"
$PyInstallerExe = ".\.venv\Scripts\pyinstaller.exe"
$AppExe = "dist\Club de Compras\Club de Compras.exe"

if (-not (Test-Path $PythonExe)) {
    py -3 -m venv .venv
}

$Version = (& $PythonExe -c "from app.version import VERSION; print(VERSION)")

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt
& $PythonExe -m pytest

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}
if (Test-Path "dist\Club de Compras") {
    Remove-Item "dist\Club de Compras" -Recurse -Force
}
if (Test-Path "dist\installer") {
    Remove-Item "dist\installer" -Recurse -Force
}

& $PyInstallerExe --clean --noconfirm club_compras_windows.spec

if (-not (Test-Path $AppExe)) {
    throw "No se encontro el ejecutable esperado: $AppExe"
}

Write-Host "Aplicacion Windows generada en: $AppExe"

$Iscc = $env:ISCC_EXE
if (-not $Iscc) {
    $Command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        $Iscc = $Command.Source
    }
}

if ($Iscc) {
    & $Iscc "/DMyAppVersion=$Version" "installer\windows\ClubDeCompras.iss"
    $Installer = "dist\installer\BellaVita_ClubDeCompras_Setup_$Version.exe"
    if (-not (Test-Path $Installer)) {
        throw "No se encontro el instalador esperado: $Installer"
    }
    Write-Host "Instalador Windows generado en: $Installer"
} else {
    Write-Host "ISCC.exe no esta disponible. PyInstaller finalizo correctamente; instala Inno Setup para generar el instalador."
}
