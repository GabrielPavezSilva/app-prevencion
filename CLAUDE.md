# CLAUDE.md

Guía para Claude Code (claude.ai/code) al trabajar en este repositorio.

## Qué es este proyecto

**Prevención EPP** — sistema de gestión de Elementos de Protección Personal para prevención de riesgos: catálogo de EPP, stock por producto/talla, entregas a trabajadores con motivo trazable, y reportabilidad.

Es un **fork del sistema de lavandería industrial** del mismo autor, reconvertido por fases. El dominio de lavandería (prendas con chips RFID, lectores UHF por puerto serial, huella dactilar DigitalPersona, portal de operarios) **fue podado y ya no existe**. Si encontrás referencias a `lecturas_rfid`, `asignaciones`, `tiposPrendas`, `secciones` o `temporadas`, es código muerto — ver "Código muerto conocido".

Backend Python/FastAPI + PostgreSQL, frontend React/Vite. **UI, comentarios y documentación en español.**

## Comandos

### Backend (desarrollo local)

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Hay un venv en `Backend/venv`. Los scripts se corren con `venv/Scripts/python.exe`.

Seeds (idempotentes, primera vez):

```bash
cd Backend
venv/Scripts/python.exe seed_admin.py       # usuario admin
venv/Scripts/python.exe seed_modulos.py     # módulos y permisos por rol
venv/Scripts/python.exe seed_recintos.py    # Las Encinas, Lucerna, Malloco
```

### Frontend

```bash
cd Frontend
npm install
npm run dev      # http://localhost:5173
npm run build
npm run lint
```

### Base de datos de desarrollo

Contenedor Docker `pg-prevencion` en `localhost:5433/db_prevencion`, cargado con la nómina real sincronizada desde RRHH — todas las filas de `personal` tienen `buk_id`; las de prueba del fork (empresa "ACME", área "Bodega" y el trabajador ficticio que colgaba de ellas) ya se borraron.

```bash
docker start pg-prevencion
```

Datos de demostración para que reportes y dashboard tengan algo que mostrar (marca todo con observación `SEED_DEMO`, admite `--limpiar`):

```bash
cd Backend && PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/seed_demo_reportes.py
```

### Docker (producción)

```bash
cp .env.example .env          # completar valores
docker compose up -d --build
docker compose exec backend python seed_admin.py
```

## Cómo se verifica el backend

**No hay suite con pytest y no se usa `TestClient`** — hay un choque de versión de httpx en el proyecto. El patrón establecido es: levantar un PostgreSQL efímero en Docker, crear el esquema desde el ORM y ejercitar **Service → Repository** directamente con un script de checks.

```bash
docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine
```

```bash
cd Backend && PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/smoke_reportes.py
```

```bash
docker rm -f pg_smoke
```

Smoke tests existentes:

| Script | Cubre | Requiere |
|---|---|---|
| `tests/smoke_reportes.py` | Los 3 reportes + dashboard | Solo Docker |
| `tests/smoke_recintos.py` | Stock por recinto: UNIQUE, permisos, libro mayor | Solo Docker |
| `tests/smoke_importaciones.py` | Políticas de error de importación (todo o nada vs parcial) | Solo Docker |
| `tests/smoke_sync_personal.py` | Sync de personal desde RRHH | Docker + túnel SSH a RRHH |

Todos hacen `drop_all` sobre la base destino: **nunca apuntarlos a una base real.**

> Al sembrar datos en un smoke test, **no pongas IDs explícitos** en tablas donde
> el código bajo prueba también inserta: la secuencia no avanza y el `INSERT`
> del service choca contra la PK con un error que no tiene nada que ver con lo
> que estás probando.

Prueba manual: Swagger en `http://localhost:8000/docs`.

## Particularidades del entorno (Windows)

- **`PYTHONIOENCODING=utf-8` en todo script que imprima texto.** Sin eso la consola cp1252 corta la salida en el primer acento. Aplica también a `curl ... | python -m json.tool`: sin la variable los acentos salen como mojibake y parece un bug de datos que no existe.
- **`uvicorn` sin `--reload` no recarga el código.** Tras editar hay que reiniciarlo.
- **Usar `localhost`, no `127.0.0.1`.** La sesión viaja en una cookie httpOnly y no se comparte entre ambos hosts.
- Leer la base de RRHH requiere túnel SSH: `ssh -N -L 5434:localhost:5432 <usuario>@192.9.200.12`. Puerto local **5434** — nunca 5433, que es la base de desarrollo.

