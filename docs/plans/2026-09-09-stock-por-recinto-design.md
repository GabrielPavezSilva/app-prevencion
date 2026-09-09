# Stock de EPP por recinto

Fecha: 2026-09-09
Estado: aprobado, en implementación
Rama: `feature/stock-por-recinto`

## Problema

El stock es **global** por diseño: `stock_epp` tiene `UNIQUE(producto_id, talla_id)`
y el modelo lo documenta como "un solo bodegón, sin segregación por empresa".

La operación real tiene tres recintos —**Las Encinas**, **Lucerna** y
**Malloco**— con bodega propia cada uno. Un stock global no puede responder la
pregunta que importa antes de entregar: *¿hay casco talla L acá, o está en otro
recinto?*

## Decisiones

| # | Decisión | Alternativas descartadas |
|---|---|---|
| D1 | Tabla `recintos` + FK `recinto_id` | `VARCHAR` con `CHECK`: **no hay sistema de migraciones**, y un cuarto recinto sería un `ALTER` a mano en producción en vez de un `INSERT`. Reusar `empresa`/`areas`: las pisa el sync de RRHH cada noche y no sabe de recintos |
| D2 | El recinto de una entrega sale del **usuario que la registra** (`usuarios.recinto_id`) | Selector libre en el carrito (error humano: descontar del recinto equivocado). Recinto del trabajador (`personal` no tiene el campo y habría que ver si RRHH lo expone) |
| D3 | Todos **ven** los 3 recintos; cada uno **mueve** solo el suyo | Ver solo el propio: esconde justo el dato que sirve para pedir un traslado |
| D4 | `entregas_epp` denormaliza `recinto_id` | Derivarlo del `MovimientoStock` tipo `ENTREGA` obliga a joinear por `referencia_id` en cada reporte, y repite la deuda ya anotada con el área |
| D5 | Borrón completo del dominio EPP antes de migrar | Asignar lo existente a un recinto dejaba cantidades mal atribuidas; lo cargado era de prueba |

D4 reemplaza al invariante "stock global" de CLAUDE.md, que queda obsoleto.

## Esquema

Tabla nueva:

```
recintos(recinto_id PK, nombre_recinto UNIQUE, activo)
```

Seed idempotente con los tres. Sin CRUD: un cuarto recinto es un `INSERT`, no
una pantalla.

Columnas nuevas:

| Tabla | Columna | Nulabilidad | Por qué |
|---|---|---|---|
| `stock_epp` | `recinto_id` | `NOT NULL` | No puede existir stock sin recinto |
| `movimientos_stock` | `recinto_id` | `NOT NULL` | El libro mayor se reconstruye por recinto |
| `entregas_epp` | `recinto_id` | `NOT NULL` | D4 |
| `usuarios` | `recinto_id` | `NULL` | Los roles de `FULL_ACCESS_ROLES` no tienen recinto |

**El cambio de fondo es la identidad de una fila de stock.** Hoy
`(producto_id, talla_id)` la identifica en seis lugares: el `UNIQUE`,
`epp_repository.get_stock_row`, `get_stock_detalle`, `ajustar_stock`,
`entregas_repository._get_stock_row` y el upsert de
`importaciones_repository`. Pasa a `(producto_id, talla_id, recinto_id)`.

El `talla_id IS NOT DISTINCT FROM :talla_id` se mantiene intacto —
`recinto_id` es `NOT NULL` y va con `=` normal.

## Permisos

D3 se implementa en el **service**, no en el endpoint: `require_module` sigue
controlando el acceso al módulo y una función nueva en `app/core/security.py`
resuelve el recinto:

```
resolver_recinto(current_user, recinto_id_pedido) -> int
```

| Caso | Resultado |
|---|---|
| Rol en `FULL_ACCESS_ROLES` | Puede pasar cualquier `recinto_id`, pero es **obligatorio**: sin recinto propio no hay default, así que `400` si no lo manda |
| Usuario con `recinto_id` | Se usa el suyo; `403` si pidió otro explícitamente, para que no falle en silencio |
| Usuario sin recinto y sin bypass | `403` hasta que un superadmin le asigne recinto |

Las lecturas no pasan por acá: el listado de stock trae los tres recintos.

El JWT suma `recinto_id` y `nombre_recinto`, igual que ya lleva `modulos`, y
`UserResponse` los expone para que la UI sepa qué prellenar y qué
deshabilitar. **Los tokens vigentes no los traen: hay que volver a loguearse.**

## Importaciones

`stock_inicial` e `ingreso_stock` suman una columna `Recinto` obligatoria. La
fila resuelve nombre → `recinto_id`; un nombre desconocido es error de fila y
el detalle lista los válidos.

Las dos plantillas ya son todo o nada (`_ATOMICOS`), así que un recinto mal
escrito revierte el archivo completo — correcto acá: un ingreso repartido a
medias entre recintos es peor que ninguno.

Cada fila pasa por `resolver_recinto`, así que un usuario de Lucerna no puede
cargar stock a Malloco ni por Excel.

## UI

- **Inventario / tab Stock**: "Recinto" como primera columna, más un selector
  para filtrar (`Todos` por defecto). Orden: recinto → producto → talla.
- **Modal de stock y de ajuste**: campo Recinto, prellenado con el del usuario
  y deshabilitado; editable y obligatorio solo para admin.
- **Entregas**: la tarjeta del carrito muestra de qué recinto sale el
  descuento — selector para admin, texto fijo para el resto. El stock
  disponible se filtra por ese recinto.
- **SuperAdmin**: asignar recinto al crear/editar usuario. Sin esto la feature
  no arranca: nadie tiene recinto todavía.
- `AuthContext` expone `recinto_id` / `nombre_recinto`.

## Verificación

Patrón del repo (Service → Repository sobre un Postgres efímero, sin pytest):
`tests/smoke_recintos.py`.

1. El mismo producto+talla convive en dos recintos sin chocar contra el `UNIQUE`.
2. Una entrega descuenta solo el stock de su recinto.
3. Un usuario de Lucerna recibe `403` al mover Malloco.
4. Un admin sin `recinto_id` recibe `400`.
5. Una importación con recinto inválido revierte completa.

`tests/smoke_importaciones.py` se extiende con la columna nueva.

## Migración

No hay sistema de migraciones: el script va versionado en
`Backend/migrations/` y se corre a mano en cada ambiente.

## Fuera de alcance

- **Traslados entre recintos** (`MovimientoStock` tipo `TRASLADO`). Con tres
  bodegas separadas va a hacer falta, pero no está en el pedido y cada recinto
  puede cargar por importación mientras tanto.
- Pantalla de CRUD de recintos.
- Stock mínimo por recinto: ya lo es, vive en la fila de `stock_epp`.
