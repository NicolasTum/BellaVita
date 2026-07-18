# Importacion masiva de clientes

La importacion masiva permite cargar clientes historicos desde un archivo CSV y, opcionalmente, hasta seis compras anteriores por cliente.

## Plantilla

Desde `Configuracion > Importar clientes` usar `Descargar plantilla CSV`.

El archivo generado se llama:

```text
Plantilla_Importacion_Clientes_BellaVita.csv
```

La plantilla usa UTF-8 con BOM y separador `;` para abrir mejor en Excel con configuracion regional uruguaya.

## Columnas

El CSV debe tener estas columnas:

```text
Nombre
Apellido
Telefono
Correo
Fecha_Nacimiento
Consentimiento_Promociones
Producto_1
Monto_1
Producto_2
Monto_2
Producto_3
Monto_3
Producto_4
Monto_4
Producto_5
Monto_5
Producto_6
Monto_6
Observaciones
```

## Campos obligatorios

- `Nombre`
- `Telefono`

El telefono se importa como texto y conserva ceros iniciales.

## Campos opcionales

- `Apellido`
- `Correo`
- `Fecha_Nacimiento`
- `Consentimiento_Promociones`
- `Observaciones`
- Productos y montos de compras historicas.

La fecha de nacimiento acepta `DD/MM/AAAA` y `AAAA-MM-DD`. Puede guardarse aunque el cliente no acepte promociones; las campanas de cumpleaños filtran siempre por consentimiento.

## Consentimiento

`Consentimiento_Promociones` acepta:

```text
SI
SÍ
TRUE
1
NO
FALSE
0
vacio
```

Si la columna no tiene valor, se guarda como `NO`.

## Compras historicas

Cada par `Producto_X` y `Monto_X` representa una compra y un cupon/sticker.

Reglas:

- Producto sin monto genera error.
- Monto sin producto genera error.
- El monto debe ser mayor que cero.
- Se aceptan importes como `1500`, `1500.50`, `1500,50`, `$ 1.500` y `$1.500,50`.
- Las compras se cargan en orden desde `Producto_1` hasta `Producto_6`.
- La cantidad objetivo del ciclo se toma desde Configuracion.

Si el objetivo actual es 6 y una fila tiene 6 compras, se completa el ciclo y se genera el premio por promedio. Si el objetivo actual es 8, esas mismas 6 compras quedan como 6 de 8.

## Duplicados

La deteccion principal usa telefono normalizado.

Opciones para clientes existentes:

- Actualizar campos vacios y agregar compras.
- Solo agregar compras.
- Omitir cliente existente.

La importacion no sobrescribe automaticamente datos existentes no vacios con valores diferentes.

## Evitar cargas repetidas

Cada archivo se registra por hash. Si se vuelve a cargar el mismo archivo, la aplicacion avisa que ya fue importado.

Las compras usan un identificador de operacion estable, por lo que una reimportacion autorizada no duplica compras ya cargadas.

## Flujo recomendado

1. Descargar plantilla.
2. Completar CSV en Excel o similar.
3. Guardar como CSV UTF-8.
4. Seleccionar archivo.
5. Analizar archivo.
6. Revisar vista previa, errores y advertencias.
7. Elegir comportamiento para existentes.
8. Importar registros.
9. Revisar el resumen y descargar el reporte.

## Reporte

La importacion genera un reporte con:

- Fila.
- Resultado.
- Cliente.
- Mensaje.
- ID creado o actualizado.
