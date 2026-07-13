$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --name "Club de Compras" --clean app\main.py