## Arquitectura

### Backend — Clean Architecture / Repository Pattern

```
Endpoint (app/api/v1/endpoints/) → Service (app/services/) → Repository (app/repositories/) → PostgreSQL
```

- **Schemas** (`app/schemas/`): modelos Pydantic de request/response.
- **Models** (`app/models/inventario.py`): **todos** los modelos ORM en un solo archivo. Debe importarse en `main.py` para que `Base.metadata.create_all` los registre.
- **Core** (`app/core/`): `config.py` (settings), `security.py` (JWT y permisos), `logging_config.py`.
- **DB** (`app/db/`): `session.py` (Base), `session_mysql.py` (engine principal — el nombre es herencia del fork, la base es PostgreSQL), `session_employees.py` (conexión de solo lectura a RRHH), `deps.py` expone `get_mysql_db()` para `Depends`.
- **Repositories**: SQL crudo con `sqlalchemy.text()`, **no** la query API del ORM.
- **Entry point**: `main.py` — CORS, rate limiting (slowapi), routers, `create_all` al arrancar.

### Agregar un endpoint nuevo

1. Schema Pydantic en `app/schemas/`
2. Métodos de repository en `app/repositories/` — siempre `sqlalchemy.text()`
3. Lógica en `app/services/`
4. Endpoint en `app/api/v1/endpoints/`
5. **Registrar el router en `app/api/v1/api.py`** ← el paso que se olvida
6. Proteger con `require_module("<modulo>")` — ver "Autenticación"

## Rutas de la API

Todas bajo el prefijo `/api`. Registradas en `app/api/v1/api.py`.

| Módulo | Prefijo | Contenido |
|---|---|---|
| Auth | `/api/auth` | `POST /login`, `POST /logout` |
| Personal | `/api/personal` | `GET /todos`, `GET /{rut}`, `GET /areas`, `GET /subareas`, `GET /sync/estado` |
| EPP | `/api/epp` | `categorias`, `productos`, `stock`, `stock/ajuste`, `movimientos` (CRUD) |
| Entregas | `/api/entregas` | `POST /`, `GET /`, `POST /sustitucion`, `GET /trabajador/{rut}` |
| Importaciones | `/api/importaciones` | `GET /`, `POST /{template_id}` |
| Templates | `/api/templates` | `GET /`, `GET /{template_id}`, `GET /descargar/{template_id}` |
| Inventario | `/api/inventario` | Solo catálogos vivos: `tallas` (CRUD) y `GET /empresas` |
| Reportes | `/api/reportes` | `entregas`, `epp-vigentes`, `stock` — cada uno con ruta gemela `.xlsx` |
| Stats | `/api/stats` | `GET /dashboard` |
| Superadmin | `/api/superadmin` | Usuarios, roles y asignación de módulos |

`GET /` y `GET /health` cuelgan de la raíz.

**Ojo con el orden de rutas**: en `personal.py`, `GET /{rut}` va **último**; si no, `/areas`, `/subareas` y `/sync/estado` caerían en esa ruta.

## Base de datos

- **PostgreSQL** vía psycopg2-binary + SQLAlchemy 2.0.
- Configuración: `DATABASE_URL` completa, o los campos `DB_HOST_PG / DB_PORT_PG / DB_USER_PG / DB_PASSWORD_PG / DB_NAME_PG`.
- Las tablas se auto-crean al arrancar con `Base.metadata.create_all`. **No hay sistema de migraciones**: un cambio de columna sobre una tabla existente no se aplica solo.
- `SQL/` contiene scripts del dominio de lavandería. **Están obsoletos**, no los uses como referencia del esquema — la fuente de verdad es `app/models/inventario.py`.

### Tablas del dominio EPP

**`productos_epp`** — catálogo (una fila por tipo de EPP, no por unidad): `producto_id`, `nombre` UNIQUE, `categoria_id`, `talla_aplica`, `certificacion`, `activo`.

