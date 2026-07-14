# Guia rapida para instalar Bella Vita - Club de Compras

Este instructivo es para instalar la aplicacion en una computadora Windows de prueba.

## 1. Descargar el instalador

Descargar el archivo enviado por Bella Vita:

```text
BellaVita_ClubDeCompras_Setup_0.1.0.exe
```

Guardar el archivo en `Descargas` o en el escritorio.

## 2. Ejecutar el instalador

Hacer doble clic sobre:

```text
BellaVita_ClubDeCompras_Setup_0.1.0.exe
```

Si Windows muestra una advertencia de seguridad:

1. Presionar `Mas informacion`.
2. Presionar `Ejecutar de todas formas`.

Esta advertencia puede aparecer porque la primera version todavia no esta firmada digitalmente.

## 3. Instalar

Seguir los pasos del asistente.

La aplicacion se instala en:

```text
C:\Program Files\Bella Vita\Club de Compras
```

El instalador crea un acceso en el menu Inicio y puede crear un acceso directo en el escritorio.

## 4. Abrir la aplicacion

Abrir desde:

- Escritorio, si se creo el acceso directo.
- Menu Inicio > `Bella Vita - Club de Compras`.

No hace falta instalar Python ni ningun programa adicional.

## 5. Datos y respaldos

Los datos se guardan en la computadora, fuera de la carpeta de instalacion:

```text
%LOCALAPPDATA%\ClubCompras\data\club_compras.db
```

Las copias de seguridad se guardan por defecto en:

```text
%LOCALAPPDATA%\ClubCompras\backups
```

Para crear una copia:

1. Abrir la aplicacion.
2. Entrar en `Crear copia de seguridad`.
3. Presionar `Crear copia ahora`.

## 6. Cumpleanos del mes

En el panel principal hay una opcion:

```text
Cumpleaños del mes
```

Desde ahi se puede ver que clientes cumplen anos en el mes seleccionado y exportar un CSV para campanas.

## 7. Reportar errores

Si ocurre un problema, enviar:

- Captura de pantalla.
- Que accion se estaba realizando.
- Fecha y hora aproximada.

Los logs tecnicos quedan en:

```text
%LOCALAPPDATA%\ClubCompras\logs
```
