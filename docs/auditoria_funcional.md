# Auditoria funcional - Club de Compras

Fecha de auditoria: 2026-07-12

## Verificacion del proyecto

| Item | Valor |
|---|---|
| Ruta absoluta del codigo fuente | `/Users/nicolastumaian/Documents/BellaVita/club_compras` |
| Repositorio Git detectado | `/Users/nicolastumaian/Documents/BellaVita/club_compras` |
| Rama actual | `main` |
| Ultimo commit al iniciar esta auditoria | `5a00ab2 Initial project structure` |
| Remoto GitHub | No configurado (`git remote -v` no devolvio remotos) |
| Base SQLite activa | `/Users/nicolastumaian/Library/Application Support/ClubCompras/data/club_compras.db` |
| Logs | `/Users/nicolastumaian/Library/Application Support/ClubCompras/logs` |
| Backups | `/Users/nicolastumaian/Library/Application Support/ClubCompras/backups` |
| Exportaciones | `/Users/nicolastumaian/Library/Application Support/ClubCompras/exports` |
| App macOS compilada | `/Users/nicolastumaian/Documents/BellaVita/club_compras/dist/Club de Compras.app` |

## Migraciones aplicadas

| Tabla | Cambio | Motivo |
|---|---|---|
| `loyalty_cycles` | `target_purchase_count INTEGER NOT NULL DEFAULT 6` | Conservar el objetivo de compras de cada ciclo aunque cambie la configuracion futura |
| `customers` | `birth_date TEXT NULL` | Guardar fecha de nacimiento opcional sin hora para promociones de cumpleaños |
| `purchases` | Rebuild compatible del check de `sticker_number` a `>= 1` | Permitir ciclos nuevos con mas de 6 stickers |
| `purchase_items` | Rebuild de FK si apuntaba a tabla legacy durante migracion SQLite | Mantener integridad al migrar bases existentes |
| `backup_logs` | Columnas `reason`, `error` y `restored_from` | Registrar respaldos, restauraciones, errores y limpieza |
| `app_settings` | Valores por defecto de tienda, promocion, correo, moneda y carpeta de respaldo | Evitar configuracion fija en codigo |

## Auditoria inicial encontrada

| Pantalla | Boton o accion | Archivo | Accion esperada | Estado inicial |
|---|---|---|---|---|
| Panel principal | Buscar cliente | `app/ui/main_window.py` | Abrir busqueda de clientes | Parcial: mostraba aviso "en desarrollo" |
| Panel principal | Nuevo cliente | `app/ui/main_window.py` | Abrir alta de cliente | Funcional |
| Panel principal | Registrar compra | `app/ui/main_window.py` | Abrir registro de compra | Parcial: mostraba aviso "en desarrollo" |
| Nuevo cliente | Guardar cliente | `app/ui/customer_dialog.py` | Validar y guardar cliente en SQLite | Funcional |
| Nuevo cliente | Cancelar | `app/ui/customer_dialog.py` | Cerrar sin guardar | Funcional |

## Estado despues de Fase 1 y Fase 2