**`stock_epp`** — existencias por producto+talla+**recinto**: `producto_id`, `talla_id` (NULL si el producto no maneja tallas), `recinto_id`, `cantidad_actual`, `stock_minimo`, UNIQUE(producto_id, talla_id, recinto_id). Cada recinto tiene bodega propia y el mismo casco talla L existe por separado en los tres. (Hasta la Fase 6 el stock era global, un solo bodegón; ver `docs/plans/2026-09-09-stock-por-recinto-design.md`.)

**`recintos`** — los tres con bodega propia: Las Encinas, Lucerna, Malloco. `recinto_id`, `nombre_recinto` UNIQUE, `activo`. Sin CRUD en la app: un cuarto recinto es un `INSERT` — se agrega a la lista de `seed_recintos.py` y se corre de nuevo.

**`movimientos_stock`** — libro mayor: `tipo` ∈ `INGRESO_IMPORT | ENTREGA | BAJA_DANO | AJUSTE`, `cantidad` (positiva o negativa), `referencia_id`, `fecha`.

**`entregas_epp`** — entrega de EPP a un trabajador: `rut`, `nombre_completo`, `empresa_id` y `recinto_id` (denormalizados al momento de la entrega), `producto_id`, `talla_id`, `cantidad`, `motivo` ∈ `NUEVA | PERDIDA | DANO`, `entrega_reemplazada_id`, `estado_firma`, `fecha_entrega`, `uuid` UNIQUE (idempotencia offline).

**`personal`** — empleados sincronizados desde RRHH: `rut` PK, `nombre_completo`, `empresa_id` FK, `cargo`, `area_id`, `subarea_id`, `activo` (soft-delete de desvinculados), `buk_id`, `sync_at`. **No tiene talla**: se elige en cada entrega.

**`empresa` / `areas` / `subareas`** — jerarquía organizacional espejada de RRHH vía `origen_id`. El nombre de área **no** es único a nivel global (hay "Administración" en varias empresas): el UNIQUE es `(nombre_area, empresa_id)`. La identidad estable de subárea es `origen_id`.

**`usuarios` / `roles` / `modulos` / `roles_modulos`** — login y permisos.

**`categorias_epp`**, **`tallas`**, **`importaciones`**, **`auditoria_epp`**, **`token_blacklist`**.

### Invariantes que no se pueden romper

**Libro mayor del stock.** `cantidad_actual` **nunca** se edita directo: siempre a través de un `MovimientoStock` en la misma transacción.

```
stock_epp.cantidad_actual = SUM(movimientos_stock.cantidad
                                WHERE tipo IN ('INGRESO_IMPORT','ENTREGA','AJUSTE'))
```

`BAJA_DANO` queda fuera a propósito: documenta la baja de una unidad que ya estaba en terreno (su stock se descontó al entregarla), no descuenta del bodegón.

**Talla NULL.** En PostgreSQL `NULL = NULL` es NULL, así que el `UNIQUE(producto_id, talla_id, recinto_id)` **no** impide filas duplicadas para productos sin talla. Todo lookup, upsert o join usa `talla_id IS NOT DISTINCT FROM :talla_id`. `recinto_id` es NOT NULL y va con `=` normal.

**La identidad de una fila de stock es la terna `(producto_id, talla_id, recinto_id)`**, en seis lugares: el `UNIQUE`, `epp_repository.get_stock_row` / `get_stock_detalle` / `ajustar_stock`, `entregas_repository._get_stock_row` y el upsert de `importaciones_repository`. Si se agrega un séptimo, va con la terna completa.

**Quién puede mover qué recinto.** `resolver_recinto(current_user, recinto_id)` en `app/core/security.py`, al lado de `require_module`. Regla: **todos ven los tres recintos, cada uno mueve solo el suyo**. Un rol de `FULL_ACCESS_ROLES` no tiene recinto propio, así que tiene que elegirlo (400 si no lo manda); un usuario con recinto que pide otro recibe 403 en vez de que se le ignore en silencio; sin recinto asignado y sin bypass, 403. Aplica solo a **escrituras** — las lecturas traen los tres a propósito. El recinto viaja en el JWT junto a `modulos`: **una sesión abierta desde antes de este cambio no lo trae y recibe 403 hasta volver a loguearse.**

