# Guía de Arquitectura — Sistema de Lavandería Industrial

Esta guía está pensada para alguien que llega al proyecto por primera vez y necesita entender qué hace cada parte, cómo se comunican y por qué están organizadas así.

---

## ¿Qué es este sistema?

Es una aplicación web para gestionar el inventario de prendas de una lavandería industrial. Las prendas tienen chips RFID físicos que permiten identificarlas, asignarlas a trabajadores y registrar devoluciones. El sistema también gestiona personal, genera reportes y tiene un portal diferenciado para operarios.

---

## Estructura General del Repositorio

```
app-lavanderia/
├── Backend/          # Servidor Python / FastAPI
├── Frontend/         # Aplicación web React / Vite
├── SQL/              # Script DDL para crear la base de datos MySQL
├── CLAUDE.md         # Instrucciones para Claude Code
└── ARQUITECTURA.md   # Este archivo
```

---

## Cómo se comunican las partes

```
┌──────────────────────────────────────────────────────────┐
│                    Navegador del usuario                  │
│                                                          │
│   React SPA (Frontend - puerto 5173)                     │
│   └── Llama al backend via HTTP (fetch/JSON)             │
└──────────────────┬───────────────────────────────────────┘
                   │ HTTP REST (JSON)
                   ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Backend (puerto 8000)                │
│   /api/auth  /api/inventario  /api/rfid  /api/stats      │
│   └── Accede a MySQL via SQLAlchemy ORM                  │
└──────────────────┬───────────────────────────────────────┘
                   │ SQL
                   ▼
┌──────────────────────────────────────────────────────────┐
│               MySQL (base de datos)                      │
│   usuarios, personal, lecturas_rfid, asignaciones, ...   │
└──────────────────────────────────────────────────────────┘
                   ▲                    ▲
                   │ COM2 (Recepción)    │ COM3 (Asignación)
┌──────────────────┴────────────────────┴─────────────────┐
│           Lectores RFID UHF (hardware físico)            │
│   Lector Recepción  → WorkerDashboard "Recibir"          │
│   Lector Asignación → WorkerDashboard "Asignar" +        │
│                        InventoryMode                     │
└──────────────────────────────────────────────────────────┘
```

El frontend nunca habla directamente con la base de datos ni con el hardware. Todo pasa por el backend.

---

## BACKEND

### Punto de entrada: `Backend/main.py`

Es el archivo que arranca todo. Al iniciarse:

1. Importa todos los modelos ORM para que SQLAlchemy los conozca.
2. Crea automáticamente las tablas en MySQL si no existen (`Base.metadata.create_all`).
3. Configura CORS para permitir que el frontend (en `localhost:5173`) pueda hacer peticiones.
4. Monta el router principal bajo el prefijo `/api`.

```bash
# Para correr el backend en modo desarrollo:
cd Backend
uvicorn main:app --reload --port 8000
```

---

### Arquitectura interna del Backend

El backend sigue el patrón **Clean Architecture con Repository Pattern**:

```
Petición HTTP
     │
     ▼
┌─────────────┐
│  Endpoint   │  app/api/v1/endpoints/  → Recibe la petición, valida con Pydantic, llama al servicio
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service   │  app/services/          → Lógica de negocio (reglas, validaciones, orquestación)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Repository  │  app/repositories/      → Acceso a datos (SQL puro con sqlalchemy.text())
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    MySQL    │  Tablas reales en la base de datos
└─────────────┘
```

**Excepción conocida:** El endpoint `inventario.py` llama al `CatalogosRepository` directamente, sin pasar por una capa de service. Esto es funcional pero rompe la separación estricta.

**¿Por qué esta separación?**
- Los endpoints no saben nada de SQL; solo reciben y envían JSON.
- Los repositorios no saben nada de reglas de negocio; solo ejecutan consultas.
- Si mañana cambia la base de datos, solo se toca el repositorio.

---

### Módulos del Backend

#### `app/core/` — Configuración y utilidades globales

| Archivo | Qué hace |
|---------|----------|
| `config.py` | Lee variables de entorno desde `Backend/.env` usando Pydantic Settings. Define la URL de conexión a MySQL. |
| `security.py` | Genera y valida tokens JWT. El token contiene `userId`, `username` y `role`. Expira en 8 horas. |
| `logging_config.py` | Logger global llamado `"lavanderia"`, nivel INFO, salida a consola. |

