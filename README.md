# Club de Compras

Aplicacion de escritorio para Windows y macOS destinada a administrar un programa de fidelizacion de una tienda de ropa.

## Tecnologias

- Python 3
- PySide6
- SQLite
- SQLAlchemy y Alembic, previstos para la capa de datos completa
- PyInstaller para generar el ejecutable
- Inno Setup para el instalador

## Desarrollo

macOS o Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## Pruebas

```bash
pytest
```

## Estado funcional actual

Implementado en desarrollo:

- Navegacion principal con pantallas reales y boton volver.
- Alta de clientes con validaciones.
- Fecha de nacimiento opcional para clientes, con validacion y uso promocional por cumpleaños.
- Busqueda de clientes mientras se escribe.
- Ficha completa basica del cliente.
- Edicion de clientes.
- Activacion y desactivacion logica.
- Deteccion de posibles duplicados por telefono, correo o nombre y apellido.
- Resumen en ficha de stickers actuales, premios disponibles y ultima compra.
- Registro de compras simples y detalladas.
- Pantalla de compra en dos columnas: clientes a la izquierda y formulario a la derecha.
- Calculo automatico de subtotales y total.
- Asignacion automatica al ciclo de fidelizacion.
- Carton visual de seis stickers.
- Calculo de promedio parcial y final con `Decimal`.
- Finalizacion automatica del ciclo en la sexta compra.
- Creacion automatica de premio disponible.
- Inicio automatico de un nuevo ciclo en la septima compra.
- Listado real de premios disponibles, utilizados, vencidos y anulados.
- Ficha completa de premio.
- Canje de premio con validacion de diferencia pagada.
- Historial basico de compras, ciclos y premios por cliente.
- Indicadores del panel principal calculados desde SQLite.
- Flujo post-compra optimizado para registrar compras consecutivas.
- Configuracion de administrador guardada en `app_settings`.
- Cantidad objetivo de compras por ciclo configurable; cada ciclo conserva su propio objetivo.
- Pantalla de configuracion clara para compras necesarias por ciclo, con valor visible entre 1 y 50.
- Datos generales de tienda y correo promocional preparados para integraciones futuras.
- Resumen simple de cumpleaños del mes en el panel principal, sin datos personales visibles.
- Pantalla `Cumpleaños` para revisar clientes del mes, buscar, ver contactos, premios disponibles y exportar CSV.
- Respaldos manuales y automaticos con SQLite backup API, integridad, limpieza y restauracion segura.
- Carpeta de respaldo configurable, apta para una carpeta local o sincronizada por Google Drive.
- Pie de version discreto en el panel principal.

Pendiente por fases:

- Correcciones y anulaciones de compras.
- Historial avanzado con edicion auditada.
- Reportes/exportaciones.
- Seguridad completa por usuarios y roles reales.

La auditoria funcional esta en:

```text
docs/auditoria_funcional.md
```

## Identidad visual

El logo oficial de Bella Vita esta guardado en:

```text
assets/images/logo_bellavita.png
```

Los iconos de aplicacion generados desde ese logo estan en:

```text
assets/icons/app_icon.icns
assets/icons/app_icon.ico
```

La carga de recursos graficos esta centralizada en `app.ui.branding`, usando `app.utils.paths.resource_path()` para funcionar tanto en desarrollo como dentro de la aplicacion compilada. Los archivos `.spec` de PyInstaller incluyen la carpeta `assets` y usan estos iconos sin rutas absolutas.

## Base de datos

La base real no se guarda dentro del codigo, junto al ejecutable ni dentro de los paquetes compilados.

En macOS se ubica en:

```text
~/Library/Application Support/ClubCompras/data/club_compras.db
```

En Windows se ubica en:

```text
C:\Users\USUARIO\AppData\Local\ClubCompras\data\club_compras.db
```

En Windows tambien se crean:

```text
%LOCALAPPDATA%\ClubCompras\logs
%LOCALAPPDATA%\ClubCompras\backups
%LOCALAPPDATA%\ClubCompras\exports
%LOCALAPPDATA%\ClubCompras\config
```

Tambien se resuelven de forma centralizada:

- Datos de usuario: `app.utils.paths.user_data_dir()`
- Base SQLite: `app.utils.paths.database_path()`
- Logs: `app.utils.paths.log_dir()`
- Backups: `app.utils.paths.backup_dir()`
- Recursos empaquetados: `app.utils.paths.resource_path()`

La base de datos real, backups, logs, exportaciones, `.env` y credenciales estan excluidos de Git y no se incluyen en PyInstaller.

Migraciones actuales:

- `loyalty_cycles.target_purchase_count`: guarda el objetivo de compras de cada ciclo.
- `customers.birth_date`: fecha de nacimiento opcional, sin hora, para promociones de cumpleaños.
- `purchases.sticker_number`: permite objetivos configurables mayores a 6.
- `backup_logs`: registra respaldos, restauraciones, errores y limpiezas.
- `app_settings`: guarda promocion, tienda, moneda, datos de correo promocional y carpeta de respaldo.

## Respaldos y restauracion

La base activa permanece siempre local:

```text
~/Library/Application Support/ClubCompras/data/club_compras.db
```

La carpeta de respaldos se puede cambiar desde la pantalla `Respaldos`. Por defecto usa:

