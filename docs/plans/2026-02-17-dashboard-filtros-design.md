# Dashboard — Filtros por Tipo y Talla

**Fecha:** 2026-02-17
**Estado:** Aprobado

## Contexto

El panel de control muestra estadísticas globales del inventario (total, disponibles, en uso) con tres gráficos: dona (disponible/en uso), barras por tipo de prenda, barras por talla. Se requiere agregar filtros para ver esas mismas estadísticas segmentadas por tipo de prenda y, opcionalmente, por talla dentro de ese tipo.

## Decisiones de diseño

- **Trigger del filtro:** Dropdown selector (siempre visible para tipos; aparece para tallas solo tras seleccionar un tipo)
- **Gráfico de tipos al filtrar:** Se oculta (no tiene sentido mostrar distribución por tipos cuando ya se filtró por uno)
- **Filtro de talla:** Aparece dinámicamente después de seleccionar un tipo; sus opciones se alimentan del campo `por_talla` de la respuesta filtrada
- **Enfoque backend:** Opción A — endpoint parametrizado (`GET /api/stats/inventario?tipo_id=X&talla_id=Y`)

## Backend

### Cambios en `app/api/v1/endpoints/stats.py`

Agregar query params opcionales al endpoint existente:

```
GET /api/stats/inventario                       → totales globales
GET /api/stats/inventario?tipo_id=1             → totales para ese tipo
GET /api/stats/inventario?tipo_id=1&talla_id=2  → totales para tipo + talla
```

Las tres queries SQL incorporan `WHERE` dinámico:

- **Resumen** (`total`, `disponibles`, `en_uso`, `con_rfid`, `sin_rfid`): filtra por `TipoID` y/o `TallaID` cuando están presentes
- **Por tipo** (`por_tipo`): siempre global (el chart de tipos no se renderiza cuando hay filtro, pero el schema no cambia)
- **Por talla** (`por_talla`): filtra por `tipo_id` cuando está presente (para mostrar tallas dentro de ese tipo); nunca filtra por `talla_id`

El schema `InventarioStatsResponse` no cambia.

## Frontend

### Nuevos componentes / cambios

**`src/services/statsService.js`**
- `getStatsInventario(tipoId = null, tallaId = null)` — construye query string con los params no-nulos

**`src/pages/Dashboard.jsx`**

Estado nuevo:
- `tipoId` (number | null)
- `tallaId` (number | null)
- `tipos` (array de `{TipoID, nombreTipo}`) — catálogo completo

Nueva barra de filtros entre KPI cards y gráficos:
```
[ Tipo de prenda ▼ ]   [ Talla ▼ ]   [✕ Limpiar filtros]
```

Visibilidad de gráficos:

| Estado | DonutChart | BarChart Tipos | BarChart Tallas |
|---|---|---|---|
| Sin filtro | ✓ | ✓ | ✓ |
| Tipo seleccionado | ✓ | oculto | ✓ |
| Tipo + Talla | ✓ | oculto | oculto |

Flujo al cambiar filtros:
1. Cambio en dropdown de tipo → reset `tallaId` a null → `cargar(nuevoTipoId, null)`
2. La respuesta incluye `por_talla` filtrado por tipo → poblar opciones del dropdown de talla
3. Cambio en dropdown de talla → `cargar(tipoId, nuevaTallaId)`
4. Carga inicial en paralelo: `getTipos()` + `getStatsInventario()`

**`src/pages/Dashboard.css`**
- `.dashboard-filters`: flexbox con gap para la barra de filtros
- `.dashboard-charts` pasa a tener columnas dinámicas (3/2/1) según charts visibles — manejado con clases condicionales o inline style

## Manejo de errores y casos borde

- **Tipo sin stock en ninguna talla:** `por_talla` vacío → dropdown de talla muestra "Sin tallas disponibles" deshabilitado
- **`total = 0` con filtros:** KPI cards en 0, DonutChart muestra "Sin datos disponibles" (ya implementado)
- **Error de red en re-fetch:** estado de error existente aplica; "Reintentar" re-ejecuta `cargar()` con filtros activos
- **Fallo al cargar catálogo de tipos:** dropdowns vacíos, gráficos globales siguen funcionando

## Fuera de alcance

- Filtro por estado (disponible/en uso)
- Filtro por presencia de tag RFID
- Persistencia de filtros entre sesiones