**Variables de entorno requeridas (`Backend/.env`):**
```
DB_SERVER_MYSQL=localhost
DB_PORT_MYSQL=3306
DB_USER_MYSQL=root
DB_PASSWORD_MYSQL=tu_password
DB_NAME_MYSQL=db_lavanderia
JWT_SECRET_KEY=una_clave_secreta_larga
RFID_RECEPTION_PORT=COM2    # Lector de Recepción (WorkerDashboard "Recibir")
RFID_ASSIGNMENT_PORT=COM3   # Lector de Asignación + InventoryMode
RFID_BAUDRATE=57600
```
Ver `Backend/.env.example` para la plantilla completa documentada.

---

#### `app/db/` — Conexión a la base de datos

| Archivo | Qué hace |
|---------|----------|
| `session_mysql.py` | Crea el motor SQLAlchemy y la fábrica de sesiones `MysqlSessionLocal`. |
| `deps.py` | Define `get_mysql_db()`: generador que FastAPI inyecta en los endpoints con `Depends(get_mysql_db)`. Abre una sesión, la entrega y la cierra al terminar (patrón context manager). |

---

#### `app/models/inventario.py` — Modelos ORM

**Todos los modelos están en un único archivo.** Cada clase Python representa una tabla en MySQL:

| Clase ORM | Tabla MySQL | Propósito |
|-----------|-------------|-----------|
| `Rol` | `roles` | Roles de usuario (admin, worker) |
| `Usuario` | `usuarios` | Cuentas de acceso al sistema |
| `Personal` | `personal` | Empleados de la lavandería (RUT como PK) |
| `Area` / `SubArea` | `areas` / `subareas` | Catálogo de áreas organizacionales |
| `Empresa` | `empresa` | Catálogo de empresas cliente |
| `TipoPrenda` | `tiposPrendas` | Catálogo de tipos (ej: "Pantalón Blanco") |
| `Talla` | `tallas` | Catálogo de tallas (S, M, L, XL…) |
| `LecturaRFID` | `lecturas_rfid` | **Inventario real de prendas físicas** (una fila = una prenda) |
| `Asignacion` | `asignaciones` | Historial de entregas y devoluciones |

**Nota importante:** La tabla `lecturas_rfid` tiene doble propósito: es el inventario de prendas Y el log de lecturas RFID. Cada prenda tiene un `sku` único y puede tener un `tag_epc` (EPC del chip RFID).

---

#### `app/schemas/` — Validación con Pydantic

Los schemas definen qué datos acepta y devuelve cada endpoint. FastAPI los usa automáticamente para:
- Validar el cuerpo de las peticiones entrantes.
- Serializar la respuesta saliente.
- Generar la documentación Swagger en `/docs`.

| Archivo | Schemas principales |
|---------|---------------------|
| `auth.py` | `LoginRequest` (`username` + `contrasena`), `LoginResponse` (`token` + `user`), `UserResponse` |
| `inventario.py` | `InventarioResponse` (con nombre de tipo, talla y empresa) |
| `tipos_prendas.py` | `TiposPrendasCreate`, `TiposPrendasUpdate`, `TiposPrendasResponse` |
| `tallas.py` | `TallasCreate`, `TallasUpdate`, `TallasResponse` |
| `rfid.py` | Schemas para cada operación RFID (escaneo, escritura, modo inventario…) |
| `stats.py` | `InventarioStatsResponse` (KPIs del dashboard) |
| `personal.py` | `PersonalResponse` |
| `asignaciones.py` | `AsignacionesResponse` |

**Importante — campo de login:** El campo de contraseña en `LoginRequest` es `contrasena` (no `password`). El frontend (`authService.js`) envía `{ username, contrasena }`.

---

#### `app/repositories/` — Acceso a datos

Los repositorios ejecutan SQL con `sqlalchemy.text()` (SQL nativo, no ORM de alto nivel). Reciben una sesión de base de datos y retornan datos crudos o None.

| Repositorio | Responsabilidad |
|-------------|----------------|
| `auth_repository.py` | Buscar usuario por `nombre_completo` (campo de username) con JOIN usuarios+roles. También soporta búsqueda por correo. |
| `inventario_repository.py` | CRUD de prendas en `lecturas_rfid` |
| `catalogos_repository.py` | CRUD de `tiposPrendas` y `tallas`, incluyendo validación de uso |
| `personal_repository.py` | Listar y buscar empleados con filtro LIKE |
| `rfid_repository.py` | Operaciones RFID: vincular tags, buscar por EPC/SKU, gestionar inventario en sesión |
| `asignaciones_repository.py` | Crear/finalizar asignaciones, cerrar asignaciones previas antes de crear una nueva |
| `reportes_repository.py` | Consultas para generación de archivos Excel. También expone `get_inventario()` usado por `GET /rfid/lecturas` |