| Pantalla | Boton o accion | Archivo | Accion esperada | Estado actual |
|---|---|---|---|---|
| Panel principal | Buscar cliente | `app/ui/main_window.py` | Abrir pantalla real de busqueda | Funcional |
| Panel principal | Nuevo cliente | `app/ui/main_window.py` | Abrir alta, guardar y abrir ficha | Funcional |
| Panel principal | Registrar compra | `app/ui/main_window.py` | Abrir modulo de compras | Parcial: navega a pantalla preparada para Fase 3 |
| Panel principal | Premios disponibles | `app/ui/main_window.py` | Abrir listado de premios | Parcial: navega a pantalla preparada para Fase 5 |
| Panel principal | Crear copia de seguridad | `app/ui/main_window.py`, `app/ui/backups_page.py` | Abrir modulo de backups | Funcional |
| Busqueda de clientes | Volver | `app/ui/main_window.py` | Regresar al panel principal | Funcional |
| Busqueda de clientes | Nuevo cliente | `app/ui/main_window.py` | Abrir alta y refrescar listado | Funcional |
| Busqueda de clientes | Buscar mientras se escribe | `app/ui/main_window.py` | Filtrar por ID, nombre, apellido, telefono o correo | Funcional |
| Busqueda de clientes | Abrir ficha | `app/ui/main_window.py` | Abrir ficha del cliente seleccionado | Funcional con validacion de seleccion |
| Busqueda de clientes | Doble clic en fila | `app/ui/main_window.py` | Abrir ficha del cliente | Funcional |
| Ficha de cliente | Volver | `app/ui/main_window.py` | Regresar a busqueda | Funcional |
| Ficha de cliente | Editar cliente | `app/ui/main_window.py`, `app/ui/customer_dialog.py` | Editar datos y guardar en SQLite | Funcional |
| Ficha de cliente | Activar/Desactivar cliente | `app/ui/main_window.py` | Cambiar estado logico con confirmacion | Funcional |
| Ficha de cliente | Ver historial | `app/ui/main_window.py` | Abrir historial del cliente | Pantalla inexistente: placeholder de Fase 6 |
| Ficha de cliente | Ciclo actual | `app/ui/main_window.py` | Mostrar carton de fidelizacion | Pantalla inexistente: placeholder de Fase 4 |
| Ficha de cliente | Premios disponibles | `app/ui/main_window.py` | Mostrar premios del cliente | Pantalla inexistente: placeholder de Fase 5 |
| Placeholder | Volver | `app/ui/main_window.py` | Regresar a la pantalla anterior | Funcional |
| Dialogo cliente | Guardar cliente/cambios | `app/ui/customer_dialog.py` | Validar, detectar duplicados y persistir | Funcional |
| Dialogo cliente | Cancelar | `app/ui/customer_dialog.py` | Cerrar sin cambios | Funcional |
| Dialogo cliente | Fecha de nacimiento | `app/ui/customer_dialog.py` | Cargar fecha opcional con calendario, no informar o limpiar fecha | Funcional |

## Estado despues de Fase 3 y Fase 4

| Pantalla | Boton o accion | Archivo | Accion esperada | Estado actual |
|---|---|---|---|---|
| Panel principal | Registrar compra | `app/ui/main_window.py`, `app/ui/purchase_page.py` | Abrir registro real de compra | Funcional |
| Registro de compra | Buscar cliente | `app/ui/purchase_page.py` | Filtrar y seleccionar cliente existente | Funcional |
| Registro de compra | Seleccionar cliente | `app/ui/purchase_page.py` | Mostrar datos, stickers y premios | Funcional |
| Registro de compra | Nuevo cliente | `app/ui/purchase_page.py`, `app/ui/customer_dialog.py` | Crear cliente desde el panel izquierdo y preseleccionarlo | Funcional |
| Registro de compra | Refrescar lista | `app/ui/purchase_page.py` | Recargar tabla de clientes sin salir de la pantalla | Funcional |
| Registro de compra | Modalidad simple | `app/ui/purchase_page.py`, `app/services/purchases.py` | Guardar descripcion e importe total | Funcional |
| Registro de compra | Modalidad detallada | `app/ui/purchase_page.py`, `app/services/purchases.py` | Agregar lineas, calcular subtotales y total | Funcional |
| Registro de compra | Guardar compra | `app/ui/purchase_page.py`, `app/services/purchases.py` | Validar, confirmar, persistir y actualizar ciclo | Funcional |
| Registro de compra | Evitar doble registro | `app/ui/purchase_page.py`, `app/services/purchases.py` | Deshabilitar boton y usar `operation_id` unico | Funcional |
| Ficha de cliente | Ciclo actual | `app/ui/main_window.py`, `app/ui/loyalty_card_page.py` | Abrir carton visual de seis stickers | Funcional |
| Carton de fidelizacion | Registrar nueva compra | `app/ui/loyalty_card_page.py` | Abrir compra con cliente preseleccionado | Funcional |
| Carton de fidelizacion | Ver historial de ciclos | `app/ui/loyalty_card_page.py` | Enfocar lista simple de ciclos | Parcial funcional |
| Carton de fidelizacion | Volver a ficha | `app/ui/loyalty_card_page.py` | Regresar a ficha del cliente | Funcional |

