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

Contenedor Docker `pg-prevencion` en `localhost:5433/db_prevencion`, cargado con la nómina real sincronizada desde RRHH.

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
| `tests/smoke_sync_personal.py` | Sync de personal desde RRHH | Docker + túnel SSH a RRHH |

Ambos hacen `drop_all` sobre la base destino: **nunca apuntarlos a una base real.**

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
| Personal | `/api/personal` | `GET /todos`, `GET /{rut}`, `GET /areas`, `GET /subareas`, `POST /sync`, `GET /sync/estado` |
| EPP | `/api/epp` | `categorias`, `productos`, `stock`, `stock/ajuste`, `movimientos` (CRUD) |
| Entregas | `/api/entregas` | `POST /`, `GET /`, `POST /sustitucion`, `GET /trabajador/{rut}` |
| Importaciones | `/api/importaciones` | `GET /`, `POST /{template_id}` |
| Templates | `/api/templates` | `GET /`, `GET /{template_id}`, `GET /descargar/{template_id}` |
| Inventario | `/api/inventario` | Solo catálogos vivos: `tallas` (CRUD) y `GET /empresas` |
| Reportes | `/api/reportes` | `entregas`, `epp-vigentes`, `stock` — cada uno con ruta gemela `.xlsx` |
| Stats | `/api/stats` | `GET /dashboard` |
| Superadmin | `/api/superadmin` | Usuarios, roles y asignación de módulos |

`GET /` y `GET /health` cuelgan de la raíz.

**Ojo con el orden de rutas**: en `personal.py`, `GET /{rut}` va **último**; si no, `/areas`, `/subareas` y `/sync` caerían en esa ruta.

## Base de datos

- **PostgreSQL** vía psycopg2-binary + SQLAlchemy 2.0.
- Configuración: `DATABASE_URL` completa, o los campos `DB_HOST_PG / DB_PORT_PG / DB_USER_PG / DB_PASSWORD_PG / DB_NAME_PG`.
- Las tablas se auto-crean al arrancar con `Base.metadata.create_all`. **No hay sistema de migraciones**: un cambio de columna sobre una tabla existente no se aplica solo.
- `SQL/` contiene scripts del dominio de lavandería. **Están obsoletos**, no los uses como referencia del esquema — la fuente de verdad es `app/models/inventario.py`.

### Tablas del dominio EPP

**`productos_epp`** — catálogo (una fila por tipo de EPP, no por unidad): `producto_id`, `nombre` UNIQUE, `categoria_id`, `talla_aplica`, `certificacion`, `activo`.

**`stock_epp`** — existencias por producto+talla. Stock **global**, un solo bodegón sin segregar por empresa: `producto_id`, `talla_id` (NULL si el producto no maneja tallas), `cantidad_actual`, `stock_minimo`, UNIQUE(producto_id, talla_id).

**`movimientos_stock`** — libro mayor: `tipo` ∈ `INGRESO_IMPORT | ENTREGA | BAJA_DANO | AJUSTE`, `cantidad` (positiva o negativa), `referencia_id`, `fecha`.

**`entregas_epp`** — entrega de EPP a un trabajador: `rut`, `nombre_completo` y `empresa_id` (denormalizados al momento de la entrega), `producto_id`, `talla_id`, `cantidad`, `motivo` ∈ `NUEVA | PERDIDA | DANO`, `entrega_reemplazada_id`, `estado_firma`, `fecha_entrega`, `uuid` UNIQUE (idempotencia offline).

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

**Talla NULL.** En PostgreSQL `NULL = NULL` es NULL, así que el `UNIQUE(producto_id, talla_id)` **no** impide filas duplicadas para productos sin talla. Todo lookup, upsert o join por (producto, talla) usa `talla_id IS NOT DISTINCT FROM :talla_id`.

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
- Un trabajador desvinculado no puede recibir EPP nuevo, pero sus entregas se conservan y se pueden consultar.

## Autenticación

**Login** — `LoginRequest` es `{ username, contrasena }`; el campo es **`contrasena`**, no `password`. La columna `usuarios.username` es el nombre de usuario (en la lavandería era `nombre_completo`; ya no).

**Sesión por cookie httpOnly** llamada `authToken`. `security.py` la lee primero y cae al header `Authorization` como respaldo (Swagger/debug). El logout invalida el `jti` en `token_blacklist`.

**JWT**: `{ userId, username, role, modulos, exp, jti }`, expira en 480 minutos.

