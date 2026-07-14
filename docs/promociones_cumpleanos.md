# Promociones de cumpleanos

Club de Compras guarda opcionalmente la fecha de nacimiento de cada cliente para preparar campanas del mes de cumpleanos.

## Carga de fecha

En `Nuevo cliente` y `Editar cliente` el campo `Fecha de nacimiento` permite:

- No informar fecha.
- Elegir una fecha desde calendario.
- Limpiar una fecha cargada.

La fecha debe estar entre `01/01/1900` y el dia actual. No se guarda hora ni se carga la fecha actual por defecto.

La fecha de nacimiento solo puede registrarse si el cliente acepta recibir promociones. Si se retira el consentimiento promocional y existe una fecha cargada, la aplicacion pregunta si tambien debe eliminar la fecha guardada. Si se elige no eliminarla, se cancela el cambio de consentimiento.

Los clientes historicos que tengan fecha de nacimiento sin consentimiento no se modifican automaticamente. Quedan excluidos de la pantalla de cumpleaños y pueden detectarse con `BirthdayPromotionService.inconsistent_customers()`.

## Pantalla Cumpleaños

La seccion `Cumpleaños` muestra:

- Selector de mes, con el mes actual por defecto.
- Buscador por nombre, apellido, telefono o correo.
- Resumen dinamico del mes seleccionado.
- Tarjetas de cantidad total, clientes con telefono, clientes con correo y clientes con premios disponibles.
- Tabla con cliente, dia del cumpleaños, fecha de nacimiento, telefono, correo, ultima compra y premios disponibles.
- Acciones para abrir ficha, editar cliente, ver historial, ver premios disponibles y exportar.

El panel principal solo muestra el total de cumpleaños del mes y un boton para abrir esta seccion. No muestra nombres, telefonos, correos ni textos de consentimiento.

## Filtros disponibles

El servicio `BirthdayPromotionService` permite obtener:

- Clientes que cumplen anos hoy.
- Clientes que cumplen anos esta semana.
- Clientes que cumplen anos este mes.
- Clientes que cumplen anos el proximo mes.
- Clientes por rango de meses.
- Clientes con fecha cargada.
- Clientes sin fecha cargada.

Para campanas promocionales se exige cliente activo, fecha de nacimiento informada y consentimiento para recibir promociones.

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
- Fecha de ultima compra.
- Premios disponibles.

La exportacion no incluye columna visible de consentimiento y solo toma clientes validos para campaña.

## Privacidad

La fecha de nacimiento es un dato personal. No debe incluirse en logs tecnicos, nombres de archivos, repositorios publicos ni datos de demostracion reales.