---

#### `app/services/` — Lógica de negocio

Los servicios orquestan repositorios y aplican reglas de negocio. Son los que "piensan".

**`auth_service.py`:**
Verifica la contraseña con bcrypt (con fallback a texto plano para desarrollo), genera el JWT y retorna el token con datos del usuario. Accede a `user["user_id"]`, `user["username"]` y `user["nombre_rol"]` del resultado del repositorio.

**`catalogos_service.py`:**
Valida que el nombre no esté vacío ni repetido. Al eliminar un tipo/talla, verifica que no tenga prendas vinculadas (HTTP 400 si las tiene).

**`rfid_service.py`** — El más complejo:
- Delega el hardware a `multi_reader_manager`; todos los métodos de hardware aceptan `role: str = "assignment"`.
- `scan_tag(role)`: si el lector no responde, retorna `hardware_error=True` con el rol afectado (en lugar de lanzar excepción).
- Implementa el **modo inventario**: mantiene una sesión activa con `tipo_id`, `talla_id` y un set de EPCs ya escaneados en esta sesión. Siempre usa el lector `"assignment"` internamente.
- **Generación de SKU:** toma el nombre del tipo de prenda (ej: "Pantalón Blanco"), lo convierte a `PANTALON_BLANCO`, busca el último correlativo en BD y genera `PANTALON_BLANCO-0001`.
- Lógica de **asignación vs recepción**: al recibir una lectura RFID con `accion: "ASIGNACION"`, crea un registro en `asignaciones`. Con `"RECEPCION"`, cierra la asignación activa.

**`reportes_service.py`:**
Usa `openpyxl` para construir archivos Excel en memoria (sin tocar disco). Devuelve un `BytesIO` que FastAPI transmite como `StreamingResponse`.

---

#### `app/services/uhf_reader.py` — Hardware RFID

Tres elementos exportados:

**`UHFReader`:** Comunicación de bajo nivel con el lector UHF por puerto serial.
- Implementa el protocolo binario del lector (comandos, CRC16, parsing de respuesta).
- `inventario()` → escanea y devuelve EPC del tag más cercano.
- `leer_user(epc, palabras)` → lee memoria USER del chip.
- `escribir_user(epc, hex_data)` → escribe datos en el chip.

**`VALID_ROLES`:** Constante de módulo `("reception", "assignment")`. Usada para validación en endpoints y service.

**`MultiReaderManager`:** Gestiona dos lectores en paralelo.
- Diccionario interno `{ "reception": UHFReader, "assignment": UHFReader }` inicializado con los puertos de configuración.
- Cada rol tiene su propio `threading.Lock()` → recepción no bloquea a asignación y viceversa.
- Conexión lazy: el lector se conecta al primer `scan()` si no está ya conectado.
- Se exporta como `multi_reader_manager` (singleton de módulo).
- Métodos principales: `scan(role)`, `status(role)`, `conectar(role)`, `desconectar(role)`, `leer_user(role, epc, palabras)`, `escribir_user(role, epc, hex_data)`.

---

#### `app/services/biometria_manager.py` — Hardware Huella Digital

**`BiometriaManager`:** Gestiona el lector U.are.U 4500 y las sesiones de captura.
- Singleton exportado como `biometria_manager`. Patrón análogo a `MultiReaderManager`.
- SDK: pythonnet + DPUruNet DLLs desde `C:\Program Files\DigitalPersona\U.are.U SDK\Windows\Lib\.NET` y `\x64`. Se carga al importar el módulo; si las DLLs no existen, opera en modo degradado (`conectado=False`).
- **`pythonnet` debe estar instalado en el venv** (`pip install -r requirements.txt` lo cubre). Si solo está en el Python del sistema y no en el venv, el endpoint devuelve `{"conectado": false, "error": "No module named 'clr'"}`.
- Sesiones en memoria (`_sesiones` dict) con TTL de 5 minutos y limpieza automática en thread daemon.
- Callbacks de captura a nivel de módulo (limitación pythonnet: no acepta bound methods como delegates .NET).
- Usos principales:
  - `get_reader_status()` → `{ conectado, ocupado, error? }` — consulta `ReaderCollection.GetReaders()`.
  - `iniciar_identificacion(templates_data)` → lanza thread, retorna `session_id`. 1 captura → comparación 1:N.
  - `iniciar_enrolamiento(rut, nombre, save_callback)` → 4 capturas secuenciales → `Enrollment.CreateEnrollmentFmd()` → `save_callback(rut, bytes)`.