**Zona horaria.** La BD corre en **UTC** y `fecha_entrega` es `TIMESTAMP WITHOUT TIME ZONE` con `server_default=now()`: guarda hora UTC. El negocio opera en Chile. Sin convertir, una entrega del 31 a las 21:00 hora local cae en el mes siguiente. Todo agrupamiento y filtro por fecha usa la constante `FECHA_LOCAL` de `app/repositories/reportes_repository.py`:

```sql
((e.fecha_entrega AT TIME ZONE 'UTC') AT TIME ZONE 'America/Santiago')
```

**"EPP vigente".** Una entrega que ninguna posterior reemplazó:

```sql
NOT EXISTS (SELECT 1 FROM entregas_epp r WHERE r.entrega_reemplazada_id = e.entrega_id)
```

Está definido igual en `entregas_repository`, `personal_repository` y `reportes_repository`. Si cambia el criterio, hay que cambiarlo en los tres.

## Reglas de negocio del flujo de entregas

- **`NUEVA`** — primera entrega. Descuenta stock.
- **`PERDIDA`** — reposición. Descuenta stock. Puede vincular `entrega_reemplazada_id` (opcional) para retirar el EPP perdido de los vigentes; no genera `BAJA_DANO` porque el ítem no vuelve.
- **`DANO`** — sustitución. **Solo vía `POST /entregas/sustitucion`**, que exige `entrega_reemplazada_id`. `POST /entregas` rechaza este motivo. Descuenta stock y registra `BAJA_DANO` del ítem devuelto.
- No existe devolución de EPP sin reemplazo.
- El carrito de entregas es **una sola transacción**: si una línea no tiene stock suficiente, se revierte completa.
- Todo el carrito sale de **un mismo recinto** — no se acepta una línea por recinto: un acta firmada que mezcle bodegas no tendría a quién imputarle el descuento. En una sustitución, el reemplazo sale del recinto elegido pero la `BAJA_DANO` se imputa al recinto de la **entrega original**, que es de donde salió el ítem.
- Un trabajador desvinculado no puede recibir EPP nuevo, pero sus entregas se conservan y se pueden consultar.

## Políticas de error de las importaciones

`importaciones_service.py` aplica cada fila en su propio savepoint, pero el desenlace depende del template — la constante es `_ATOMICOS`:

| Template | Política | Por qué |
|---|---|---|
| `stock_inicial`, `ingreso_stock` | **Todo o nada** | Un ingreso a medias deja el bodegón mintiendo. Y como el ingreso es **aditivo**, reintentar el archivo corregido volvería a sumar las filas que sí habían entrado: nadie recorta el Excel antes del segundo intento |
| `productos_epp`, `entregas_historicas` | **Parcial** | Cargar 28 de 30 productos y corregir dos es más cómodo que rehacer el archivo, y el catálogo tolera estar incompleto un rato |

Las tres plantillas que escriben stock o entregas (`stock_inicial`, `ingreso_stock`, `entregas_historicas`) exigen una columna **`Recinto`** con el nombre exacto. Cada fila pasa por `resolver_recinto`, así que un usuario de Lucerna no puede cargar a Malloco ni por Excel; el 403 se traduce a error de fila para que la política del template lo trate como cualquier otro.

Cuando se revierte, la respuesta trae `aplicado: false` y `filas_ok: 0`, pero **la importación igual se registra** en `importaciones` — el rastro del intento fallido es lo que hay que conservar. La UI muestra "No se aplicó ningún cambio" en vez del conteo parcial.

## Autenticación

**Login** — `LoginRequest` es `{ username, contrasena }`; el campo es **`contrasena`**, no `password`. La columna `usuarios.username` es el nombre de usuario (en la lavandería era `nombre_completo`; ya no).

**Sesión por cookie httpOnly** llamada `authToken`. `security.py` la lee primero y cae al header `Authorization` como respaldo (Swagger/debug). El logout invalida el `jti` en `token_blacklist`.

