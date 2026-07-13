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

## Senales y callbacks revisados

- `QPushButton.clicked.connect(...)` en `app/ui/main_window.py`.
- `QDialogButtonBox.accepted.connect(...)` y `rejected.connect(...)` en `app/ui/customer_dialog.py`.
- `QLineEdit.textChanged.connect(...)` para busqueda en vivo.
- `QTableWidget.doubleClicked.connect(...)` para abrir ficha.

## Prueba automatica ejecutada

Comando:

```bash
.venv/bin/python -m pytest
```

Resultado:

```text
6 passed
```

Cobertura funcional actual de pruebas:

- Inicializacion de configuracion.
- Inicializacion de SQLite.
- Creacion de administrador inicial.
- Alta de cliente.
- Validacion de medio de contacto obligatorio.
- Busqueda, edicion y desactivacion de cliente.

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

## Plan de implementacion pendiente

| Fase | Alcance | Estado |
|---|---|---|
| Fase 1 - Navegacion principal | Botones reales, volver, evitar pantallas duplicadas | Completada para navegacion base |
| Fase 2 - Clientes | Buscar, nuevo, editar, ficha, activar/desactivar, duplicados, resumen de historial/ciclo/premios | Completada parcialmente: historial/ciclo/premios muestran placeholders hasta sus fases |
| Fase 3 - Compras | Registro de compras, productos, total, ciclo correcto, evitar doble clic | Pendiente |
| Fase 4 - Carton | Seis stickers, promedio parcial, completar ciclo y premio | Pendiente |
| Fase 5 - Premios | Listado, ficha, canje, validaciones y doble canje | Pendiente |
| Fase 6 - Historial y correcciones | Compras, ciclos, premios, anulacion, auditoria | Pendiente |
| Fase 7 - Reportes | Filtros, metricas, exportacion CSV/Excel | Pendiente |
| Fase 8 - Configuracion y seguridad | Usuarios, roles, promociones, moneda, backups, auditoria | Pendiente |
| Fase 9 - Backups | Crear/restaurar, Google Drive, ultimo backup | Pendiente |