---

#### `app/api/v1/endpoints/` — Endpoints HTTP

El archivo `app/api/v1/api.py` registra todos los routers bajo `/api`:

| Archivo | Prefijo | Endpoints principales | Estado |
|---------|---------|----------------------|--------|
| `auth.py` | `/api/auth` | `POST /login`, `POST /logout` | ✅ Registrado |
| `inventario.py` | `/api/inventario` | CRUD de tipos y tallas | ✅ Registrado |
| `personal.py` | `/api/personal` | `GET /todos?search=...` | ✅ Registrado |
| `endpoints_rfid.py` | `/api/rfid` | Todo lo relacionado con RFID (ver abajo) | ✅ Registrado |
| `stats.py` | `/api/stats` | `GET /inventario` (KPIs del dashboard) | ✅ Registrado |
| `asignaciones.py` | `/api/asignaciones` | `GET /todas` | ✅ Registrado |
| `biometria.py` | `/api/biometria` | Identificación y enrolamiento de huellas | ✅ Registrado |
| `reportes.py` | *(sin prefijo aún)* | Generación de Excel | ❌ No registrado |

**Sub-rutas de RFID (`/api/rfid`):**

```
Log / Persistencia:
  POST /lectura              → Registra lectura (asignación o recepción)
  GET  /buscar/{epc}         → Busca prenda por EPC
  POST /vincular             → Vincula EPC a SKU existente
  GET  /log                  → Últimas N lecturas
  GET  /lecturas             → Inventario completo desde lecturas_rfid (para tablas del frontend)

Hardware del lector (todos aceptan ?role=reception|assignment, default: assignment):
  GET  /reader/status        → Estado de conexión del lector indicado
  POST /reader/connect       → Conectar al lector indicado
  POST /reader/disconnect    → Desconectar el lector indicado
  POST /reader/scan          → Escanear un tag con el lector indicado
  GET  /reader/read/{epc}    → Leer memoria USER del tag
  POST /reader/write         → Escribir SKU en tag y vincularlo en BD

  Respuesta de /reader/scan incluye:
    { encontrado, epc?, sku?, hardware_error, hardware_role? }
    hardware_error=true indica que el lector físico no responde

Modo Inventario (escaneo masivo, siempre usa lector "assignment"):
  POST /inventario/iniciar   → Iniciar sesión de inventario
  POST /inventario/detener   → Detener y obtener resumen
  GET  /inventario/estado    → Estado actual de la sesión
  POST /inventario/scan      → Escanear un tag (crea prenda si es nuevo)

Modo Ajuste:
  PATCH  /inventario/prenda/{sku}      → Cambiar tipo/talla de una prenda
  DELETE /inventario/prenda/{sku}/tag  → Desvincular el chip RFID
```

---

## BASE DE DATOS

### Diagrama de tablas

```
roles ──────────────── usuarios
                           │
                           │ (autenticación por nombre_completo)

modulos ────────────── roles_modulos (permisos por rol)

areas ──┐
         ├── personal (rut PK)
subareas─┘       │
                  │
tallas ───────────┼────────── lecturas_rfid (sku UNIQUE)
                  │                │
tiposPrendas ─────────────────────┘
                                   │
empresa ───────────────────────────┘
                  │
                  └──────── asignaciones
                               (rut FK, sku, tag_epc, fecha_entrega, fecha_devolucion)
```

### Esquema completo de tablas

#### `roles`
| Columna | Tipo | Restricciones |
|---------|------|---------------|
| `rol_id` | INT AUTO_INCREMENT | PRIMARY KEY |
| `nombre_rol` | VARCHAR(50) | NOT NULL, UNIQUE |

#### `usuarios`
| Columna | Tipo | Restricciones |
|---------|------|---------------|
| `user_id` | INT AUTO_INCREMENT | PRIMARY KEY |
| `nombre_completo` | VARCHAR(100) | NOT NULL, UNIQUE — **es el campo de username para login** |
| `correo` | VARCHAR(100) | NOT NULL, UNIQUE |
| `contrasena` | VARCHAR(255) | NOT NULL — hash bcrypt |
| `rol_id` | INT | FK → roles(rol_id) |
| `activo` | BIT | DEFAULT 1 |
| `creado_en` | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| `ultimo_login` | DATETIME | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