**JWT**: `{ userId, username, role, modulos, exp, jti }`, expira en 480 minutos.

**`UserResponse`**: `{ id, username, email, role, modulos }` — el campo es `role`, no `rol`.

**Permisos por módulo**: `require_module("nombre")` como dependencia FastAPI. Los roles en `FULL_ACCESS_ROLES = ("admin", "administrador")` tienen bypass total; el resto necesita el módulo en su lista. Módulos: `dashboard`, `inventario`, `entregas`, `personal`, `reportes`, `configuracion`, `superadmin`.

Ojo con la asimetría entre backend y frontend: el bypass del backend cubre a los dos roles, pero `ProtectedRoute` solo exime a `admin` — cualquier otro rol se rige por los módulos del JWT. Por eso `seed_modulos.py` le asigna a `administrador` la lista **completa** de módulos: si le falta uno, el backend lo deja pasar pero la UI lo redirige. Probado en runtime con un usuario de ese rol: los 7 módulos llegan en el JWT y `/superadmin` abre.

Credenciales por defecto: `admin` / `admin123`.

## Frontend

React 19 + Vite 7, React Router 7, Recharts, TanStack Table, react-hot-toast, Dexie.

- **Pages** (`src/pages/`), **components** (`src/components/` por dominio), **services** (`src/services/`, todos importan `apiClient` de `api.js`).
- `apiClient` lee `VITE_API_URL` o cae a `http://localhost:8000/api`, y manda `credentials: 'include'` para la cookie.
- **La navegación real es `components/layout/TopNav.jsx`.** (El viejo `Sidebar.jsx` del fork ya se borró.)
- Tablas: `components/common/DataTable.jsx` (TanStack Table) — props `columns`, `data`, `loading`, `filterable`, `initialSort`, `emptyState`.
- Toasts: `toast.success()` / `toast.error()`, nunca `alert()`.
- Gráficos: `components/dashboard/` — `MetricCard`, `BarChart`, `DonutChart` (genérico sobre `[{nombre, cantidad}]`), `TrendChart` (barras apiladas por motivo). Los colores salen de `useThemeColors` para seguir el tema claro/oscuro.

### Rutas

| Path | Módulo requerido | Componente |
|---|---|---|
| `/login` | público | Login |
| `/` | `dashboard` | Dashboard |
| `/inventario` | `inventario` | Inventory (Productos / Stock / Categorías / Tallas) |
| `/entregas` | `entregas` | Entregas (Registrar / Historial) |
| `/importaciones` | `inventario` | Importaciones |
| `/personal` | `personal` | Staff (solo lectura + modal de EPP) |
| `/reportes` | `reportes` | Reports (Trazabilidad / EPP vigentes / Stock) |
| `/configuracion` | `configuracion` | Settings |
| `/superadmin` | `superadmin` | SuperAdmin |

Agregar una página requiere: ruta en `App.jsx` **y** entrada en `TopNav.jsx` (con su `modulo`).

`ProtectedRoute` valida el módulo; `admin` pasa siempre.

### Variables CSS (`src/styles/index.css`)

Paleta teal, con tema claro y oscuro. Las principales:

| Variable | Claro | Uso |
|---|---|---|
| `--color-accent` | `#0f766e` | Teal — botones, foco |
| `--color-accent-bright` | `#0d9488` | Series de gráfico, subrayado activo |
| `--color-brand` | `#dc2626` | Rojo — errores críticos |
| `--color-bg` | `#f4f7f8` | Fondo de la app |
| `--color-card` / `--color-card-border` | `#ffffff` / `#e2e8f0` | Tarjetas |
| `--color-success` / `--color-warning` / `--color-error` | | Estados, con variantes `-light` |

Cada color de estado tiene su `-light` definido en **ambos** temas: usalos en vez de `color-mix()`.

Estilos compartidos entre páginas (como `.dash-badge` de estado de stock) van en `index.css`, no en el CSS de una página — si no, dependen de que ese archivo se haya cargado.

## Sincronización de personal

`personal` se sincroniza desde la base de RRHH `rh_cramer` (schema `rh`), que es la **fuente de verdad**: pisa todos los campos y desactiva (nunca borra) a quien sale de la nómina. La página Personal es de solo lectura.

