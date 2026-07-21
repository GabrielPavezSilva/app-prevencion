# Diseño: Panel de Control con Estadísticas de Inventario

**Fecha:** 2026-02-17
**Rama:** incorporacion_categorias
**Estado:** Aprobado

---

## Contexto

El Dashboard existe con componentes (`MetricCard`, `BarChart`, `AlertsPanel`) pero sus 3 endpoints de datos no existen en el backend (`/api/stats/inventory`, `/api/inventory/categories/levels`, `/api/alerts/recent`). El panel siempre mostraba ceros. Las tablas `inventario`, `tiposPrendas` y `tallas` tienen la estructura necesaria para calcular estadísticas reales.

---

## Objetivo

Conectar el Dashboard a datos reales del inventario mediante un endpoint unificado de estadísticas, con datos de prueba (seed SQL) para desarrollo.

---

## Decisiones de diseño

| Decisión | Elección | Razón |
|---|---|---|
| Dominio de stats | Inventario | Prioridad del usuario |
| Estrategia de datos ficticios | Seed SQL | El backend siempre retorna datos reales |
| Endpoint | Un único `GET /api/stats/inventario` | Una sola llamada, fácil de mantener |
| Router | Nuevo `/stats` dedicado | Escalable para futuros stats de personal/asignaciones |
| Visualizaciones | Barras por tipo + Barras por talla + Dona disponible/en uso | Selección del usuario |

---

## Arquitectura Backend

### Queries SQL (principios OLAP del database-schema-designer)

Queries directas con `text()` — sin ORM para agregaciones, más eficiente:

```sql
-- Q1: Resumen general (una sola pasada sobre inventario)
SELECT
  COUNT(*)                    AS total,
  SUM(EstadoDisponible = 1)   AS disponibles,
  SUM(EstadoDisponible = 0)   AS en_uso,
  SUM(TagEPC IS NOT NULL)     AS con_rfid,
  SUM(TagEPC IS NULL)         AS sin_rfid
FROM inventario;

-- Q2: Stock por tipo de prenda
SELECT t.nombreTipo AS nombre, COUNT(*) AS cantidad
FROM inventario i
JOIN tiposPrendas t ON i.TipoID = t.TipoID
GROUP BY t.TipoID, t.nombreTipo
ORDER BY cantidad DESC;

-- Q3: Stock por talla
SELECT ta.nombreTalla AS nombre, COUNT(*) AS cantidad
FROM inventario i
JOIN tallas ta ON i.TallaID = ta.TallaID
GROUP BY ta.TallaID, ta.nombreTalla
ORDER BY cantidad DESC;
```

### Respuesta del endpoint

```json
GET /api/stats/inventario → 200
{
  "total": 120,
  "disponibles": 85,
  "en_uso": 35,
  "con_rfid": 98,
  "sin_rfid": 22,
  "por_tipo": [{"nombre": "Camisa", "cantidad": 45}, ...],
  "por_talla": [{"nombre": "M", "cantidad": 38}, ...]
}
```

### Archivos backend

| Archivo | Rol | Acción |
|---|---|---|
| `app/schemas/stats.py` | Pydantic `InventarioStatsResponse` | Nuevo |
| `app/api/v1/endpoints/stats.py` | Router con `GET /inventario` | Nuevo |
| `app/api/v1/api.py` | Registrar router `/stats` | Modificar |

### Seed SQL

**`SQL/seed_datos_prueba.sql`** — usa `INSERT IGNORE` para idempotencia:
- 5 tipos de prenda: Camisa, Pantalón, Chaqueta, Polera, Overol
- 5 tallas: XS, S, M, L, XL
- ~50 prendas con distribución variada de tipo, talla, `EstadoDisponible` y `TagEPC`

---

## Arquitectura Frontend

### Nuevo layout Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  Tarjetas KPI (fila 3 columnas)                         │
│  [Total Prendas]  [Disponibles]  [En Uso]               │
├─────────────────────────────────────────────────────────┤
│  Gráficos (fila 3 columnas)                             │
│  [Dona: Disp/En uso]  [Barras: por Tipo]  [Barras: por Talla] │
└─────────────────────────────────────────────────────────┘
```

`AlertsPanel` y `FingerprintControl` eliminados del dashboard (sin datos reales).

### Nuevo componente

**`Frontend/src/components/dashboard/DonutChart.jsx`**
- Usa `recharts` (ya instalado): `PieChart`, `Pie`, `Cell`, `Tooltip`, `Legend`
- Verde (#22c55e) = disponibles, Rojo (#ef4444) = en uso
- `innerRadius=60`, `outerRadius=90`

### Nuevo servicio

**`Frontend/src/services/statsService.js`**
```javascript
export const getStatsInventario = () => apiClient.get('/stats/inventario');
```

### Cambios en Dashboard.jsx

- Reemplaza 3 fetch fallidos por un solo `getStatsInventario()`
- `por_tipo` → `BarChart` existente (sin cambios en ese componente)
- `por_talla` → segundo `BarChart` (color azul para diferenciar)
- `disponibles` / `en_uso` → nuevo `DonutChart`
- 3 tarjetas: `total`, `disponibles`, `en_uso` (sin % cambio — no hay historial temporal)

### Archivos frontend

| Archivo | Rol | Acción |
|---|---|---|
| `src/services/statsService.js` | `getStatsInventario()` | Nuevo |
| `src/components/dashboard/DonutChart.jsx` | Gráfico dona | Nuevo |
| `src/pages/Dashboard.jsx` | Un fetch, nuevo layout | Modificar |

---

## Estados y manejo de errores

| Estado | UI |
|---|---|
| `loading` | Skeleton de tarjetas grises |
| `error` | Mensaje + botón "Reintentar" |
| Datos vacíos (sin seed) | Mensaje "Sin datos disponibles" en gráficos |
| Datos reales | Tarjetas + 3 gráficos normalmente |

---

## Fuera de alcance (este sprint)

- Stats de personal (por empresa, área, biométrico)
- Stats de asignaciones (requiere registrar router en api.py + timestamps)
- Stats de RFID en tiempo real
- Alertas automáticas (bajo stock, devoluciones pendientes)
- Actualización automática (polling/websocket)
