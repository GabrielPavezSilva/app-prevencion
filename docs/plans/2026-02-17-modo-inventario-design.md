# Modo Inventario RFID — Documento de Diseño

**Fecha:** 2026-02-17
**Estado:** Aprobado

## Objetivo

Implementar un modo de lectura continua RFID que permita escanear chips y crear automáticamente prendas en inventario asociadas a una categoría (TipoID) y talla (TallaID) seleccionadas previamente. Incluye un modo de ajuste para modificar/desvincular categorías.

## Modelo de Datos

**No se crean tablas nuevas.** Se reutiliza la tabla `inventario` existente.

Cada EPC escaneado crea un registro nuevo en `inventario`:
- `SKU` — generado automáticamente con formato `{PREFIJO_TIPO}-{CORRELATIVO}` (ej: `PANT_BLANCO-0001`)
- `TipoID` — categoría seleccionada al iniciar sesión
- `TallaID` — talla seleccionada al iniciar sesión
- `TagEPC` — EPC del chip escaneado
- `EstadoDisponible` — `True` por defecto

**Estado de sesión (en memoria, no en BD):**

```python
{
    "activo": True,
    "tipo_id": 3,
    "talla_id": 2,
    "epcs_sesion": set(),  # para deduplicación
    "inicio": datetime
}
```

El set `epcs_sesion` evita duplicados: si el lector re-detecta el mismo chip durante la sesión, se ignora.

## Generación de SKU

1. Obtener `nombreTipo` de `tiposPrendas` por `TipoID`
2. Convertir a prefijo: mayúsculas, espacios → `_` (ej: `pantalon blanco` → `PANTALON_BLANCO`)
3. Buscar último SKU con ese prefijo en `inventario` via `LIKE '{prefijo}-%'`
4. Incrementar correlativo: `PANTALON_BLANCO-0001`, `PANTALON_BLANCO-0002`, etc.

## Endpoints

### Modo Inventario

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/rfid/inventario/iniciar` | Inicia sesión. Body: `{tipo_id, talla_id}` |
| `POST` | `/api/rfid/inventario/detener` | Detiene sesión. Retorna resumen |
| `GET` | `/api/rfid/inventario/estado` | Estado actual de la sesión |
| `POST` | `/api/rfid/inventario/scan` | Escanea tag y crea prenda si sesión activa |

### Modo Ajuste

| Método | Ruta | Descripción |
|--------|------|-------------|
| `PATCH` | `/api/rfid/inventario/prenda/{sku}` | Actualiza tipo_id y/o talla_id |
| `DELETE` | `/api/rfid/inventario/prenda/{sku}/tag` | Desvincula TagEPC (NULL) |

## Flujo de Scan (Polling)

1. Frontend llama `POST /inventario/scan` cada ~500ms
2. Backend verifica sesión activa → si no, retorna error
3. `reader_manager.scan()` → obtiene EPC
4. Si no hay tag → `{encontrado: false}`
5. Si EPC ya está en `epcs_sesion` → `{encontrado: true, duplicado: true, epc: "..."}`
6. Si EPC ya existe en `inventario.TagEPC` → `{encontrado: true, duplicado: true}` (ya registrado previamente)
7. Si EPC es nuevo → genera SKU, INSERT en inventario, agrega a set → retorna prenda creada

## Frontend

**Nueva página** "Modo Inventario" (ruta `/inventario-rfid`, solo admin).

Componentes:
- **SelectorCategoria** — dropdown con `tiposPrendas`
- **SelectorTalla** — dropdown con `tallas`
- **BotonInventario** — toggle iniciar/detener
- **TablaChipsLeidos** — tabla en tiempo real (SKU, EPC, categoría, talla, hora)
- **ContadorResumen** — total de prendas registradas en la sesión

Flujo:
1. Seleccionar categoría + talla
2. "Iniciar Inventario" → `POST /inventario/iniciar` + setInterval 500ms
3. Cada scan exitoso agrega fila a la tabla
4. "Detener" → `POST /inventario/detener` + clearInterval

Vista de ajuste: botón "Ajustar" por prenda en la vista de inventario existente.