## Estado despues de Fase 5 e historial basico

| Pantalla | Boton o accion | Archivo | Accion esperada | Estado actual |
|---|---|---|---|---|
| Panel principal | Premios disponibles | `app/ui/main_window.py`, `app/ui/rewards_page.py` | Abrir listado real de premios | Funcional |
| Premios disponibles | Buscar | `app/ui/rewards_page.py` | Filtrar por nombre, apellido, telefono o correo | Funcional |
| Premios disponibles | Filtro de estado | `app/ui/rewards_page.py` | Mostrar todos, disponibles, utilizados, vencidos o anulados | Funcional |
| Premios disponibles | Ver premio | `app/ui/rewards_page.py`, `app/ui/reward_dialogs.py` | Abrir ficha completa del premio | Funcional |
| Premios disponibles | Doble clic | `app/ui/rewards_page.py` | Abrir ficha del premio | Funcional |
| Premios disponibles | Canjear premio | `app/ui/rewards_page.py`, `app/ui/reward_dialogs.py`, `app/services/rewards.py` | Canjear premio disponible con validaciones | Funcional |
| Ficha de premio | Canjear premio | `app/ui/reward_dialogs.py` | Abrir dialogo de canje si esta disponible | Funcional |
| Canje de premio | Confirmar canje | `app/services/rewards.py` | Transaccion SQLite, estado utilizado, fecha, prenda, precio, diferencia y auditoria | Funcional |
| Ficha de cliente | Ver historial | `app/ui/main_window.py`, `app/ui/customer_history_page.py` | Mostrar compras, ciclos y premios en pestañas | Funcional |
| Historial cliente | Ver compra | `app/ui/customer_history_page.py` | Mostrar detalle de fila seleccionada | Funcional |
| Historial cliente | Ver ciclo | `app/ui/customer_history_page.py` | Mostrar detalle de fila seleccionada | Funcional |
| Historial cliente | Ver premio | `app/ui/customer_history_page.py` | Abrir ficha del premio seleccionado | Funcional |
| Historial cliente | Registrar nueva compra | `app/ui/customer_history_page.py` | Abrir compra con cliente preseleccionado | Funcional |
| Historial cliente | Canjear premio disponible | `app/ui/customer_history_page.py` | Canjear premio disponible seleccionado | Funcional |
| Panel principal | Indicadores | `app/repositories/dashboard.py`, `app/ui/main_window.py` | Mostrar compras hoy, premios y ciclos próximos | Funcional |

## Estado despues de mejoras de configuracion y flujo post-compra

