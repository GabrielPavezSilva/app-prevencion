# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sistema de Lavandería Industrial — a laundry management system with RFID tag integration, inventory tracking, staff management, and biometric fingerprint authentication (DigitalPersona U.are.U 4500). The app has a Python/FastAPI backend and a React/Vite frontend.

## Commands

### Backend (desarrollo local)
```bash
cd Backend
pip install -r requirements.txt          # Install dependencies
uvicorn main:app --reload --port 8000    # Run dev server
python seed_admin.py                      # Seed admin user (first time only)
```

### Frontend (desarrollo local)
```bash
cd Frontend
npm install       # Install dependencies
npm run dev       # Dev server (http://localhost:5173)
npm run build     # Production build
npm run lint      # ESLint
```

### Docker (producción en VPS)
```bash
# 1. Crear .env desde el ejemplo y completar valores
cp .env.example .env

# 2. Levantar todo (primera vez incluye build)
docker compose up -d --build

# 3. Seed del admin (solo primera vez)
docker compose exec backend python seed_admin.py

# 4. Reconstruir un servicio tras cambios
docker compose up -d --build backend
docker compose up -d --build frontend
```

No test suite exists yet. Manual testing via Swagger UI at `http://localhost:8000/docs` (local) o `https://civot.cramer.cl/docs` (producción).

## Architecture

### Backend (Clean Architecture / Repository Pattern)

```
Endpoints (app/api/v1/endpoints/) → Services (app/services/) → Repositories (app/repositories/) → MySQL
```

- **Schemas** (`app/schemas/`): Pydantic models for request/response validation
- **Models** (`app/models/inventario.py`): All SQLAlchemy ORM models in a single file; must be imported in `main.py` for `Base.metadata.create_all` to register them
- **Core** (`app/core/`): Settings (`config.py`), JWT auth (`security.py`), logging (`logging_config.py`)
- **DB** (`app/db/`): Session factory (`session_mysql.py`); `deps.py` exposes `get_mysql_db()` for FastAPI `Depends`
- **Repositories**: Use `sqlalchemy.text()` (raw SQL), not ORM query API
- **Entry point**: `main.py` — configures CORS, mounts routers, auto-creates tables on startup

**Exception:** `inventario.py` endpoint calls `CatalogosRepository` directly (no service layer). Functional but breaks strict separation.

### Adding a new backend endpoint

1. Pydantic schema in `app/schemas/`
2. Repository methods in `app/repositories/` — use `sqlalchemy.text()` for all SQL
3. Service logic in `app/services/`
4. Endpoint in `app/api/v1/endpoints/`
5. **Register router in `app/api/v1/api.py`** ← easy to forget

### Frontend (React SPA)

- **Pages** (`src/pages/`): Main views routed via React Router
- **Components** (`src/components/`): Organized by domain (dashboard, staff, returns, reports, worker, fingerprint, layout, inventory)
  - `inventory/TabRealizarInventario.jsx` — RFID bulk scan tab (mounted inside `Inventory.jsx`)
- **Services** (`src/services/`): All import `apiClient` from `api.js` (default export singleton); reads `VITE_API_URL` or defaults to `http://localhost:8000/api`
- **Context** (`src/context/AuthContext.jsx`): Auth state; token stored in localStorage
- **Charts**: Recharts library
- **Toasts**: `react-hot-toast` — `<Toaster position="bottom-right" />` mounted in `main.jsx`. Use `toast.success()` / `toast.error()` instead of `alert()`.

### Frontend Routes (App.jsx)

| Path | Role | Component |
|------|------|-----------|
| `/login` | Public | Login |
| `/` | admin | Dashboard |
| `/inventario` | admin | Inventory (7 tabs: Prendas, Tipos, Tallas, Secciones, Temporadas, Realizar Inventario, Revisar prenda) — ver nota abajo |
| `/personal` | admin | Staff (includes return management — clicking "Prendas Activas" badge opens PrendasModal) |
| `/reportes` | admin | Reports |
| `/inventario-rfid` | — | Redirects to `/inventario` (legacy, no sidebar entry) |
| `/configuracion` | admin | Settings |
| `/worker` | worker, admin | WorkerDashboard |

