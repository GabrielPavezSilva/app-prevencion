# Diseño: Clon Prevención de Riesgos — Gestión de EPP

**Fecha:** 2026-07-21
**Alcance:** Proyecto nuevo (fork quirúrgico de app-lavanderia). Este documento vive temporalmente en el repo original; debe copiarse al repo del clon cuando exista.

---

## Contexto

Prevención de riesgos usa hoy un software de escritorio (un solo computador) para gestionar EPP con estas carencias:

- El catálogo de EPP existe pero **el stock no se mantiene actualizado**.
- No registra el **estado de la entrega**: EPP nuevo, sustitución por daño o reposición por pérdida (la pérdida se informa por correo del supervisor a prevención).
- Enrolamiento manual del personal, **sin sincronización con Buk** y sin áreas normalizadas.
- El trabajador firma el documento de entrega **en papel**.
- Reportabilidad solo por trabajador individual; no hay reportes generales ni estadísticas por área.

La app de lavandería (este repo) ya resuelve la infraestructura que el software actual no tiene: aplicación web multi-usuario, login con roles y permisos por módulo, motor de import/export Excel, dashboard de estadísticas y despliegue Docker en VPS. El clon reutiliza ese esqueleto y reemplaza el dominio (prendas con RFID → stock de EPP).

### Situación esperada (requisitos del negocio)

1. Filtrar entregas por estado del EPP (nueva / pérdida / daño) → **reporte de trazabilidad**.
2. Sincronización con Buk para el personal (áreas normalizadas desde la base `employees` existente).
3. Reporte general de todos los usuarios + estadísticas de entregas por mes/año, separadas por área.
4. Exportables e importables Excel para gestión (incluye importadores para alimentar la base de EPP).
5. Asignación por RUT (hoy). Futuro: firma electrónica vía API Buk — el modelo de datos debe anticiparla.

---

## Estrategia general

**Fork quirúrgico**: repo independiente copiado de app-lavanderia, sobre el cual se poda todo lo que no aplica y se remodela el dominio de inventario. Se descartaron multi-tenant/feature-flags (los dominios divergen en el corazón: unit-tracking RFID vs stock por cantidades) y core compartido como librería (overhead injustificado para el tamaño del equipo).

La diferencia estructural que define toda la cirugía:

| | Lavandería | Prevención (clon) |
|---|---|---|
| Unidad de inventario | Cada prenda física = 1 fila (`lecturas_rfid`, SKU + tag EPC únicos) | Stock por producto+talla (cantidades) |
| Ingreso de inventario | Escaneo RFID uno a uno | Importador Excel |
| Entrega | Escanear tag → vincular a RUT | RUT + producto + cantidad + **motivo** |
| Devolución | La prenda vuelve a disponible | Sustitución por daño (el dañado se da de baja) |
| Identificación | Huella digital + RUT fallback | RUT (futuro: firma Buk) |
| Personal | Carga manual a la tabla | Sync desde Buk / base `employees` |

---

## Fase 0 — Poda (dejar el esqueleto funcionando)

### Eliminar completo

**Raíz:**
- `HardwareMiddleware/` completo (incluye los `power_*.py` sueltos y los JSON de scan)
- `huella_test/`
- `reconocimiento-facial.py` (referenciado en Backend)

**Backend:**
- `app/api/v1/endpoints/`: `endpoints_rfid.py`, `lectura.py`, `biometria.py`, `prendas_predeterminadas.py`
- `app/services/`: `rfid_service.py`, `uhf_reader.py`, `biometria_manager.py`, `biometria_service.py`, `prendas_predeterminadas_service.py`
- `app/repositories/`: `rfid_repository.py`, `biometria_repository.py`, `prendas_predeterminadas_repository.py`
- `app/schemas/`: `rfid.py`, `biometria.py`, `prendas_predeterminadas.py`
- `lector_escritor.py`
- Modelos en `inventario.py`: `LecturaRFID`, `PrendaPredeterminada`, `Seccion`, `Temporada` (y `AuditoriaPrenda` se conserva pero re-apuntada, ver Fase 2)
- Variables de entorno `RFID_RECEPTION_PORT` / `RFID_ASSIGNMENT_PORT`

**Frontend:**
- `services/`: `rfidService.js`, `huellasService.js`, `prendasPredeterminadasService.js`, `alertService.js` (ya era ruta muerta)
- `components/fingerprint/`, `components/worker/` completo
- `pages/`: `RecepcionDashboard.jsx`, `AsignacionDashboard.jsx`, `WorkerDashboard.jsx`, `InventoryMode.jsx` (+ sus CSS)
- `components/inventory/TabRealizarInventario.jsx`
- En `App.jsx`: rutas `/worker/*`, `/inventario-rfid`
- Referencia a `hardwareClient` / `VITE_HARDWARE_URL`

