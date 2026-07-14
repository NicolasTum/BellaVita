# Instalacion en Windows - Bella Vita Club de Compras

## Instalador

El archivo esperado es:

```text
BellaVita_ClubDeCompras_Setup_0.1.0.exe
```

La aplicacion instalada no necesita Python, PySide6, SQLite, Visual Studio, Inno Setup ni dependencias manuales.

## Generar desde GitHub Actions

1. Entrar al repositorio privado en GitHub.
2. Abrir `Actions`.
3. Seleccionar el workflow `Build Windows Installer`.
4. Presionar `Run workflow`.
5. Esperar a que termine correctamente.
6. Descargar el artifact:

```text
BellaVita-ClubDeCompras-Windows-Installer
```

GitHub descarga un archivo `.zip`. Extraerlo y usar el instalador:

```text
BellaVita_ClubDeCompras_Setup_0.1.0.exe
```

El artifact contiene solo el instalador, no la carpeta completa `dist`.

## Advertencia de Windows SmartScreen

Windows puede mostrar una advertencia porque el instalador todavia no esta firmado digitalmente:

```text
Windows protegió su PC
```

Usar:

```text
Mas informacion
Ejecutar de todas formas
```

Hacerlo solamente cuando el instalador proviene de nuestro repositorio o fue enviado directamente por nosotros.

## Instalar

1. Hacer doble clic en `BellaVita_ClubDeCompras_Setup_0.1.0.exe`.
2. Elegir si se quiere crear acceso directo en el escritorio.
3. Finalizar la instalacion.
4. Abrir desde el escritorio o desde el menu Inicio.

La carpeta de instalacion predeterminada es:

```text
C:\Program Files\Bella Vita\Club de Compras
```

El ejecutable instalado se llama:

```text
ClubDeCompras.exe
```

## Datos locales

Los datos no se guardan dentro de `Program Files`.

La base activa queda en:

```text
%LOCALAPPDATA%\ClubCompras\data\club_compras.db
```

Tambien se usan estas carpetas:

```text
%LOCALAPPDATA%\ClubCompras\logs
%LOCALAPPDATA%\ClubCompras\backups
%LOCALAPPDATA%\ClubCompras\exports
%LOCALAPPDATA%\ClubCompras\config
```

La primera ejecucion crea automaticamente las carpetas, la base SQLite, las tablas y los valores por defecto.

## Actualizaciones

Instalar una version nueva encima de la anterior conserva:

- Base de datos.
- Backups.
- Logs.
- Exportaciones.
- Configuracion local.

No borrar manualmente `%LOCALAPPDATA%\ClubCompras` salvo que se quiera eliminar definitivamente la informacion local.

## Desinstalacion

El desinstalador quita la aplicacion de `Program Files`, pero conserva los datos del usuario en:

```text
%LOCALAPPDATA%\ClubCompras
```

Esto permite reinstalar o actualizar sin perder informacion.

## Crear copia de seguridad

1. Abrir la aplicacion.
2. Entrar en `Crear copia de seguridad`.
3. Revisar la carpeta configurada.
4. Presionar `Crear copia ahora`.
5. Opcionalmente elegir una carpeta sincronizada por Google Drive como destino.

## Informar errores

Enviar:

- Descripcion breve de lo que ocurrio.
- Captura de pantalla si existe.
- Fecha y hora aproximada.
- Archivo de log si se solicita.

Los logs quedan en:

```text
%LOCALAPPDATA%\ClubCompras\logs
```