Adding a new page also requires adding an entry to `src/components/layout/Sidebar.jsx`.

**Nota:** La validación de roles en `ProtectedRoute` está actualmente **comentada** — cualquier usuario autenticado puede acceder a cualquier ruta (sin redirección por rol). Solo el redirect en `/login` según `user.role` permanece activo.

**Tab "Prendas" — estado actual:**
- Columnas visibles: **SKU → Estado → Tipo Prenda (compuesta) → Empresa → Acciones** (anchos: 28% / 14% / 40% / 10% / 8%).
- Columna "Tipo Prenda" es compuesta: `tipo · talla · sección · temporada`, separadas por ` · `, omite valores vacíos.
- Tabla usa variante `.inventory-table-container--wide` (`min-width: 880px`) para que SKU largo + compuesto no colapse.

### CSS Variables (src/styles/index.css)

| Variable | Value | Use |
|----------|-------|-----|
| `--color-primary` | `#1e293b` | Charcoal — generic dark references |
| `--color-accent` | `#6366f1` | Indigo — tabs, buttons, focus rings |
| `--color-brand` | `#ef4444` | Red — logo "Uniform Tracker" + critical errors |
| `--color-bg-sidebar` | `#1e293b` | Sidebar background |

## Authentication

### Login flow
- `LoginRequest` schema: `{ username: str, contrasena: str }` — field is `contrasena`, NOT `password`
- `authService.js` sends: `apiClient.post('/auth/login', { username, contrasena })`
- `AuthRepository.get_user_by_username()` queries by `nombre_completo` column (this is the username field in `usuarios` table)
- `auth_service.py` accesses result dict keys: `user["user_id"]`, `user["username"]`, `user["nombre_rol"]`
- `UserResponse` schema: `{ id, username, email, role }` — field is `role` (not `rol`)
- Password verification: bcrypt via passlib with plaintext fallback for dev environments

### JWT payload
`{ userId, username, role }` — expires in 480 minutes (8 hours)

### Default credentials
- Admin: `admin` / `admin123` (stored as `nombre_completo = 'admin'` in `usuarios` table)

### `seed_admin.py`
Creates or updates the admin user — idempotent (safe to re-run). Uses `nombre_completo` column as username, `correo` for email, hashes password with bcrypt. If the user already exists, it updates the password and role.

## API Routes

Currently registered in `app/api/v1/api.py`:

| Module | Prefix | Purpose |
|--------|--------|---------|
| Auth | `/api/auth` | Login/logout, JWT tokens |
| Personal | `/api/personal` | Staff/employee management |
| RFID | `/api/rfid` | RFID reader control, tag linking, reading log, inventory mode |
| Stats | `/api/stats` | Aggregated dashboard statistics |
| Asignaciones | `/api/asignaciones` | Assignment history (GET /todas) |
| Inventario | `/api/inventario` | Tipos de prenda y tallas (catálogos) |
| Biometría | `/api/biometria` | Fingerprint identification (1:N) and enrollment (4 captures) |
| Devoluciones | `/api/returns` | Return management — GET /employees, GET /employees/{rut}/items, POST /process |

**Inventario sub-routes** (prefix `/api/inventario`):
- `GET /tipos`, `POST /tipos`, `PUT /tipos/{tipo_id}`, `DELETE /tipos/{tipo_id}` — catálogo tiposPrendas
- `GET /tallas`, `POST /tallas`, `PUT /tallas/{talla_id}`, `DELETE /tallas/{talla_id}` — catálogo tallas
- `GET /secciones`, `POST /secciones`, `PUT /secciones/{seccion_id}`, `DELETE /secciones/{seccion_id}` — catálogo secciones
- `GET /temporadas`, `POST /temporadas`, `PUT /temporadas/{temporada_id}`, `DELETE /temporadas/{temporada_id}` — catálogo temporadas
- Note: these endpoints call `CatalogosRepository` directly (no service layer)

**Note**: `app/api/v1/endpoints/reportes.py` exists but is **not registered** (Excel streaming, needs wiring to `api.py`).