**Decisión pendiente (D3):** modo offline (`db/localDb.js`, `sync/syncManager.js`, `api/offlineWrapper.js`, `OfflineBanner`, panel de sincronización en SuperAdmin). Si prevención opera siempre con red, eliminarlo simplifica; si hay entregas en terreno, se conserva (el patrón UUID-idempotencia ya funciona).

### Mantener casi intacto

- **Auth completo**: JWT, bcrypt, token blacklist, `seed_admin.py`
- **Sistema de permisos**: `modulos` / `roles_modulos` / `ProtectedRoute` / SuperAdmin — solo cambia la lista de módulos en `seed_modulos.py`:
  ```python
  MODULOS = ["dashboard", "inventario", "entregas", "personal", "reportes", "configuracion", "superadmin"]
  ```
- **Layout y design system**: `Layout`, `Sidebar` (nuevas entradas), `TopNav`, `ThemeContext`, `styles/index.css`, `DataTable`
- **Motor Excel**: `templates.py` (endpoint + schema), `reportes.py`, `ReportesService` (se reescriben solo los `DEFAULT_TEMPLATES` y las queries de generación)
- **Personal**: backend ~95% igual (2 endpoints GET, solo lectura). El borrador comentado de sync Buk en `personal_repository.py:73-118` y los settings `BUK_*` de `config.py` se conservan — son la semilla de la Fase 4
- **Infra**: `compose.yml`, `compose.staging.yml`, `nginx/`, `airflow/` (el DAG de backup se renombra), `scripts/deploy.sh` — con renombres (ver Branding)

### Adaptar

- **Staff.jsx** (página Personal): quitar `FingerprintControl`, columna `tiene_huella` y modal de huella; `PrendasModal` → `EppsModal` (EPPs entregados vigentes del trabajador, misma estructura, fuente `entregas_epp`)
- **Inventory.jsx** → página **Inventario EPP**: tabs Productos / Stock / Catálogos (tallas, categorías) — desaparecen tabs Secciones, Temporadas y Realizar Inventario
- **Returns/devoluciones** → flujo de sustitución (ver Fase 3)
- **Dashboard/stats** → métricas de stock y entregas (ver Fase 5)

---

## Fase 1 — Modelo de datos del dominio EPP

Convención: mismas prácticas del repo (SQLAlchemy declarativo en `app/models/`, tablas auto-creadas con `Base.metadata.create_all`, SQL crudo en repositories).

```
personal (adaptada)
  rut VARCHAR(20) PK, nombre_completo, empresa, cargo,
  area_id FK→areas, subarea_id FK→subareas,
  url_picture, activo BOOLEAN,
  buk_id INTEGER NULL, sync_at TIMESTAMP NULL          -- nuevo
  -- se elimina: huella_digital, talla_id (D2: talla del trabajador
  --             podría conservarse para pre-cargar talla en entregas)

productos_epp
  producto_id SERIAL PK, nombre VARCHAR(100) UNIQUE,
  categoria_id FK→categorias_epp, talla_aplica BOOLEAN DEFAULT FALSE,
  certificacion VARCHAR(100) NULL, descripcion TEXT NULL,
  activo BOOLEAN DEFAULT TRUE

categorias_epp                                          -- ej: protección auditiva, calzado, cabeza
  categoria_id SERIAL PK, nombre_categoria VARCHAR(100) UNIQUE

tallas (se conserva el catálogo actual, ampliable a tallas numéricas de calzado)

stock_epp
  stock_id SERIAL PK,
  producto_id FK→productos_epp, talla_id FK→tallas NULL,
  cantidad_actual INTEGER NOT NULL DEFAULT 0,
  stock_minimo INTEGER NOT NULL DEFAULT 0,
  UNIQUE (producto_id, talla_id)

movimientos_stock                                       -- libro mayor: el stock siempre es auditable
  movimiento_id SERIAL PK,
  producto_id FK, talla_id FK NULL,
  tipo VARCHAR(20) NOT NULL,      -- INGRESO_IMPORT | ENTREGA | BAJA_DANO | AJUSTE
  cantidad INTEGER NOT NULL,      -- positivo o negativo
  referencia_id INTEGER NULL,     -- entrega_id o importacion_id según tipo
  usuario_id FK→usuarios, observacion TEXT NULL,
  fecha TIMESTAMP DEFAULT now()

entregas_epp
  entrega_id SERIAL PK,
  rut FK→personal, nombre_completo VARCHAR(100),        -- denormalizado (patrón de asignaciones)
  producto_id FK, talla_id FK NULL, cantidad INTEGER DEFAULT 1,
  motivo VARCHAR(20) NOT NULL,    -- NUEVA | PERDIDA | DANO
  entrega_reemplazada_id FK→entregas_epp NULL,          -- para sustituciones
  estado_firma VARCHAR(20) DEFAULT 'PENDIENTE',         -- PENDIENTE | FIRMADA (futuro Buk)
  usuario_entrega FK→usuarios, observacion TEXT NULL,
  fecha_entrega TIMESTAMP DEFAULT now(),
  uuid VARCHAR(36) UNIQUE NULL                          -- solo si se conserva offline (D3)

importaciones
  importacion_id SERIAL PK, template_id VARCHAR(50),
  nombre_archivo VARCHAR(255), filas_ok INTEGER, filas_error INTEGER,
  detalle_errores TEXT NULL, usuario_id FK, fecha TIMESTAMP DEFAULT now()

auditoria_epp (reemplaza auditoria_prendas)
  misma estructura, ref = producto_id/entrega_id según acción
```

