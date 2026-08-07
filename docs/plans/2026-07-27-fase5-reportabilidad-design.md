# Fase 5 — Reportabilidad y dashboard EPP

Fecha: 2026-07-27 · Rama: `fase-4` → `fase-5`
Precede: Fase 4 (sync de personal desde RRHH). Plan maestro: `2026-07-21-clon-prevencion-epp-design.md`.

## Estado del que se parte

| Artefacto | Estado real |
|---|---|
| `app/api/v1/endpoints/reportes.py` | **Registrado** en `api.py` y roto: consulta `lecturas_rfid`, `tiposprendas`, `secciones`, `temporadas` (tablas eliminadas en Fase 1). Además **sin ninguna dependencia de auth** — `POST /reportes/importar/{template_id}` es escritura masiva sin token. |
| `app/api/v1/endpoints/stats.py` | Registrado y roto por la misma razón. |
| `ReportesRepository` | 100% dominio lavandería. Se reescribe de cero. |
| `ReportesService` | `ExcelReportBuilder` (líneas 12-75) es reutilizable; el resto se descarta. |
| `POST /reportes/importar` | Obsoleto — lo reemplazó `/api/importaciones` en Fase 3. Se elimina. |
| `Frontend/src/pages/Dashboard.jsx` | Dominio viejo, muestra error. Andamiaje reutilizable. |
| `Frontend/src/pages/Reports.jsx` | 90% mock (`RecentExportsTable`, `downloadTemplate`, botones PDF falsos). |

## Principio estructural

**Una query por reporte, dos presentaciones.** El repository devuelve `List[dict]`; el endpoint JSON lo serializa y el endpoint `.xlsx` pasa las mismas filas por el builder de Excel. La tabla en pantalla y el archivo exportado no pueden divergir.

## Zona horaria (decisión Q9)

`entregas_epp.fecha_entrega` es `TIMESTAMP WITHOUT TIME ZONE` con `server_default=now()`. El negocio opera en Chile (UTC-4/-3).

Sin conversión, una entrega del 31 de julio a las 21:00 hora chilena **cae en el mes equivocado** en todo corte mensual.

**Corrección posterior (2026-07-28).** El diseño original asumía que la BD guardaba UTC, basándose en el contenedor de desarrollo `pg-prevencion`. Eso resultó ser una propiedad del entorno, no del sistema: al guardar un `timestamptz` en una columna sin zona, PostgreSQL convierte **según la zona de la sesión**. El contenedor de desarrollo corre en UTC pero `compose.yml` arranca Postgres con `timezone=America/Santiago`, así que el mismo instante quedaba almacenado con 4 horas de diferencia entre entornos y los reportes salían corridos en producción.

La decisión final tiene dos mitades:

1. **La conexión fija su zona en UTC** — `connect_args={"options": "-c timezone=UTC"}` en `app/db/session_mysql.py`. El almacenamiento es UTC en todos los entornos, sea cual sea la configuración del servidor.
2. **La conversión ocurre en un solo lugar**, la constante `FECHA_LOCAL` del repository, para que no se olvide en ninguna query nueva:

```sql
(e.fecha_entrega AT TIME ZONE 'UTC') AT TIME ZONE 'America/Santiago'
```

`tests/smoke_reportes.py` verifica ambas mitades: el borde de mes con un timestamp literal, y que una entrega recién creada (camino `now()`, el que depende de la zona de la sesión) se reporte en la hora local correcta. El smoke corre en verde contra un servidor en UTC y contra uno en `America/Santiago`.

---

## Reportes

### R1 · Trazabilidad de entregas (requisito #1 del negocio)

Grano: 1 fila por `entregas_epp`.

Filtros: `desde`, `hasta`, `motivo`, `empresa_id`, `area_id`, `subarea_id`, `producto_id`, `categoria_id`, `rut`.

Columnas: Fecha · RUT · Trabajador · Empresa · Área · Subárea · Cargo · Categoría · Producto · Talla · Cantidad · Motivo · Reemplaza a (id + fecha, solo sustituciones) · Observación · Registró.