**Arquitectura de comunicación (producción Docker)**:
```
Browser (en red local lavandería)
 ├── apiClient  → https://civot.cramer.cl/api  → VPS: Nginx → Backend → PostgreSQL
 └── hardwareClient → http://localhost:5050    → HardwareMiddleware.exe (Windows local)
                                                      ├── RFID COM2/COM3
                                                      └── Huella USB (DigitalPersona)
```
El HardwareMiddleware corre como servicio Windows en la máquina física con el hardware. El browser lo llama directamente en `localhost:5050`. Su CORS acepta `https://civot.cramer.cl` vía `frontend_url` en `%ProgramData%\LavanderiaMiddleware\config.ini`.

**RFID sub-routes** (prefix `/api/rfid`):
- `POST /lectura`, `GET /buscar/{epc}`, `POST /vincular`, `GET /log` — log/persistence
- `GET /lecturas` — full active inventory from `lecturas_rfid` (used by frontend Inventory table); implemented via `ReportesRepository.get_inventario()`
- `/reader/status`, `/reader/connect`, `/reader/disconnect`, `/reader/scan`, `/reader/read/{epc}`, `/reader/write` — hardware control (all accept `?role=reception|assignment`, default: `assignment`)
- `/inventario/iniciar`, `/inventario/detener`, `/inventario/estado` — bulk inventory mode
- `/inventario/scan` — acepta `{ epc: string }` en el body; el frontend obtiene el EPC desde `hardwareClient.post('/rfid/scan?role=assignment')` y lo envía aquí para persistencia
- `PATCH /inventario/prenda/{sku}`, `DELETE /inventario/prenda/{sku}/tag` — adjustment mode

`POST /reader/scan` response: `{ encontrado, epc?, sku?, hardware_error, hardware_role? }` — `hardware_error=true` means the physical reader is unresponsive.

**Biometría sub-routes** (prefix `/api/biometria`):
- `POST /identificar` — starts 1:N fingerprint identification session → `{session_id}`
- `POST /enrolar/{rut}` — starts 4-capture enrollment session → `{session_id}`
- `GET /estado/{session_id}` — polling endpoint for session status → `{session_id, tipo, status, paso_actual, pasos_total, resultado?, error?}`
- `POST /cancelar/{session_id}` — cancels active session
- `GET /reader/status` — USB reader status → `{conectado, ocupado, error?}`
- `DELETE /huella/{rut}` — removes stored fingerprint template
- **Architecture**: `BiometriaManager` singleton (`app/services/biometria_manager.py`) manages the U.are.U 4500 reader via pythonnet + DPUruNet DLLs. Background threads for non-blocking captures. Sessions stored in memory (auto-cleanup after 5min).

## Database

- **Engine**: PostgreSQL via psycopg2-binary + SQLAlchemy 2.0
- **Schema script**: `SQL/Creacion_de_tablas_my_sql.sql` (SQL escrito para MySQL — revisar compatibilidad antes de ejecutar manualmente en PostgreSQL; las tablas se auto-crean con `Base.metadata.create_all`)
- **Configuración**: variable `DATABASE_URL` (Docker) o campos `DB_HOST_PG / DB_PORT_PG / DB_USER_PG / DB_PASSWORD_PG / DB_NAME_PG` (`.env` local)
- Tables are auto-created on backend startup via `Base.metadata.create_all`

### Nota de compatibilidad SQL
Los repositories usan `sqlalchemy.text()` con SQL escrito originalmente para MySQL. Al migrar a PostgreSQL verificar:
- `IFNULL(x, y)` → `COALESCE(x, y)`
- Backticks `` `col` `` → sin quotes o `"col"`
- `BIT` columns → SQLAlchemy los mapea a `Boolean` correctamente en PostgreSQL

### Key tables

**`usuarios`** — system login accounts:
- `user_id` INT PK, `nombre_completo` VARCHAR(100) UNIQUE (this is the username), `correo` VARCHAR(100) UNIQUE, `contrasena` VARCHAR(255) (bcrypt hash), `rol_id` FK→roles, `activo` BIT