#### `modulos` y `roles_modulos`
Tablas para control de acceso por módulo. `modulos` define módulos del sistema. `roles_modulos` asocia qué roles pueden acceder a qué módulos. **Actualmente no utilizadas por el backend.**

#### `personal`
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `rut` | VARCHAR(20) | PRIMARY KEY |
| `nombre_completo` | VARCHAR(100) | NOT NULL |
| `empresa` | VARCHAR(100) | NOT NULL — texto libre, no FK |
| `cargo` | VARCHAR(50) | NOT NULL |
| `area_id` | INT | FK → areas |
| `subarea_id` | INT | FK → subareas |
| `talla_id` | INT | FK → tallas |
| `huella_digital` | LONGBLOB | NULL — encoding facial biométrico |

#### `lecturas_rfid` — Tabla central del inventario
Esta tabla es el corazón del inventario. Cada fila es una **prenda física**:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_lectura` | INT PK | Identificador interno |
| `tag_epc` | VARCHAR(50) | EPC del chip RFID |
| `sku` | VARCHAR(100) UNIQUE | Código único de la prenda (ej: `PANTALON_BLANCO-0042`) |
| `tipo_id` | INT | FK → tiposPrendas |
| `talla_id` | INT | FK → tallas |
| `accion` | VARCHAR(50) | Última acción registrada (ej: `INVENTARIO`, `ASIGNACION`, `RECEPCION`) |
| `resultado` | VARCHAR(50) | Resultado de la acción |
| `estado_disponible` | BIT | 1 = disponible, 0 = asignada |
| `empresa_id` | INT | FK → empresa |
| `hora` | DATETIME | DEFAULT CURRENT_TIMESTAMP |

#### `asignaciones`
Historial completo de entregas y devoluciones:

| Columna | Descripción |
|---------|-------------|
| `asignacion_id` | PK auto-increment |
| `rut` | FK → personal |
| `nombre_completo` | Denormalizado (preserva nombre aunque el empleado cambie) |
| `sku` | Prenda entregada |
| `tag_epc` | EPC del chip al momento de la asignación |
| `fecha_entrega` | Cuándo se entregó |
| `fecha_devolucion` | NULL si aún no fue devuelta |

---

## FRONTEND

### Estructura de directorios

```
Frontend/src/
├── main.jsx              # Punto de entrada, monta <App /> + <Toaster /> (react-hot-toast)
├── App.jsx               # Router principal + AuthProvider
├── context/
│   └── AuthContext.jsx   # Estado global de autenticación
├── services/             # Comunicación con el backend
│   ├── api.js            # Cliente HTTP base (singleton ApiClient)
│   ├── authService.js    # Login, logout, decodificación JWT
│   ├── statsService.js   # KPIs del dashboard
│   ├── catalogosService.js # CRUD tipos y tallas
│   ├── rfidService.js    # Todas las operaciones RFID
│   └── staffService.js   # Listado de personal
├── pages/                # Una página por ruta
│   ├── Login.jsx
│   ├── Dashboard.jsx
│   ├── Inventory.jsx     # 4 pestañas: Prendas, Tipos, Tallas, Realizar Inventario
│   ├── InventoryMode.jsx # LEGACY — conservado sin uso activo (ruta redirige a /inventario)
│   ├── Staff.jsx
│   ├── Returns.jsx
│   ├── Reports.jsx
│   ├── Settings.jsx
│   └── WorkerDashboard.jsx
└── components/           # Componentes reutilizables por dominio
    ├── layout/           # Sidebar, Header, Layout
    ├── dashboard/        # MetricCard, BarChart, DonutChart
    ├── inventory/        # CatalogoTable, CatalogoModal, ConfirmDeleteModal,
    │                     # TabRealizarInventario (escaneo RFID masivo)
    ├── staff/            # EmployeeTable, Pagination
    ├── returns/          # Componentes de devoluciones
    ├── reports/          # FileUploadArea, ReportGenerator
    ├── worker/           # WorkerLayout, ScanningPanel, ScanHistory
    └── fingerprint/      # FingerprintControl
```

---

### Autenticación y rutas protegidas

**`AuthContext.jsx`** mantiene el estado de sesión en memoria y en `localStorage`:

```
Al cargar la app:
  localStorage tiene token? → ¿Es válido (no expirado)? → Restaura sesión
                                                          → Si expiró: limpiar

