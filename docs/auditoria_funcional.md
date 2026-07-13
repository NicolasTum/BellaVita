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
| Panel principal | Crear copia de seguridad | `app/ui/main_window.py` | Abrir modulo de backups | Parcial: navega a pantalla preparada para Fase 9 |
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
33 passed
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
| Fase 7 - Reportes | Filtros, metricas, exportacion CSV/Excel | Pendiente |
| Fase 8 - Configuracion y seguridad | Usuarios, roles, promociones, moneda, backups, auditoria | Pendiente |
| Fase 9 - Backups | Crear/restaurar, Google Drive, ultimo backup | Pendiente |
