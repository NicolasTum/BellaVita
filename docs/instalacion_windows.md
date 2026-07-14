# Instalacion en Windows - Bella Vita Club de Compras

## Descargar

Descargar el archivo:

```text
BellaVita_ClubDeCompras_Setup_0.1.0.exe
```

Usar solamente el instalador enviado por Bella Vita o descargado desde el artifact privado del workflow del repositorio.

## Advertencia de Windows

Windows puede mostrar una advertencia porque el instalador todavia no esta firmado digitalmente.

Si el archivo fue enviado por nosotros:

1. Hacer doble clic sobre el instalador.
2. Si aparece una advertencia, seleccionar `Mas informacion`.
3. Seleccionar `Ejecutar de todas formas`.
4. Continuar la instalacion.

## Instalar

El instalador crea la aplicacion en:

```text
C:\Program Files\Bella Vita\Club de Compras
```

Tambien crea acceso directo en el menu Inicio y puede crear un acceso directo en el escritorio.

## Abrir

Abrir desde:

- Menu Inicio: `Bella Vita - Club de Compras`
- Acceso directo del escritorio, si fue seleccionado durante la instalacion.

No hace falta instalar Python.

## Datos locales

Los datos no se guardan dentro de Program Files ni junto al ejecutable.

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

Al actualizar o desinstalar la aplicacion, estos datos locales se conservan.

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
- Archivo de log si se solicita, ubicado en:

```text
%LOCALAPPDATA%\ClubCompras\logs
```