login(username, contrasena):
  → authService.login() → POST /api/auth/login { username, contrasena }
  → Guarda token + user en localStorage
  → Actualiza estado de React

logout():
  → POST /api/auth/logout
  → Limpia localStorage
  → Limpia estado de React
```

**`ProtectedRoute`** en `App.jsx`:
- Si no está autenticado → redirige a `/login`.
- ⚠️ **La validación de roles está comentada actualmente** — cualquier usuario autenticado puede acceder a cualquier ruta. Solo el redirect al hacer login (`/` para admin, `/worker` para worker) usa el rol.

**Roles disponibles:** `admin` (acceso completo) y `worker` (solo portal de operario).

---

### Cliente HTTP: `src/services/api.js`

`ApiClient` es un singleton (una sola instancia compartida en toda la app):

```javascript
// Todos los servicios lo importan así:
import apiClient from './api';

// Y hacen llamadas como:
apiClient.get('/inventario/tipos')
apiClient.post('/auth/login', { username, contrasena })
```

Lee la URL base de `VITE_API_URL` o usa `http://localhost:8000/api` por defecto.
Agrega automáticamente el header `Authorization: Bearer <token>` si hay sesión activa.
En caso de error, extrae el mensaje del campo `detail` de FastAPI.

---

### Servicios Frontend

| Servicio | Conectado al backend | Qué hace |
|----------|---------------------|----------|
| `authService.js` | ✅ Sí | Login (`username`+`contrasena`)/logout, decodifica JWT para leer rol |
| `statsService.js` | ✅ Sí | Obtiene KPIs del inventario con filtros |
| `catalogosService.js` | ✅ Sí | CRUD de tipos de prenda y tallas |
| `rfidService.js` | ✅ Sí | Todo el flujo RFID; exporta `RFID_ROLES = { RECEPTION, ASSIGNMENT }` |
| `staffService.js` | ⚠️ Parcial | Solo `getEmployees()` funciona (vía `/personal/todos`). Rutas `/staff/departments`, `/staff/employees/*` NO existen (404 harmless) |
| `huellasService.js` | ✅ Sí | Identificación 1:N y enrolamiento 4 capturas vía `/biometria/*` |
| `returnsService.js` | ❌ No implementado | Endpoints `/returns/*` no existen en backend |
| `reportsService.js` | ❌ Parcial | Usa mock data; `reportes.py` no está registrado en el router |
| `alertService.js` | ❌ No implementado | Endpoints `/alerts/*` no existen |

---

### Páginas

**`Login.jsx`**
Formulario de acceso. Credenciales demo: `admin`/`admin123`. Redirige según rol al ingresar.

**`Dashboard.jsx`**
Panel de estadísticas con:
- 3 KPIs: Total de prendas, Disponibles, En Uso.
- Filtros por tipo de prenda y talla.
- 3 gráficos: dona (disponibles vs en uso), barras por tipo, barras por talla.
- Datos obtenidos de `GET /api/stats/inventario`.

**`Inventory.jsx`**
4 pestañas:
- **Prendas**: Tabla del inventario con 4 columnas visibles — **Tipo, Talla, Estado, SKU**. Las columnas "Tag EPC" y "Acción" están comentadas en el código (pendiente de habilitar en fase de asignaciones). La columna Estado muestra un badge gris "Pendiente" como placeholder; la lógica real de Disponible/Asignado está comentada junto al badge, lista para activarse. Anchos de columna explícitos vía `<colgroup>`: Tipo 35%, Talla 15%, Estado 20%, SKU 30%.
- **Tipos de Prenda**: CRUD del catálogo.
- **Tallas**: CRUD del catálogo.
- **Realizar Inventario**: Escaneo masivo RFID integrado como tab (ver `TabRealizarInventario` abajo).

**`components/inventory/TabRealizarInventario.jsx`**
Componente que implementa el modo inventario RFID dentro de la pestaña "Realizar Inventario":
- Recibe props `tipos`, `tallas` (arrays) y `activo` (boolean).
- **Ciclo de vida con cleanup automático:** si `activo` pasa a `false` (cambio de pestaña), llama `detenerModoInventario()` y limpia el `setInterval` para evitar procesos en background.
- Polling cada 500ms a `POST /api/rfid/inventario/scan` mientras la sesión está activa.
- Indicador LED tricolor: verde (conectado), gris clickeable (desconectado), rojo (hardware_error).
- Panel de resumen post-sesión con `cantidad_registrada` y `duplicadas` antes de limpiar el estado.
- Siempre usa el lector `assignment` internamente (igual que `InventoryMode.jsx`).

