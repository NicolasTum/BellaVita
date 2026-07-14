# Promociones de cumpleanos

Club de Compras guarda opcionalmente la fecha de nacimiento de cada cliente para preparar campanas del mes de cumpleanos.

## Carga de fecha

En `Nuevo cliente` y `Editar cliente` el campo `Fecha de nacimiento` permite:

- No informar fecha.
- Elegir una fecha desde calendario.
- Limpiar una fecha cargada.

La fecha debe estar entre `01/01/1900` y el dia actual. No se guarda hora ni se carga la fecha actual por defecto.

## Filtros disponibles

El servicio `BirthdayPromotionService` permite obtener:

- Clientes que cumplen anos hoy.
- Clientes que cumplen anos esta semana.
- Clientes que cumplen anos este mes.
- Clientes que cumplen anos el proximo mes.
- Clientes por rango de meses.
- Clientes con fecha cargada.
- Clientes sin fecha cargada.

Para campanas promocionales se puede exigir:

- Cliente activo.
- Consentimiento para recibir promociones.
- Telefono o correo disponible.

La comparacion usa dia y mes. El ano de nacimiento no se usa para decidir si corresponde una campana.

## Exportacion

La exportacion mensual genera un CSV con:

- Nombre.
- Apellido.
- Fecha de nacimiento.
- Dia de cumpleanos.
- Mes de cumpleanos.
- Telefono.
- Correo.
- Consentimiento promocional.
- Fecha de ultima compra.
- Premios disponibles.

## Privacidad

La fecha de nacimiento es un dato personal. No debe incluirse en logs tecnicos, nombres de archivos, repositorios publicos ni datos de demostracion reales.