| Pantalla | Boton o accion | Archivo | Accion esperada | Estado actual |
|---|---|---|---|---|
| Registrar compra | Guardar compra | `app/ui/purchase_page.py`, `app/services/purchases.py` | Guardar, mostrar resumen, limpiar formulario y quedar listo para otra compra | Funcional |
| Registrar compra | Buscador de clientes | `app/ui/purchase_page.py` | Recibir foco despues de guardar | Funcional |
| Registrar compra | Cliente seleccionado | `app/ui/purchase_page.py` | Deseleccionarse despues de guardar | Funcional |
| Panel principal | Configuracion | `app/ui/main_window.py`, `app/ui/settings_page.py` | Abrir configuracion desde engranaje compacto del encabezado, visible solo para admin | Funcional |
| Configuracion | Promocion | `app/ui/settings_page.py`, `app/services/settings.py` | Cambiar objetivo de compras, nombre, descripcion y estado | Funcional |
| Configuracion | Compras necesarias para obtener el premio | `app/ui/settings_page.py` | Mostrar valor claro entre 1 y 50, ayuda contextual y configuracion actual | Funcional |
| Configuracion | Correo promociones | `app/ui/settings_page.py`, `app/services/settings.py` | Guardar datos para futura integracion sin contrasenas | Funcional |
| Configuracion | Datos generales | `app/ui/settings_page.py`, `app/services/settings.py` | Guardar datos de tienda, moneda y textos legales | Funcional |
| Configuracion | Guardar cambios | `app/services/settings.py` | Validar, persistir en `app_settings` y auditar | Funcional |
| Panel principal | Pie de version | `app/ui/main_window.py` | Mostrar texto discreto no clickeable con version centralizada | Funcional |
| Panel principal | Acerca de | `app/ui/main_window.py` | No mostrar boton de acerca de | Eliminado |
| Panel principal | Cumpleaños este mes | `app/repositories/dashboard.py`, `app/ui/main_window.py` | Mostrar tarjeta clickeable con cantidad de clientes activos con cumpleaños y consentimiento, sin datos personales ni contador duplicado | Funcional |
| Panel principal | Cumpleaños | `app/ui/main_window.py`, `app/ui/birthdays_page.py` | Abrir listado mensual desde la tarjeta unica, con busqueda, acciones y exportacion CSV | Funcional |
| Configuracion | Importar clientes | `app/ui/csv_import_page.py`, `app/services/csv_import.py` | Analizar CSV, mostrar vista previa, importar clientes/compras historicas y generar reporte | Funcional |

## Estado despues de fecha de nacimiento y promociones

| Modulo | Archivo | Accion esperada | Estado actual |
|---|---|---|---|
| Clientes | `app/repositories/customers.py`, `app/services/customers.py` | Crear, editar, limpiar y persistir `birth_date` opcional | Funcional |
| Migracion | `app/database/schema.py` | Agregar `birth_date` si falta sin perder clientes existentes | Funcional e idempotente |
| Ficha de cliente | `app/ui/main_window.py` | Mostrar fecha de nacimiento o `No informada` y mes de cumpleaños | Funcional |
| Promociones cumpleaños | `app/services/birthday_promotions.py` | Filtrar por hoy, semana, mes, proximo mes, rango, cliente activo y consentimiento | Funcional |
| Listado cumpleaños | `app/ui/birthdays_page.py` | Mostrar clientes validos del mes, buscar, abrir acciones relacionadas y exportar CSV sin columna de consentimiento | Funcional |
| Exportacion campañas | `app/services/birthday_promotions.py` | Exportar CSV mensual con fecha, dia, mes y datos de contacto | Funcional |

## Estado despues de respaldos y restauracion

| Pantalla | Boton o accion | Archivo | Accion esperada | Estado actual |
|---|---|---|---|---|
| Panel principal | Crear copia de seguridad | `app/ui/main_window.py`, `app/ui/backups_page.py` | Abrir pantalla real de respaldos | Funcional |
| Respaldos | Estado actual | `app/ui/backups_page.py`, `app/services/backups.py` | Mostrar base activa, carpeta, ultimo respaldo, cantidad de copias y estado | Funcional |
| Respaldos | Crear copia ahora | `app/services/backups.py` | Crear copia segura con API de backup SQLite e integridad | Funcional |
| Respaldos | Elegir carpeta de respaldo | `app/ui/backups_page.py`, `app/services/backups.py` | Guardar carpeta configurable en `app_settings` | Funcional |
| Respaldos | Abrir carpeta de respaldos | `app/ui/backups_page.py` | Abrir carpeta con Qt Desktop Services | Funcional |
| Respaldos | Restaurar copia | `app/ui/backups_page.py`, `app/services/backups.py` | Validar copia, crear copia previa, restaurar y auditar | Funcional |
| Respaldos automaticos | Cierre, compra, canje, configuracion | `app/ui/main_window.py`, `app/services/backups.py` | Crear respaldo automatico con limite de 30 minutos | Funcional |
| Limpieza de respaldos | Retencion | `app/services/backups.py` | Conservar ultimas 30 copias sin borrar la unica existente | Funcional |