**`personal`** — laundry employees:
- `rut` VARCHAR(20) PK, `nombre_completo`, `empresa` VARCHAR(100) (free text, NOT FK), `cargo`, `area_id` FK→areas, `subarea_id` FK→subareas, `talla_id` FK→tallas, `huella_digital` LONGBLOB (biometric encoding)

**`lecturas_rfid`** — central inventory table (dual purpose: inventory + RFID scan log). Each row is one physical garment:
- `sku` VARCHAR(100) UNIQUE — generated as `TIPO_PRENDA-0042`
- `tag_epc` VARCHAR(50) — EPC of the RFID chip
- `accion` VARCHAR(50) — last action (e.g., `INVENTARIO`, `ASIGNACION`, `RECEPCION`)
- `resultado` VARCHAR(50) — result of the action
- `estado_disponible` BIT — 1 = available, 0 = assigned
- `empresa_id` FK→empresa, `tipo_id` FK→tiposPrendas, `talla_id` FK→tallas

**`asignaciones`** — delivery/return history:
- `rut` FK→personal, `nombre_completo` (denormalized), `sku`, `tag_epc`, `fecha_entrega`, `fecha_devolucion` (NULL until returned)

**`modulos` / `roles_modulos`** — defined in SQL schema but not yet used by the backend application.

## Environment Variables

**Producción — `.env` en raíz del proyecto** (usado por `docker-compose.yml`):
```
POSTGRES_DB=db_lavanderia
POSTGRES_USER=lavanderia
POSTGRES_PASSWORD=<contraseña segura>
JWT_SECRET_KEY=<clave hex aleatoria larga>
```
Ver `.env.example` para la plantilla documentada.

**Backend local** (`Backend/.env`):
```
# Opción A: URL completa (recomendado)
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/db_lavanderia

# Opción B: campos individuales
DB_HOST_PG=localhost
DB_PORT_PG=5432
DB_USER_PG=root
DB_PASSWORD_PG=your_password
DB_NAME_PG=db_lavanderia

JWT_SECRET_KEY=long_secret_key
RFID_RECEPTION_PORT=COM2
RFID_ASSIGNMENT_PORT=COM3
```

**Frontend** (`Frontend/.env`):
```
VITE_API_URL=http://localhost:8000/api    # Desarrollo local
VITE_HARDWARE_URL=http://localhost:5050   # HardwareMiddleware local (default)
```
En producción estos valores se inyectan en tiempo de build via `docker-compose.yml` (`VITE_API_URL=https://civot.cramer.cl/api`).

## Hardware Integration

- **RFID**: Two dedicated UHF readers via serial port (`app/services/uhf_reader.py`).
  - `UHFReader`: low-level binary protocol with CRC16.
  - `MultiReaderManager`: manages `{ "reception": UHFReader, "assignment": UHFReader }`. Each reader has its own `threading.Lock()`. Exported as `multi_reader_manager` singleton.
  - `VALID_ROLES = ("reception", "assignment")` — constant in `uhf_reader.py`, used for endpoint validation via `_validate_role()`.
  - Lazy connection: readers connect on first use, not at startup.
  - `app/api/v1/endpoints/lectura.py` is a **standalone CLI tool** (run directly with Python), not a FastAPI endpoint.
- **Fingerprint**: DigitalPersona U.are.U 4500 via pythonnet + DPUruNet SDK (`app/services/biometria_manager.py`).
  - `BiometriaManager`: singleton managing reader access, capture sessions in memory, background threads. Exported as `biometria_manager`.
  - SDK DLLs: `C:\Program Files\DigitalPersona\U.are.U SDK\Windows\Lib\.NET` and `\x64`. Auto-detected; degrades gracefully if missing.
  - `pythonnet` (`clr`) is listed in `requirements.txt` — `pip install -r requirements.txt` installs it. **Must be installed inside the active venv**, not just system Python; otherwise `GET /biometria/reader/status` returns `{"conectado": false, "error": "No module named 'clr'"}`.
  - Uses `CaptureAsync` (not sync `Capture`), callbacks as module-level functions (pythonnet limitation), `CancelCapture()` after every capture.
  - Templates stored as LONGBLOB in `personal.huella_digital`. Identification uses `Comparison.Identify()` (1:N, FAR threshold 21474 = 1/100,000).
  - Frontend: `FingerprintControl.jsx` component (identification + enrollment), integrated in WorkerDashboard (identify) and Staff (enroll).