Reemplaza al reporte de pérdidas que hoy se maneja por correo.

### R2 · EPP vigentes por trabajador (reporte general)

Grano: 1 fila por (trabajador × EPP vigente). **`LEFT JOIN`**: los trabajadores sin ningún EPP aparecen con la fila en blanco y `sin_epp = true` (Q3) — saber quién está descubierto es la mitad del valor del reporte.

Hoja 2 "Resumen": 1 fila por persona, `COUNT` de vigentes + `string_agg` de productos.

Filtros: `empresa_id`, `area_id`, `subarea_id`, `producto_id`, `categoria_id`, `incluir_inactivos` (default `false`).

Definición de vigente: entrega sin reemplazo posterior — `NOT EXISTS (SELECT 1 FROM entregas_epp r WHERE r.entrega_reemplazada_id = e.entrega_id)`, igual que `get_vigentes_por_rut`.

### R3 · Stock y quiebres

Grano: 1 fila por `stock_epp` (producto × talla).

Columnas: Categoría · Producto · Talla · Cantidad actual · Stock mínimo · Déficit · Estado · Consumo 90 días · Cobertura estimada (días).

- Estado: `QUIEBRE` si `cantidad_actual = 0`; `BAJO` si `<= stock_minimo`; `OK` en otro caso.
- Consumo 90 días: `SUM(-cantidad)` de `movimientos_stock` tipo `ENTREGA` en la ventana.
- Cobertura: `cantidad_actual / (consumo_90 / 90)`, `NULL` si no hubo consumo.

**"Valorizado" queda fuera de la fase**: no existe precio en `productos_epp` (Q5).

---

## Endpoints

Router `/api/reportes` reescrito de cero. **Todos con `require_module("reportes")`.**

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/reportes/entregas` | JSON |
| GET | `/reportes/entregas.xlsx` | `StreamingResponse` |
| GET | `/reportes/epp-vigentes` · `.xlsx` | ídem |
| GET | `/reportes/stock` · `.xlsx` | ídem |

Rutas gemelas en vez de `?formato=`: `response_model` y `StreamingResponse` no conviven bien en una misma ruta. Ambas llaman al mismo método de service, así que no hay lógica duplicada. Como la auth es por cookie httpOnly, el `.xlsx` se dispara con un `<a href>` directo.

Se eliminan `POST /reportes/generar` y `POST /reportes/importar/{template_id}`.

### Catálogo de áreas (nuevo, habilita los filtros)

`GET /personal/areas` y `GET /personal/subareas?area_id=` — lectura simple de los catálogos jerárquicos de Fase 4. Hoy no existe forma de poblar un filtro por área en el frontend.

---

## Dashboard

`GET /api/stats/dashboard?desde=&hasta=&empresa_id=&area_id=` reemplaza a `/stats/inventario`.

```
kpis:          entregas_periodo (unidades), lineas_periodo,
               reposiciones_perdida, sustituciones_dano,
               productos_bajo_minimo, productos_en_quiebre,
               trabajadores_activos, trabajadores_sin_epp