**`InventoryMode.jsx`** *(LEGACY — no usar directamente)*
Conservado en disco como respaldo. La ruta `/inventario-rfid` redirige a `/inventario`. No tiene entrada en el sidebar.

**`Staff.jsx`**
Lista de personal con búsqueda por nombre o RUT. El backend `GET /personal/todos` retorna un array plano `[{rut, nombre_completo, empresa, cargo, ...}]` — el frontend mapea: `rut→id`, `nombre_completo→name`, `empresa→department`. Tabla simplificada con columnas EMPLEADO | CARGO | ACCIONES. Botón 👆 abre modal de enrolamiento de huella usando `FingerprintControl` en modo `registration` (prop `rut`). Botón `+ Agregar Empleado` presente pero no implementado (stub vacío). No tiene paginación ni filtro por departamento (rutas `/staff/*` no implementadas en backend).

**`Returns.jsx`**
Gestión de devoluciones. **Actualmente no funcional** porque los endpoints del backend no están implementados.

**`Reports.jsx`**
Generador de reportes. **Actualmente usa datos simulados** porque `reportes.py` no está registrado en el router.

**`WorkerDashboard.jsx`**
Vista del operario. Contiene el componente `ScanningPanel` con dos tabs:
- **Recibir prendas** (tab `receive`): usa el lector de Recepción (`?role=reception`). Escanea tags en loop y registra recepciones (`POST /api/rfid/lectura` con `accion: "RECEPCION"`).
- **Asignar prenda** (tab `assign`): primero identifica al trabajador, luego escanea prendas en loop (`POST /api/rfid/lectura` con `accion: "ASIGNACION"`).
  - **Identificación biométrica (método principal)**: botón "Identificar con Huella" → `POST /biometria/identificar` → polling `GET /biometria/estado/{session_id}` hasta completar. El resultado (`resultado.rut`, `resultado.nombre_completo`) se carga directamente.
  - **Fallback manual**: enlace "Modo Manual (RUT)" muestra input para buscar por `GET /personal/todos?search=...`.
  - `workerData` acepta keys en dos formatos: `Rut`/`NombreCompleto` (biometría) y `rut`/`nombre_completo` (búsqueda manual).
- Si un lector falla (`hardware_error=true`), se muestra un banner de error específico sin bloquear el otro modo.
- `RFID_ROLES` en `rfidService.js` define las constantes `{ RECEPTION: 'reception', ASSIGNMENT: 'assignment' }`.

---

## Flujos de datos completos

### Inicio de sesión

```
Usuario escribe credenciales
    → Login.jsx llama useAuth().login(username, contrasena)
    → authService.login() → POST /api/auth/login { username, contrasena }
    → [Backend] AuthRepository busca usuario por nombre_completo (JOIN usuarios+roles)
    → AuthService verifica contraseña con bcrypt
    → Genera JWT con {userId, username, role}
    → [Frontend] guarda token en localStorage
    → Redirige a '/' (admin) o '/worker' (operario)
```

### Inventario en modo RFID masivo

```
Admin abre Inventario → pestaña "Realizar Inventario"
    → TabRealizarInventario verifica estado lector y sesión activa previa
    → Selecciona categoría y talla, presiona "Iniciar inventario"
    → POST /api/rfid/inventario/iniciar {tipo_id, talla_id}
    → Backend valida catálogos y guarda estado en memoria

    [Cada 500ms — polling desde TabRealizarInventario.jsx]
    → POST /api/rfid/inventario/scan
    → Backend: lector serial escanea el chip más cercano
    → Si EPC nuevo en esta sesión:
        → Genera SKU: "PANTALON_BLANCO-0043"
        → INSERT en lecturas_rfid
        → Retorna {sku, tipo_prenda, talla, epc}
    → Frontend: agrega fila en tiempo real a la tabla

Admin presiona "Detener"
    → POST /api/rfid/inventario/detener
    → Backend retorna resumen {cantidad_registrada, duplicadas}
    → Frontend muestra panel de resumen antes de limpiar el estado
    → toast.success('Inventario finalizado')
    → Presionar "Nuevo inventario" limpia el estado y vuelve al panel inicial

Si el admin cambia de pestaña con sesión abierta:
    → useEffect de TabRealizarInventario detecta activo=false
    → Llama detenerModoInventario() + clearInterval automáticamente
```