```text
~/Library/Application Support/ClubCompras/backups/
```

Las copias se crean con el formato:

```text
club_compras_YYYY-MM-DD_HHMMSS.db
```

El respaldo usa la API segura de SQLite, verifica integridad antes y despues de copiar, audita el resultado y conserva inicialmente las ultimas 30 copias sin borrar nunca la unica copia existente. Tambien se crean respaldos automaticos al cerrar correctamente la aplicacion y despues de compras, canjes de premios o cambios de configuracion, con un maximo aproximado de uno cada 30 minutos.

La restauracion verifica el archivo elegido y crea antes una copia de seguridad de la base actual. Despues de restaurar, cerrar y abrir nuevamente la aplicacion.

## Promociones de cumpleaños

Los clientes pueden tener una fecha de nacimiento opcional. El formulario permite dejarla sin informar, cargarla con calendario o limpiarla. No se guarda la fecha actual por defecto.

Para cargar una fecha de nacimiento el cliente debe aceptar `Acepta recibir promociones`. Si se retira ese consentimiento, la aplicacion pregunta si debe eliminar tambien la fecha guardada.

El panel principal solo muestra la cantidad de cumpleaños del mes y un acceso a la seccion dedicada. No muestra nombres, telefonos, correos ni estados de consentimiento.

El servicio `app.services.birthday_promotions.BirthdayPromotionService` permite filtrar:

- Cumpleaños de hoy.
- Cumpleaños de esta semana.
- Cumpleaños del mes actual o un mes seleccionado.
- Cumpleaños del proximo mes.
- Rango de meses.
- Clientes con o sin fecha de nacimiento.
- Clientes activos con consentimiento promocional.

La exportacion CSV para campañas incluye nombre, apellido, fecha de nacimiento, dia, mes, telefono, correo, ultima compra y premios disponibles. No incluye una columna visible de consentimiento.

Ver [docs/promociones_cumpleanos.md](docs/promociones_cumpleanos.md).

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

Compilar la aplicacion y, si Inno Setup esta disponible, el instalador desde Windows:

```powershell
.\scripts\build_windows.ps1
```

El script crea o usa `.venv`, instala dependencias, ejecuta `pytest`, limpia builds anteriores y compila con:

```powershell
.\.venv\Scripts\pyinstaller.exe --clean --noconfirm club_compras_windows.spec
```

La aplicacion `onedir` queda en:

```text
dist/Club de Compras/Club de Compras.exe
```

Si `ISCC.exe` esta disponible, el instalador queda en:

```text
dist/installer/BellaVita_ClubDeCompras_Setup_0.1.0.exe
```

Notas:

- El `.exe` y el instalador deben generarse en Windows.
- No se incluye la base real ni backups.
- `installer/windows/ClubDeCompras.iss` instala en `{autopf}\Bella Vita\Club de Compras`.
- El instalador crea acceso directo en el menu Inicio y ofrece crear acceso directo en el escritorio.
- Actualizar o desinstalar la aplicacion no elimina la base local ni respaldos.

Para enviar a una computadora de prueba:

1. Generar el instalador en Windows o con GitHub Actions.
2. Enviar `dist/installer/BellaVita_ClubDeCompras_Setup_0.1.0.exe`.
3. La persona de prueba debe seguir [docs/instalacion_windows.md](docs/instalacion_windows.md).

Tambien hay una guia breve para enviar al cliente en [docs/guia_cliente_instalacion.md](docs/guia_cliente_instalacion.md).

## macOS

Compilar la aplicacion `.app` desde una Mac:

```bash
bash scripts/build_macos.sh
```

El script instala dependencias, ejecuta `pytest` y compila con:

```bash
.venv/bin/pyinstaller --clean --noconfirm club_compras_macos.spec
```

La aplicacion queda en:

```text
dist/Club de Compras.app
```

Para abrirla desde Terminal:

```bash
open "dist/Club de Compras.app"
```

La base real no se incluye dentro del paquete `.app`; se guarda en la carpeta de datos del usuario:

```text
~/Library/Application Support/ClubCompras/data/club_compras.db
```

## GitHub Actions

El workflow manual esta en:

```text
.github/workflows/build-desktop.yml
```

Para ejecutarlo:

1. Ir a GitHub Actions.
2. Seleccionar `Build desktop apps`.
3. Presionar `Run workflow`.

El workflow compila en runners separados:

- `macos-latest`: genera `club-compras-macos`.
- `windows-latest`: genera `club-compras-windows`.

Los compilados se publican como artifacts privados del workflow dentro del repositorio privado. Antes de cada compilacion se ejecutan las pruebas.

El workflow especifico del instalador Windows esta en:

```text
.github/workflows/build-windows-installer.yml
```

Se ejecuta manualmente con `workflow_dispatch` o al crear una etiqueta `v*`. Publica el artifact privado:

```text
BellaVita-ClubDeCompras-Windows-Installer
```

Para descargarlo, entrar en GitHub Actions, abrir la ejecucion del workflow y descargar el artifact. El instalador no se sube al repositorio.

## Backups y Google Drive

La base activa debe permanecer local. Google Drive se puede usar como destino de copias de seguridad configurables desde la aplicacion, seleccionando una carpeta sincronizada.

Ver [docs/manual_usuario.md](docs/manual_usuario.md).