serie_mensual: [{mes, NUEVA, PERDIDA, DANO, total}] ×12
por_motivo:    donut
por_area:      barra, top 10
top_productos: barra, top 10
alertas_stock: tabla, 10 más críticos
```

Agregación: **un CTE por bloque**, no una mega-query. Con 591 personas el costo es despreciable y la legibilidad importa más.

Detalles que sí importan:

- **`generate_series` de 12 meses `LEFT JOIN` la agregación**, para que los meses sin entregas salgan en 0. Si no, Recharts dibuja un hueco y parece un bug de datos.
- `por_area` usa `COALESCE(a.nombre_area, 'Sin área')` — `personal.area_id` es nullable.
- El filtro por empresa usa `entregas_epp.empresa_id` (denormalizado al momento de la entrega), no el de `personal`: un traslado de empresa no debe reescribir el pasado.
- KPI de entregas cuenta **unidades** (`SUM(cantidad)`); el conteo de líneas va como subtítulo (Q1).

---

## Frontend

**`Dashboard.jsx`** — se reescribe el cuerpo, se conserva el andamiaje: `MetricCard`, `BarChart`, `DonutChart`, `useThemeColors`, `Dashboard.css` y los componentes `Section`/`Panel` (colapsables con estado persistido) son agnósticos del dominio. Cambia la barra de filtros (tipo/talla/sección/temporada → periodo/empresa/área) y se agrega `TrendChart.jsx` (barras apiladas por motivo, 12 meses).

**`Reports.jsx`** — reescrito con el patrón de tabs de Inventario/Entregas: `Trazabilidad · EPP vigentes · Stock`. Cada tab = barra de filtros + `DataTable` + botón "Exportar Excel".

Se eliminan `components/reports/FileUploadArea` (duplica `/importaciones`), `RecentExportsTable` (mock puro) y `ReportGenerator` (columnas del dominio viejo). `reportsService.js` y `statsService.js` se reescriben.

---

## Esquema

**No se toca en Fase 5.** Pendientes evaluados y pospuestos:

- Índices en `entregas_epp(fecha_entrega)` y `entregas_epp(rut)` — innecesarios hoy; sí importarán al migrar las entregas históricas.
- `productos_epp.costo_unitario` — solo si Q5 sale afirmativa.
- `entregas_epp.area_id` denormalizado — ver Q2, es la decisión con fecha de vencimiento.

## Corrección incluida: vigentes con motivo PERDIDA (Q6)

Hoy `PERDIDA` no marca la entrega perdida: si a alguien se le pierde un casco y se le repone quedan **dos** entregas vigentes de casco. En el `EppsModal` era cosmético; en R2 hace que el reporte que reemplaza al software actual mienta.

Corrección: `entrega_reemplazada_id` pasa a ser opcional también para líneas con motivo `PERDIDA`, elegible desde el flujo de entrega igual que en `DANO`. No genera `BAJA_DANO` (el ítem perdido no vuelve). Si no se informa, el comportamiento es el actual.

---

## Preguntas de negocio: estado

| # | Pregunta | Resolución |
|---|---|---|
| Q1 | ¿Entregas = unidades o eventos? | **Unidades** como número grande, líneas como subtítulo |
| Q2 | ¿Área histórica o actual? | **Actual** por ahora (es lo único disponible). Si prevención necesita la histórica hay que denormalizar `area_id` en `entregas_epp` — decidir antes de acumular historial |
| Q3 | ¿Incluir trabajadores sin EPP en R2? | **Sí**, con flag `sin_epp` |
| Q4 | Desvinculados con EPP sin devolver | Se incluyen si `incluir_inactivos=true`. "EPP a recuperar por finiquito" queda abierto (enlaza con D5) |
| Q5 | Stock valorizado | **Fuera de fase** — no hay precio en el modelo |
| Q6 | PERDIDA infla los vigentes | **Se corrige** (ver arriba) |
| Q7 | Rango por defecto del dashboard | Mes en curso, con selector de 3/6/12 meses |
| Q8 | ¿PDF? | **Solo Excel** |
| Q9 | Zona horaria | **Se convierte a `America/Santiago` al reportar** (ver arriba) |

## Verificación

`Backend/tests/smoke_reportes.py` — patrón de `smoke_sync_personal.py`: PostgreSQL efímero en Docker, esquema desde el ORM, siembra de datos sintéticos (empresas/áreas/personal/productos/stock/entregas con los 3 motivos), y ejercicio de Service → Repository de los 3 reportes + dashboard. Sin `TestClient` (choque de versión de httpx).

Casos que el smoke debe cubrir explícitamente:

- Corte de mes en el borde de zona horaria (entrega guardada el día 1 a las 02:00 UTC debe contar en el mes anterior).
- Producto sin talla (`talla_id IS NULL`) en R3 — no debe duplicar filas.
- Trabajador sin EPP presente en R2 con `sin_epp = true`.
- Mes sin entregas presente en `serie_mensual` con total 0.
- Entrega reemplazada por sustitución que desaparece de R2.