Eventos auditados:

- `BACKUP_CREATED`
- `BACKUP_FAILED`
- `BACKUP_FOLDER_CHANGED`
- `BACKUP_RESTORED`
- `BACKUP_RESTORE_FAILED`
- `BACKUP_CLEANUP`

## Senales y callbacks revisados

- `QPushButton.clicked.connect(...)` en `app/ui/main_window.py`.
- `QDialogButtonBox.accepted.connect(...)` y `rejected.connect(...)` en `app/ui/customer_dialog.py`.
- `QLineEdit.textChanged.connect(...)` para busqueda en vivo.
- `QTableWidget.doubleClicked.connect(...)` para abrir ficha.
- `QSplitter` en `app/ui/purchase_page.py` para la pantalla de compra en dos columnas.
- `QTableWidget.doubleClicked.connect(...)` en `app/ui/rewards_page.py` para abrir premios.
- `QDialogButtonBox.accepted.connect(...)` en `app/ui/reward_dialogs.py` para confirmar canjes.

## Prueba automatica ejecutada

Comando:

```bash
.venv/bin/python -m pytest
```

Resultado:

```text
52 passed, 1 warning
```

Cobertura funcional actual de pruebas:

- Inicializacion de configuracion.
- Inicializacion de SQLite.
- Creacion de administrador inicial.
- Alta de cliente.
- Validacion de medio de contacto obligatorio.
- Busqueda, edicion y desactivacion de cliente.
- Registro simple y detallado de compras.
- Creacion automatica de ciclo.
- Asignacion de stickers 1 a 6.
- Finalizacion del ciclo en la sexta compra.
- Calculo de total y promedio con Decimal.
- Creacion de premio disponible.
- Inicio automatico del ciclo siguiente.
- Prevencion de doble registro mediante `operation_id`.
- Persistencia de compras, items, ciclos, premios y auditoria.
- Layout de compra con dos columnas, boton guardar deshabilitado sin cliente y cambio de modalidad simple/detallada.
- Listado de premios, filtros, busqueda y canje.
- Validaciones de diferencia pagada y doble canje.
- Historial de compras, ciclos y premios por cliente.
- Dashboard con cifras reales desde SQLite.
- Configuracion central en `app_settings`.
- Objetivo de stickers configurable entre 1 y 50.
- `target_purchase_count` guardado por ciclo.
- Flujo post-compra vuelve a registro vacío y enfoca buscador.
- Configuracion muestra claramente compras necesarias para obtener el premio.
- Fecha de nacimiento opcional, validaciones, migracion y filtros de cumpleaños.
- Respaldos manuales, carpeta no disponible, limpieza y restauracion.
- Auditoria de respaldo y restauracion.
- Eliminacion del boton `Acerca de` y pie de version no clickeable.

## Prueba manual documentada

Comando de apertura en desarrollo:

```bash
cd /Users/nicolastumaian/Documents/BellaVita/club_compras
source .venv/bin/activate
python -m app.main
```

Flujo probado:

