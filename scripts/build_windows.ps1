$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$PythonExe = ".\.venv\Scripts\python.exe"
$PyInstallerExe = ".\.venv\Scripts\pyinstaller.exe"
$AppDir = "dist\ClubDeCompras"
$AppExe = Join-Path $AppDir "ClubDeCompras.exe"

if (-not (Test-Path $PythonExe)) {
    py -3 -m venv .venv
}

$Version = (& $PythonExe -c "from app.version import VERSION; print(VERSION)")

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements-build.txt
& $PythonExe -m pytest

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}
if (Test-Path $AppDir) {
    Remove-Item $AppDir -Recurse -Force
}
if (Test-Path "dist\installer") {
    Remove-Item "dist\installer" -Recurse -Force
}

& $PyInstallerExe --clean --noconfirm club_compras_windows.spec

if (-not (Test-Path $AppExe)) {
    throw "No se encontro el ejecutable esperado: $AppExe"
}

$DatabaseFiles = Get-ChildItem $AppDir -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".db", ".sqlite", ".sqlite3") }
if ($DatabaseFiles) {
    $Names = ($DatabaseFiles | ForEach-Object { $_.FullName }) -join ", "
    throw "El paquete contiene bases de datos y debe corregirse: $Names"
}

Write-Host "Aplicacion Windows generada en: $AppExe"

$Iscc = $env:ISCC_EXE
if (-not $Iscc) {
    $Command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        $Iscc = $Command.Source
    }
}

if (-not $Iscc) {
    throw "ISCC.exe no esta disponible. Instala Inno Setup para generar el instalador."
}

if (-not (Test-Path $Iscc)) {
    throw "ISCC.exe no existe en la ruta detectada: $Iscc"
}

& $Iscc "/DMyAppVersion=$Version" "installer\windows\ClubDeCompras.iss"
$Installer = "dist\installer\BellaVita_ClubDeCompras_Setup_$Version.exe"
if (-not (Test-Path $Installer)) {
    throw "No se encontro el instalador esperado: $Installer"
}
Write-Host "Instalador Windows generado en: $Installer"