- CLI, único punto de entrada: `Backend/sync_personal.py` (acepta `--dry-run`)
- Lo dispara Ofelia a las 04:00 (label en `compose.yml`); a mano,
  `docker compose exec backend python sync_personal.py`
- **No hay endpoint que lo dispare**, a propósito: es una escritura masiva que
  puede desactivar a cientos de personas, y no va al alcance de un usuario.
  `GET /api/personal/sync/estado` es solo lectura
- Runbook completo: `docs/runbook-sync-personal.md`

## Reportabilidad

Principio: **una query por reporte, dos presentaciones.** Cada reporte tiene un único método de repository que devuelve `List[dict]`; la ruta JSON y la `.xlsx` consumen las mismas filas, así que la tabla en pantalla y el archivo exportado no pueden divergir. Al agregar un reporte, respetá esto.

Motor Excel: `app/services/excel_builder.py` — infraestructura sin dominio, columnas declaradas por reporte con `Columna(key, label, ancho, formato, fmt)`.

Diseño y decisiones: `docs/plans/2026-07-27-fase5-reportabilidad-design.md`.

## Código muerto conocido

La poda de los sobrevivientes del dominio de lavandería **ya se hizo** (rama `fase-5`): se borraron los endpoints `asignaciones.py` y `devoluciones.py` con su repository/service/schema, `catalogos_repository/service`, `auditoria_repository`, `schemas/tipos_prendas.py`, y en el frontend `pages/Returns.jsx`, `components/returns/`, `returnsService.js`, `layout/Sidebar.jsx` y `api/offlineWrapper.js`. `catalogosService.js` quedó reducido a tallas. Si necesitás ver alguno, está en el historial de git.

Lo que **queda** por revisar:

- `services/personalCacheService.js` — sí lo importa `main.jsx`: `poblarCachePersonal()` corre en cada arranque y vuelca `/personal/todos` en Dexie. Pero **nadie lee esa caché**: `buscarPersonalOffline()` no tiene llamadores. Vive o muere con la capa offline (ver "Deuda").
- `app/schemas/tallas.py` — sin importadores; `inventario.py` declara sus propios modelos Pydantic.
- `Backend/migrations/add_uuid_to_tables.sql` — toca la tabla `asignaciones`, que ya no existe.
- **SQL** — todo `SQL/` describe el esquema de lavandería.

## Deuda y pendientes

| Tema | Estado |
|---|---|
| Área en reportes | Se usa el área **actual** del trabajador. Si el negocio necesita la histórica hay que denormalizar `area_id` en `entregas_epp` — decisión con fecha de vencimiento, cada día acumula historial |
| Stock valorizado | No hay precio en `productos_epp` |
| Capa offline | Dexie, `syncManager` y `OfflineBanner` están montados en `main.jsx`, pero **nada encola operaciones**: la cola nunca se llena. El puente que faltaba (`api/offlineWrapper.js`) se borró en la poda; completar la capa implica escribirlo de nuevo o decidir que la app siempre opera con red |
| Despliegue | Las imágenes ya son `ghcr.io/gabrielpavezsilva/prevencion-*`, pero **falta definir la variable `DEPLOY_DIR`** del repositorio con la ruta del checkout en el VPS: sin ella, `deploy.yml` falla a propósito (antes apuntaba al directorio de la lavandería y habría reiniciado el stack equivocado). Siguen con nombre viejo `scripts/deploy.sh`, `docs/staging-deploy.md` y `airflow/dags/backup_lavanderia_db.py`, que dependen de rutas reales del servidor |
| Migraciones | No hay. Cambiar una columna existente requiere hacerlo a mano en la BD; los scripts quedan versionados en `Backend/migrations/` con la fecha |
| Traslados entre recintos | Fuera de alcance de la Fase 6. Con tres bodegas separadas va a hacer falta un `MovimientoStock` tipo `TRASLADO`; mientras tanto cada recinto carga por importación o ajuste |
| Ramas | `main`, `fase-1`, `fase-4`, `fase-5` en el remoto; **ninguna fase está mergeada a `main`** |