- **Facial Recognition**: OpenCV + face_recognition (`reconocimiento-facial.py` at repo root). Legacy — superseded by fingerprint biometrics above.

## Key Details

- CORS allows `localhost:5173`, `localhost:3000`, and `127.0.0.1` variants
- JWT tokens expire in 480 minutes (8 hours), payload includes `userId`, `username`, `role`
- Logger name: `"lavanderia"`, level INFO, console output
- UI and comments are in Spanish

### Staff Page (`/personal`)

- **Backend**: `GET /personal/todos?search=...` returns a **flat array** `[{rut, nombre_completo, empresa, cargo, area_id, subarea_id, talla_id}]` — no pagination, no wrapping object.
- **Frontend mapping**: `Staff.jsx` maps backend fields → `{id: rut, rut, name: nombre_completo, department: empresa, cargo}`.
- **Table columns**: EMPLEADO (avatar + name + empresa + RUT) | CARGO | ACCIONES (fingerprint + edit).
- **Fingerprint enrollment**: Button 👆 opens modal with `FingerprintControl` in `mode="registration"` passing `rut` as prop.
- **`+ Agregar Empleado` button**: Present in UI but non-functional (TODO — `handleAddEmployee` is empty stub).
- **`staffService.js` dead routes**: `getDepartments()` calls `/staff/departments` (404, harmless). `getEmployeeById`, `createEmployee`, `updateEmployee`, `deleteEmployee` call `/staff/employees/*` (not implemented). Only `getEmployees()` works (calls `/personal/todos`).
- **Seed data**: `SQL/seed_datos_prueba.sql` uses the legacy `inventario` table schema (PascalCase columns, old structure). **Does not work with current `lecturas_rfid` schema.** For `personal` table, insert manually with correct FK references.

### WorkerDashboard — Identificación de trabajador

El `ScanningPanel` usa identificación **biométrica como método principal** para el modo "Asignar":
1. Botón "Identificar con Huella" → `huellasService.iniciarIdentificacion()` → polling hasta completado
2. Si el backend retorna `resultado.rut/nombre_completo`, se carga el trabajador automáticamente
3. Fallback "Modo Manual (RUT)": búsqueda por texto contra `GET /personal/todos?search=...`
4. El resultado de biometría retorna keys `Rut`/`NombreCompleto`; la búsqueda manual retorna `rut`/`nombre_completo` — el código acepta ambas formas (`workerData.Rut || workerData.rut`).

## Known Issues / Incomplete Features

| Problem | Impact |
|---------|--------|
| `reportes.py` not registered in `api.py` | Reports page uses mock data |
| `staffService.js` has dead routes (`/staff/employees/*`, `/staff/departments`) | Only `getEmployees()` works via `/personal/todos`; CRUD and departments not implemented |
| `+ Agregar Empleado` button in Staff.jsx | Present in UI, `handleAddEmployee` is empty stub — not implemented |
| `alertService.js` calls `/alerts/*` (no backend) | Alerts non-functional |
| `inventoryService.js` calls `/inventory/categories/*` (no backend) | Those calls silently fail |
| `modulos`/`roles_modulos` tables defined in SQL but unused | Module-level access control not implemented |
| `inventario.py` skips service layer | Calls CatalogosRepository directly from endpoint |
| `InventoryMode.jsx` / route `/inventario-rfid` | Legacy file kept on disk; route redirects to `/inventario`; can be deleted in future cleanup |
| Tab Prendas — columnas Tag EPC y Acción | Comentadas (no eliminadas) en `Inventory.jsx`; badge Estado muestra "Pendiente" como placeholder. Pendiente habilitar en fase de asignaciones. |
| `ProtectedRoute` role validation | Commented out in `App.jsx` — all authenticated users bypass role-based redirects |
| `SQL/seed_datos_prueba.sql` | Targets legacy `inventario` table (PascalCase columns). Does not work with current `lecturas_rfid` schema. Needs rewrite. |
