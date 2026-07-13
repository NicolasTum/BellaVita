# Club de Compras

Aplicacion de escritorio para Windows destinada a administrar un programa de fidelizacion de una tienda de ropa.

## Tecnologias

- Python 3
- PySide6
- SQLite
- SQLAlchemy y Alembic, previstos para la capa de datos completa
- PyInstaller para generar el ejecutable
- Inno Setup para el instalador

## Desarrollo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

En macOS o Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Pruebas

```bash
pytest
```

## Base de datos

La base real no se guarda dentro del codigo ni junto al ejecutable. En Windows se ubicara en:

```text
C:\Users\USUARIO\AppData\Local\ClubCompras\data\club_compras.db
```

La base de datos real, backups, logs y exportaciones estan excluidos de Git.

## GitHub

Este repositorio debe ser privado porque manejara informacion de clientes.

Si GitHub CLI esta disponible:

```bash
gh auth status
gh repo create club-compras --private --source=. --remote=origin --push
```

Si no esta disponible, crear un repositorio privado en GitHub y luego ejecutar:

```bash
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
```

## Windows

Scripts previstos:

- `scripts/run_dev.ps1`: ejecutar en desarrollo.
- `scripts/build_windows.ps1`: generar un ejecutable con PyInstaller.
- `installer/club_compras.iss`: base para instalador con Inno Setup.

## Backups y Google Drive

La base activa debe permanecer local. Google Drive se usara solo como destino de copias de seguridad configurables desde la aplicacion.

Ver [docs/manual_usuario.md](docs/manual_usuario.md).