1. La ventana principal abre correctamente.
2. `Buscar cliente` abre una pantalla real de clientes.
3. `Nuevo cliente` abre formulario.
4. Guardar cliente valida campos obligatorios y persiste en SQLite.
5. Al guardar, se abre la ficha del cliente.
6. `Editar cliente` permite modificar y guardar.
7. `Activar/Desactivar cliente` solicita confirmacion y actualiza estado.
8. `Volver` regresa a la pantalla anterior.
9. `Registrar compra` abre una pantalla real.
10. Se puede seleccionar un cliente activo y registrar compra simple o detallada.
11. La sexta compra completa el ciclo y genera premio disponible.
12. `Ciclo actual` muestra seis stickers, total, promedio, faltantes e historial simple.
13. `Registrar compra` usa dos columnas: clientes a la izquierda y formulario a la derecha.
14. La columna derecha mantiene el boton guardar accesible mediante scroll en resoluciones bajas.
15. `Premios disponibles` abre listado real con filtros.
16. Canje de premio menor al valor permitido queda utilizado y desaparece de disponibles.
17. Diferencia insuficiente se rechaza y diferencia correcta se acepta.
18. `Ver historial` muestra compras, ciclos y premios del cliente.
19. Despues de registrar una compra la pantalla queda lista para otro cliente.
20. Configuracion permite cambiar el objetivo para ciclos nuevos sin alterar ciclos existentes.
21. Configuracion muestra `Compras necesarias para obtener el premio`, ayuda contextual y valor legible.
22. Respaldos abre pantalla real con base activa, carpeta y estado.
23. Crear copia genera un archivo `club_compras_YYYY-MM-DD_HHMMSS.db`.
24. Restaurar copia valida integridad y crea copia previa.
25. El panel principal ya no muestra boton `Acerca de`; muestra pie de version discreto.
25.1. Configuracion se abre desde un engranaje compacto del encabezado y no ocupa una tarjeta grande.
25.2. El panel principal tiene un unico acceso a cumpleaños mediante tarjeta clickeable.
26. Nuevo cliente permite guardar sin fecha de nacimiento.
27. Editar cliente permite agregar y limpiar fecha de nacimiento.
28. Ficha de cliente muestra fecha o `No informada` y mes de cumpleaños.
29. Servicio de promociones filtra cumpleaños por dia, semana, mes, cliente activo y consentimiento.
30. Exportacion CSV de cumpleaños incluye fecha y mes, sin columna visible de consentimiento.
31. `Cumpleaños` muestra una lista completa, buscable y exportable desde el panel principal.
32. `Importar clientes` permite carga masiva CSV con plantilla, vista previa, control de duplicados, compras historicas y auditoria.

Flujo manual controlado de Fase 3/4:

1. Cliente temporal `Demo Fase34`.
2. Compras: 1000, 1500, 2000, 1200, 1800, 1500.
3. Resultado: total `9000.00`, promedio `1500.00`, premio disponible `1500.00`.
4. Septima compra: ciclo `2`, sticker `1`.
5. Premio del ciclo 1 continua disponible.

## Plan de implementacion pendiente

| Fase | Alcance | Estado |
|---|---|---|
| Fase 1 - Navegacion principal | Botones reales, volver, evitar pantallas duplicadas | Completada para navegacion base |
| Fase 2 - Clientes | Buscar, nuevo, editar, ficha, activar/desactivar, duplicados, resumen de historial/ciclo/premios | Completada parcialmente: historial y premios detallados siguen en fases posteriores |
| Fase 3 - Compras | Registro de compras, productos, total, ciclo correcto, evitar doble clic | Completada |
| Fase 4 - Carton | Seis stickers, promedio parcial, completar ciclo y premio | Completada |
| Fase 5 - Premios | Listado, ficha, canje, validaciones y doble canje | Completada |
| Fase 6 - Historial y correcciones | Compras, ciclos, premios, anulacion, auditoria | Parcial: historial basico completado; correcciones/anulaciones pendientes |
| Fase 7 - Reportes | Filtros, metricas, exportacion CSV/Excel | Parcial: exportacion CSV de cumpleaños implementada |
| Fase 8 - Configuracion y seguridad | Usuarios, roles, promociones, moneda, backups, auditoria | Parcial: configuracion admin y auditoria de respaldos implementadas; usuarios/roles avanzados pendientes |
| Fase 9 - Backups | Crear/restaurar, Google Drive, ultimo backup | Completada para carpeta local o sincronizada |