### Asignar prenda a un trabajador

```
Operario en WorkerDashboard selecciona "Asignar"
    → Busca trabajador por RUT → GET /api/personal/todos?search=RUT
    → Inicia loop de escaneo cada 500ms

    [Cada 500ms]
    → POST /api/rfid/reader/scan?role=assignment   ← lector de Asignación (COM3)
    → Si hardware_error=true: muestra banner de error; detiene el loop
    → POST /api/rfid/lectura {tag_epc, accion: "ASIGNACION", rut}
    → [Backend] RFIDService:
        → Busca prenda por tag_epc en lecturas_rfid
        → Busca empleado por RUT en personal
        → AsignacionesRepository: cierra asignación activa previa del mismo SKU
        → INSERT en asignaciones {rut, nombre_completo, sku, tag_epc, fecha_entrega}
    → Frontend: muestra confirmación
```

---

## Cómo agregar una nueva funcionalidad

### Nuevo endpoint de backend

1. **Schema** en `app/schemas/mi_feature.py` — define qué datos entran y salen.
2. **Repository** en `app/repositories/mi_feature_repository.py` — escribe las consultas SQL con `sqlalchemy.text()`.
3. **Service** en `app/services/mi_feature_service.py` — implementa la lógica de negocio.
4. **Endpoint** en `app/api/v1/endpoints/mi_feature.py` — conecta todo con FastAPI.
5. **Registrar** en `app/api/v1/api.py` ← **fácil de olvidar**:
   ```python
   from app.api.v1.endpoints import mi_feature
   api_router.include_router(mi_feature.router, prefix="/mi-feature", tags=["Mi Feature"])
   ```

### Nueva página de frontend

1. **Servicio** en `src/services/miFeatureService.js` — llama a `apiClient`.
2. **Página** en `src/pages/MiFeature.jsx` — componente React principal.
3. **Registrar ruta** en `src/App.jsx`:
   ```jsx
   <Route path="/mi-feature" element={<ProtectedRoute allowedRoles={['admin']}><MiFeature /></ProtectedRoute>} />
   ```
4. **Agregar al menú** en `src/components/layout/Sidebar.jsx`.

---

## Inconsistencias conocidas / Features incompletos

| Problema | Impacto | Estado |
|----------|---------|--------|
| `reportes.py` no registrado en `api.py` | Los reportes usan datos simulados | Pendiente registrar |
| `returnsService.js` apunta a `/returns/*` que no existe | La página de Devoluciones no funciona | Pendiente implementar |
| `staffService.js` rutas muertas (`/staff/departments`, `/staff/employees/*`) | 404 harmless en consola; solo `getEmployees()` funciona | Pendiente limpiar o implementar CRUD |
| `+ Agregar Empleado` en `Staff.jsx` | Botón presente, `handleAddEmployee` es stub vacío | Pendiente implementar |
| `alertService.js` apunta a `/alerts/*` que no existe | Las alertas no funcionan | Pendiente implementar |
| `inventario.py` llama al repositorio directamente (sin service) | Rompe la separación de capas | Aceptable por ahora |
| Tablas `modulos` y `roles_modulos` en SQL | Definidas en el schema pero sin uso en el backend | Pendiente implementar |
| `InventoryMode.jsx` / ruta `/inventario-rfid` | Archivo legacy conservado; ruta redirige a `/inventario` | Puede eliminarse en limpieza futura |
| Tab Prendas — columnas Tag EPC y Acción | Comentadas en `Inventory.jsx` (no eliminadas). Estado muestra badge "Pendiente" como placeholder | Pendiente habilitar en fase de asignaciones |
| `ProtectedRoute` validación de roles | Lógica de redirección por rol está comentada en `App.jsx` | Pendiente rehabilitar |
| `SQL/seed_datos_prueba.sql` | Usa tabla `inventario` legacy con columnas PascalCase. No compatible con schema actual (`lecturas_rfid`). | Requiere reescritura |

---

## Comandos de desarrollo

```bash
# Backend
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Documentación Swagger: http://localhost:8000/docs

# Seeding inicial (idempotente — seguro de re-ejecutar, actualiza si ya existe)
python seed_admin.py

# Frontend
cd Frontend
npm install
npm run dev
# App: http://localhost:5173

# Credenciales de prueba
# Admin:  admin / admin123   (campo username = nombre_completo en DB)
```