**`UserResponse`**: `{ id, username, email, role, modulos }` — el campo es `role`, no `rol`.

**Permisos por módulo**: `require_module("nombre")` como dependencia FastAPI. Los roles en `FULL_ACCESS_ROLES = ("admin", "administrador")` tienen bypass total; el resto necesita el módulo en su lista. Módulos: `dashboard`, `inventario`, `entregas`, `personal`, `reportes`, `configuracion`, `superadmin`.

Credenciales por defecto: `admin` / `admin123`.

## Frontend

React 19 + Vite 7, React Router 7, Recharts, TanStack Table, react-hot-toast, Dexie.

- **Pages** (`src/pages/`), **components** (`src/components/` por dominio), **services** (`src/services/`, todos importan `apiClient` de `api.js`).
- `apiClient` lee `VITE_API_URL` o cae a `http://localhost:8000/api`, y manda `credentials: 'include'` para la cookie.
- **La navegación real es `components/layout/TopNav.jsx`.** `Sidebar.jsx` existe pero **no lo importa nadie** — no lo edites creyendo que se ve.
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

- Endpoint: `POST /api/personal/sync` (acepta `?dry_run=true`)
- CLI para el scheduler: `Backend/sync_personal.py`
- Runbook completo: `docs/runbook-sync-personal.md`

## Reportabilidad

Principio: **una query por reporte, dos presentaciones.** Cada reporte tiene un único método de repository que devuelve `List[dict]`; la ruta JSON y la `.xlsx` consumen las mismas filas, así que la tabla en pantalla y el archivo exportado no pueden divergir. Al agregar un reporte, respetá esto.

Motor Excel: `app/services/excel_builder.py` — infraestructura sin dominio, columnas declaradas por reporte con `Columna(key, label, ancho, formato, fmt)`.

Diseño y decisiones: `docs/plans/2026-07-27-fase5-reportabilidad-design.md`.

## Código muerto conocido

Sobrevivientes de la poda del dominio de lavandería. **No los uses como referencia y no los "arregles"** — corresponde borrarlos.

**Backend**
- `app/api/v1/endpoints/asignaciones.py` y `devoluciones.py` — no registrados en `api.py`; consultan `lecturas_rfid`, que no existe.
- `app/repositories/asignaciones_repository.py` y `app/services/asignaciones_service.py` — solo los usan los dos anteriores.
- `app/repositories/catalogos_repository.py` y `app/services/catalogos_service.py` — **nadie los importa**; `inventario.py` hace SQL directo.
- `app/repositories/auditoria_repository.py` — sin uso.
- `__pycache__` con `.pyc` de módulos ya borrados (`biometria`, `endpoints_rfid`, `rfid_repository`).

**Frontend**
- `pages/Returns.jsx`, `components/returns/` y `services/returnsService.js` — no ruteados; la sustitución vive dentro del flujo de entrega.
- `components/layout/Sidebar.jsx` — reemplazado por TopNav.
- `services/personalCacheService.js` y `api/offlineWrapper.js` — sin importadores.
- `services/catalogosService.js` — solo `getTallas` tiene backend; `/inventario/tipos`, `/secciones` y `/temporadas` ya no existen.
- `services/staffService.js` — `getDepartments()` y el CRUD `/staff/*` no tienen backend; solo `getEmployees()` (contra `/personal/todos`) funciona.

**SQL** — todo `SQL/` describe el esquema de lavandería.

## Deuda y pendientes

| Tema | Estado |
|---|---|
| Área en reportes | Se usa el área **actual** del trabajador. Si el negocio necesita la histórica hay que denormalizar `area_id` en `entregas_epp` — decisión con fecha de vencimiento, cada día acumula historial |
| Stock valorizado | No hay precio en `productos_epp` |
| Capa offline | Dexie, `syncManager` y `OfflineBanner` están montados en `main.jsx`, pero **nada encola operaciones** (`offlineWrapper` no lo usa nadie): la cola nunca se llena |
| Imágenes Docker | `compose.yml` todavía apunta a `ghcr.io/bgacitua/lavanderia-*` — falta el rename del fork |
| Módulo `superadmin` | No está asignado a ningún rol; `admin` entra por bypass |
| Rol `administrador` | Falta probar el login en runtime con ese rol |
| Migraciones | No hay. Cambiar una columna existente requiere hacerlo a mano en la BD |
| Ramas | `main`, `fase-1`, `fase-4`, `fase-5` en el remoto; **ninguna fase está mergeada a `main`** |