**Regla de oro:** `stock_epp.cantidad_actual` nunca se edita directo desde la app; siempre cambia a través de un `movimientos_stock` (transacción atómica). El ajuste manual existe pero es tipo `AJUSTE` con usuario y observación obligatoria.

---

## Fase 2 — Backend: API del dominio

Routers registrados en `api.py` (se quitan rfid, biometria, prendas-predeterminadas):

| Prefijo | Contenido |
|---|---|
| `/api/auth`, `/api/superadmin` | Sin cambios |
| `/api/personal` | Sin cambios funcionales (se quita `tiene_huella` del SELECT) + `POST /sync` (Fase 4) |
| `/api/epp` | `GET/POST/PUT/DELETE /productos`, `GET/POST/PUT/DELETE /categorias`, `GET /stock` (con filtros producto/categoría/bajo-mínimo), `POST /stock/ajuste`, `GET /movimientos` |
| `/api/entregas` | `POST /` (entrega con motivo, descuenta stock transaccionalmente), `GET /` (historial con filtros: rut, motivo, área, rango fechas), `GET /trabajador/{rut}` (vigentes, alimenta EppsModal), `POST /sustitucion` (baja del dañado + entrega nueva vinculada, una transacción) |
| `/api/templates`, `/api/reportes` | Motor igual; nuevos templates y generadores (Fases 3 y 5) |
| `/api/stats` | Reescrito: métricas EPP (Fase 5) |
| `/api/inventario` | Se reduce a catálogos vivos: tallas (secciones/temporadas se eliminan) — o se fusiona en `/api/epp` |

Patrón en todo: Endpoint → Service → Repository con `sqlalchemy.text()`, igual que el repo original.

---

## Fase 3 — Importadores y flujo de entregas (el corazón del clon)

### Templates de importación (`DEFAULT_TEMPLATES` nuevos)

| id | Propósito | Columnas |
|---|---|---|
| `stock_inicial` | Poblar stock por primera vez | Producto*, Talla, Cantidad*, Stock Mínimo |
| `ingreso_stock` | Reposiciones periódicas / OC | Producto*, Talla, Cantidad*, Proveedor, Observación |
| `productos_epp` | Alta masiva de catálogo | Nombre*, Categoría*, Aplica Talla (SI/NO)*, Certificación |
| `entregas_historicas` | Migrar historial del software antiguo | RUT*, Producto*, Talla, Cantidad, Fecha*, Motivo |

Validaciones del importador: producto existente (o creación con flag), talla obligatoria si `talla_aplica`, RUT existente en `personal`, motivo ∈ {NUEVA, PERDIDA, DANO}. Cada import genera fila en `importaciones` + movimientos tipo `INGRESO_IMPORT`.

### Página Entregas (nueva, sustituye a los dashboards worker)

Flujo en una sola pantalla:

1. **Buscar trabajador por RUT** (mismo autocomplete de `ScanningPanel` modo manual, contra `GET /personal/todos?search=`). Muestra ficha: nombre, área, cargo + EPPs vigentes.
2. **Carrito de entrega**: agregar productos (select con búsqueda), talla si aplica, cantidad, **motivo por línea**:
   - `NUEVA` — primera entrega
   - `PERDIDA` — reposición (queda trazado para el reporte que hoy se maneja por correo)
   - `DANO` — sustitución: exige seleccionar cuál entrega vigente reemplaza (`entrega_reemplazada_id`); genera además `BAJA_DANO` del ítem devuelto
3. **Confirmar** → transacción: N filas `entregas_epp` + N movimientos `ENTREGA` + descuento de stock. Si algún producto no tiene stock suficiente → error por línea antes de confirmar.
4. Comprobante en pantalla con `estado_firma = PENDIENTE` (impresión simple ahora; firma Buk después).

La página Returns actual se elimina como página propia: la sustitución vive dentro del flujo de entrega (D5 abierta: ¿existe devolución de EPP sin reemplazo, ej. desvinculación del trabajador?).

---

## Fase 4 — Sincronización con Buk / base employees

Ya existe medio camino en el repo: settings `BUK_API_BASE_URL`, `BUK_API_KEY`, `BUK_TOKEN` en `config.py` y borrador comentado de `update_personal()` con paginación en `personal_repository.py`.

- **Fuente (D1, decisión principal abierta):** API Buk directa vs base `employees` interna que ya está poblada desde Buk. Recomendación: base `employees` (menos fricción, áreas ya normalizadas, sin límites de rate de la API).
- **Mecanismo:** DAG de Airflow (ya hay Airflow en el stack con el DAG de backup como plantilla) con frecuencia diaria; upsert por RUT a `personal` con `buk_id`, `sync_at`, y `activo=false` para quienes salen de la nómina (soft-delete, se conserva historial de entregas).
- **Alternativa sin Airflow:** endpoint `POST /personal/sync` protegido + tarea programada (Ofelia ya corre en el compose para backups).
- La página Personal se vuelve **solo lectura** (el origen de verdad es Buk); se elimina cualquier edición manual.

---

## Fase 5 — Reportabilidad y dashboard

### Reportes (motor Excel existente, nuevos generadores)

1. **Trazabilidad de entregas** — filtros: rango de fechas, motivo (NUEVA/PERDIDA/DANO), área, producto, trabajador. Es el requisito #1 del negocio (hoy las pérdidas viven en correos).
2. **Reporte general** — todos los trabajadores con sus EPPs vigentes y fechas (reemplaza la reportabilidad individualizada del software actual).
3. **Stock valorizado / bajo mínimo** — snapshot de `stock_epp` con alerta de quiebre.

### Dashboard

- Cards: entregas del mes, reposiciones por pérdida del mes, sustituciones por daño del mes, productos bajo stock mínimo.
- Gráficos (Recharts, ya en el stack): entregas por mes (12 meses), entregas por área (barra), distribución por motivo (donut).
- Todos los agregados salen de `entregas_epp` JOIN `personal` (área) y `stock_epp` — sin tablas de agregación.

---

## Branding e infraestructura del clon

- Renombrar: nombre del compose project, imágenes (`ghcr.io/.../prevencion-*`), BD (`db_prevencion`), IndexedDB (`CivotOfflineDB` → si se conserva offline), dominio nuevo en nginx + `VITE_API_URL`.
- `.env` nuevo (JWT_SECRET_KEY distinto — no compartir secretos entre productos).
- `CLAUDE.md` y `ARQUITECTURA.md` del clon se reescriben tras la Fase 2 (el actual describe lavandería).
- Rama base del fork: idealmente `main` con `feature/rediseño-devoluciones` ya mergeada (la copia se hizo desde esta rama, que está 24 commits ahead — verificar que es el estado deseado).

---

## Orden de implementación y criterio de avance

| Fase | Entregable verificable |
|---|---|
| 0 Poda | App levanta con login, SuperAdmin y módulos nuevos; cero referencias a RFID/huella; `docker compose up` funciona |
| 1 Modelo | Tablas nuevas auto-creadas; seeds corren idempotentes |
| 2 API | CRUD productos + stock consultable vía Swagger |
| 3 Importadores + Entregas | Cargar Excel de stock inicial y registrar una entrega con motivo descuenta stock |
| 4 Sync Buk | `personal` se puebla/actualiza automáticamente desde la fuente elegida |
| 5 Reportes | Exportar trazabilidad filtrada por motivo y estadística por área |
| Futuro | Firma electrónica Buk (`estado_firma` ya lo anticipa); matriz de EPP por cargo (D6) |

---

## Decisiones abiertas

| # | Pregunta | Recomendación provisional |
|---|---|---|
| D1 | ¿Sync desde API Buk directa o desde la base `employees` interna? | Base `employees` (ya normalizada) |
| D2 | ¿Conservar talla del trabajador en `personal` para pre-cargar talla en entregas? | Sí, es barato y útil |
| D3 | ¿Conservar modo offline? | Eliminar salvo que haya entregas en terreno sin red |
| D4 | ¿Multiempresa? La lavandería gestiona varias empresas (`empresa_id`); ¿prevención es una sola? | Si es una sola, eliminar catálogo `empresa` del flujo |
| D5 | ¿Existe devolución de EPP sin reemplazo (ej. finiquito)? | Definir con prevención; el modelo lo soporta con un tipo de movimiento extra |
| D6 | ¿Matriz de EPP por cargo (qué EPP corresponde a cada puesto)? Es estándar en prevención y sería el sucesor natural de `prendas_predeterminadas` | Fase futura, no bloquea |
| D7 | ¿Vida útil / vencimiento de EPP (certificaciones)? | Fase futura; agregar `vida_util_meses` a `productos_epp` cuando se necesite |
| D8 | Nombre del producto/dominio/repositorio del clon | Pendiente del usuario |
