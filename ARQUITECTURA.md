# Guía de Arquitectura — Prevención EPP

Esta guía está pensada para alguien que llega al proyecto por primera vez y necesita entender qué hace cada parte, cómo se comunican y **por qué** están organizadas así.

Para el detalle operativo (comandos, convenciones al escribir código, landmines) mirá `CLAUDE.md`. Este documento explica el sistema; ese otro explica cómo trabajar en él.

---

## ¿Qué es este sistema?

Una aplicación web para gestionar los **Elementos de Protección Personal (EPP)** de una empresa: cascos, calzado de seguridad, guantes, protección auditiva, y demás.

El problema que resuelve tiene tres partes:

1. **Saber qué hay en bodega.** Stock por producto y talla, con alertas cuando algo baja del mínimo.
2. **Saber quién tiene qué.** Cada entrega queda registrada contra un trabajador, con su motivo.
3. **Poder demostrarlo.** Prevención de riesgos necesita reportar qué EPP tiene cada persona y desde cuándo. Antes de este sistema, las pérdidas de EPP se manejaban por correo electrónico; esa trazabilidad era el requisito número uno del negocio.

El sistema **no** maneja unidades individuales identificadas: no hay un número de serie por casco. Maneja **cantidades** por producto y talla. Esa decisión define todo el modelo de datos.

---

## De dónde viene (contexto importante)

Este repositorio es un **fork de un sistema de lavandería industrial** del mismo autor, reconvertido por fases.

La lavandería gestionaba prendas individuales con **chips RFID**, leídas por lectores UHF conectados por puerto serial, con identificación de operarios por **huella dactilar** (DigitalPersona U.are.U 4500) y un portal separado para trabajadores.

**Todo eso fue eliminado**, y el código muerto que había quedado en pie (endpoints de asignaciones y devoluciones, la página de Returns, el Sidebar) ya se barrió. No hay hardware, ni RFID, ni biometría, ni portal de operarios. Si igual te cruzás con `lecturas_rfid`, `asignaciones`, `tiposPrendas`, `secciones` o `temporadas`, es un resto: `CLAUDE.md` lista lo poco que sigue pendiente.

Vale la pena tenerlo presente porque explica varias rarezas que de otro modo parecen decisiones arbitrarias:

- El archivo de sesión de base de datos se llama `session_mysql.py` y la dependencia `get_mysql_db()`, pero la base es PostgreSQL. Es herencia del fork; renombrarlo tocaría cada endpoint.
- Todos los modelos ORM viven en `app/models/inventario.py`, un nombre que ya no describe su contenido.
- La navegación vive en `TopNav.jsx`; los planes viejos en `docs/plans/` hablan de un `Sidebar.jsx` que ya no existe.

---

## Estructura del repositorio

```
app-prevencion/
├── Backend/          Servidor Python / FastAPI
│   ├── app/          Código de la aplicación (ver abajo)
│   ├── tests/        Smoke tests y seeds de demostración
│   ├── main.py       Punto de entrada
│   ├── seed_admin.py / seed_modulos.py
│   └── sync_personal.py   CLI del sync con RRHH
├── Frontend/         Aplicación web React / Vite
├── docs/             Runbooks y planes de diseño por fase
├── SQL/              Scripts del dominio viejo — OBSOLETOS
├── airflow/          DAGs
├── nginx/            Configuración del reverse proxy
├── compose.yml       Despliegue en el VPS
├── CLAUDE.md         Guía de trabajo para agentes
└── ARQUITECTURA.md   Este archivo
```

---

## Cómo se comunican las partes

```
┌──────────────────────────────────────────────────────┐
│                Navegador del usuario                 │
│  React SPA (Vite, puerto 5173 en desarrollo)         │
│  └── fetch con credentials: 'include'                │
└───────────────────────┬──────────────────────────────┘
                        │  HTTP REST (JSON)
                        │  cookie httpOnly `authToken`
                        ▼
┌──────────────────────────────────────────────────────┐
│            FastAPI Backend (puerto 8000)             │
│  /api/auth  /api/epp  /api/entregas  /api/personal   │
│  /api/reportes  /api/stats  /api/importaciones  ...  │
└───────────────────────┬──────────────────────────────┘
                        │  SQL (SQLAlchemy, text() crudo)
          ┌─────────────┴─────────────┐
          ▼                           ▼
┌───────────────────┐      ┌────────────────────────────┐
│   PostgreSQL      │      │  Base RRHH `rh_cramer`     │
│   db_prevencion   │      │  (solo lectura)            │
│                   │      │  fuente de verdad de la    │
│  productos_epp    │      │  nómina; se sincroniza a   │
│  stock_epp        │◄─────┤  `personal` una vez al día │
│  movimientos_stock│ sync └────────────────────────────┘
│  entregas_epp     │
│  personal  ...    │
└───────────────────┘
```

El frontend nunca habla con la base de datos. Todo pasa por el backend. **No hay hardware en el circuito.**

---

## Backend

### Punto de entrada: `Backend/main.py`

Al arrancar:

1. Importa `app.models.inventario` para que SQLAlchemy registre los modelos.
2. Crea las tablas que falten (`Base.metadata.create_all`). Es idempotente, pero **no es un sistema de migraciones**: si cambiás una columna de una tabla que ya existe, el cambio no se aplica solo.
3. Configura CORS (localhost para desarrollo, más lo que venga en `CORS_ORIGINS`).
4. Monta rate limiting con slowapi.
5. Monta el router principal bajo `/api`.
6. En producción (`ENVIRONMENT=production`) apaga `/docs`, `/redoc` y `/openapi.json`.

### Las tres capas

```
Petición HTTP
     │
     ▼
┌─────────────┐
│  Endpoint   │  app/api/v1/endpoints/   Recibe, valida con Pydantic, delega.
└──────┬──────┘                          No sabe SQL.
       ▼
┌─────────────┐
│   Service   │  app/services/           Reglas de negocio, validaciones,
└──────┬──────┘                          orquestación. Traduce errores de
       │                                 negocio a HTTPException.
       ▼
┌─────────────┐
│ Repository  │  app/repositories/       Acceso a datos. SQL crudo con
└──────┬──────┘                          sqlalchemy.text(). No sabe de reglas.
       ▼
   PostgreSQL
```

**¿Por qué SQL crudo y no el ORM?** Los modelos existen para crear el esquema y documentarlo, pero las consultas reales son agregaciones con varios JOIN y CTEs que en la query API del ORM quedan ilegibles. La regla es consistente: **los repositorios usan `text()`**.

**¿Por qué la separación?** Porque las reglas del dominio EPP son transaccionales y no triviales (ver "Invariantes"). Tenerlas en un solo lugar, sin mezclar con SQL ni con serialización HTTP, es lo que permite testearlas sin levantar el servidor.

### Módulos

| Carpeta | Contenido |
|---|---|
| `app/core/` | `config.py` (settings vía pydantic-settings), `security.py` (JWT, permisos), `logging_config.py` |
| `app/db/` | `session.py` (Base declarativa), `session_mysql.py` (engine principal), `session_employees.py` (conexión de solo lectura a RRHH), `deps.py` (`get_mysql_db`) |
| `app/models/` | `inventario.py` — todos los modelos ORM |
| `app/schemas/` | Modelos Pydantic de request/response |
| `app/repositories/` | Acceso a datos |
| `app/services/` | Lógica de negocio; además `excel_builder.py`, que es infraestructura pura |
| `app/api/v1/` | `api.py` arma el router; `endpoints/` los define |

---

## El modelo de datos

Es el corazón del sistema. Vale la pena entenderlo antes de tocar nada.

### Catálogo y existencias

```
categorias_epp ──< productos_epp ──< stock_epp >── tallas
                          │              │
                          └──────────────┴──< movimientos_stock
```

- **`productos_epp`** es el *catálogo*: una fila por tipo de EPP ("Casco de seguridad"), no por unidad física. `talla_aplica` define si ese producto se maneja por talla.
- **`stock_epp`** son las *existencias*: una fila por combinación producto + talla. Para productos sin talla, `talla_id` es `NULL`.
- **`movimientos_stock`** es el *libro mayor*: cada cambio de existencias deja un asiento con su tipo y su referencia.

El stock es **global**: un solo bodegón, sin segregar por empresa, aunque el sistema es multiempresa. La empresa solo importa a la hora de reportar quién recibió qué.

### Entregas

```
personal ──< entregas_epp >── productos_epp
                 │
                 └── entrega_reemplazada_id ──┐
                      (auto-referencia)  ◄────┘
```

`entregas_epp` denormaliza `nombre_completo` y `empresa_id` al momento de la entrega. No es redundancia por descuido: si un trabajador cambia de empresa o se corrige su nombre, el historial debe seguir diciendo lo que decía cuando se firmó.

La auto-referencia `entrega_reemplazada_id` es lo que permite encadenar reposiciones y sustituciones sin una tabla aparte.

### Organización

```
empresa ──< areas ──< subareas ──< personal
```

Espejo de la jerarquía de RRHH, vinculado por `origen_id`. Dos sutilezas que costaron encontrar:

- El nombre de área **no** es único a nivel global: hay "Administración" y "Operaciones" en varias empresas. Por eso el UNIQUE es `(nombre_area, empresa_id)`. Con un UNIQUE solo sobre el nombre, las áreas de empresas distintas se fusionaban y los reportes por área sumaban empresas.
- La identidad estable de una subárea es `origen_id`, no su nombre: el mismo nombre se repite incluso dentro de una empresa bajo áreas distintas.

---

## Invariantes

Son las reglas que el sistema mantiene siempre. Romperlas corrompe datos de forma silenciosa.

### El stock es un libro mayor

`stock_epp.cantidad_actual` **nunca** se edita directo. Cada cambio pasa por un `MovimientoStock` en la misma transacción, de modo que las existencias siempre se pueden reconstruir desde el historial.

```
cantidad_actual = SUM(movimientos_stock.cantidad
                      WHERE tipo IN ('INGRESO_IMPORT','ENTREGA','AJUSTE'))
```

`BAJA_DANO` queda fuera de esa suma **a propósito**: documenta la baja de una unidad que ya estaba en terreno. Su stock se descontó cuando se entregó; volver a descontarlo sería contarlo dos veces.

### Los productos sin talla son un caso especial

En PostgreSQL `NULL = NULL` evalúa a `NULL`, no a verdadero. Por eso `UNIQUE(producto_id, talla_id)` **no** impide filas duplicadas cuando `talla_id` es `NULL`, que es justo el caso de todo producto sin talla.

Todo lookup, upsert o join por (producto, talla) usa `talla_id IS NOT DISTINCT FROM :talla_id`, que sí trata `NULL` como igual a `NULL`. Es la clase de error que no falla: simplemente duplica filas de stock hasta que alguien nota que los números no cierran.

### Las fechas se guardan en UTC y se reportan en hora de Chile

`fecha_entrega` es `TIMESTAMP WITHOUT TIME ZONE` con `server_default=now()`. En PostgreSQL, guardar un `timestamptz` en una columna sin zona lo convierte **según la zona horaria de la sesión** — así que el mismo instante se almacena distinto según cómo esté configurado el servidor.

Eso es un problema real acá: el contenedor de desarrollo corre en UTC y el `compose.yml` de producción arranca Postgres con `timezone=America/Santiago`. La misma entrega quedaría guardada con 4 horas de diferencia en cada entorno.

La solución tiene dos mitades:

1. **La conexión fija su zona en UTC** (`connect_args` en `session_mysql.py`). El almacenamiento es UTC en todos los entornos, sin importar cómo esté configurado el servidor.
2. **La conversión a hora local ocurre en un solo lugar**, la constante `FECHA_LOCAL` de `reportes_repository.py`:

```sql
((e.fecha_entrega AT TIME ZONE 'UTC') AT TIME ZONE 'America/Santiago')
```

Sin esto, una entrega registrada el 31 a las 21:00 hora chilena cae en el mes siguiente y todo corte mensual queda mal. `tests/smoke_reportes.py` cubre ese borde y verifica que una entrega recién creada se reporte en la hora local correcta.

### "EPP vigente" tiene una definición y una sola

Un EPP está vigente si su entrega no fue reemplazada por otra posterior:

```sql
NOT EXISTS (SELECT 1 FROM entregas_epp r WHERE r.entrega_reemplazada_id = e.entrega_id)
```

Está escrito igual en tres repositorios (`entregas`, `personal`, `reportes`). Si el criterio cambia, hay que cambiarlo en los tres o las pantallas empiezan a contradecirse.

---

## Los flujos

### Entrega de EPP

La página Entregas resuelve todo en una pantalla:

1. Se busca al trabajador por nombre o RUT.
2. Se arma un **carrito** de líneas: producto, talla si aplica, cantidad y **motivo por línea**.
3. Al confirmar, el backend ejecuta **una sola transacción**: N filas en `entregas_epp`, N movimientos `ENTREGA` y el descuento de stock. Si alguna línea no tiene existencias suficientes, **se revierte el carrito completo** — no queda media entrega registrada.

Los tres motivos:

| Motivo | Qué significa | Stock | Vínculo |
|---|---|---|---|
| `NUEVA` | Primera entrega | Descuenta | — |
| `PERDIDA` | Reposición de algo extraviado | Descuenta | Opcional: la entrega que se perdió |
| `DANO` | Sustitución de algo roto | Descuenta | Obligatorio: la entrega que se reemplaza |

`DANO` solo se registra por `POST /entregas/sustitucion`, que además genera el movimiento `BAJA_DANO`. `POST /entregas` rechaza ese motivo: una sustitución sin saber qué sustituye no es trazable.

`PERDIDA` acepta el vínculo pero no lo exige, y no genera `BAJA_DANO` — el ítem perdido no vuelve a bodega. **Conviene informarlo igual**: sin el vínculo, el EPP perdido sigue contando como vigente al lado de su reposición, y el reporte general muestra dos cascos donde hay uno.

No existe devolución de EPP sin reemplazo. Un trabajador desvinculado no puede recibir EPP nuevo, pero su historial se conserva y se puede consultar.

### Importación masiva

Para la carga inicial y la migración desde el software anterior. Cada plantilla (`productos_epp`, `stock_inicial`, `ingreso_stock`, `entregas_historicas`) declara sus columnas en `app/schemas/templates.py`.

El importador procesa **cada fila en su propio savepoint**: una fila mala no aborta el lote, se acumula en el reporte de errores y el resto entra. Cada corrida deja una fila en `importaciones` con el conteo y el detalle.

`entregas_historicas` inserta con la fecha original y **no toca el stock actual**: son entregas que ya ocurrieron, su stock ya se consumió en el sistema anterior.

### Sincronización de personal

RRHH (`rh_cramer`) es la **fuente de verdad** de la nómina. El sync pisa todos los campos y **desactiva** (nunca borra) a quien sale de la nómina, para no perder su historial de entregas. La página Personal es de solo lectura por eso mismo: editarla ahí sería mentirle al próximo sync.

Corre a diario de forma automática y también a demanda desde la UI. Detalle completo en `docs/runbook-sync-personal.md`.

### Reportabilidad

Tres reportes, cada uno con una pregunta de negocio detrás:

| Reporte | Pregunta |
|---|---|
| **Trazabilidad de entregas** | ¿Qué se entregó, a quién, cuándo y por qué? Filtrable por motivo, área, fecha, producto y trabajador |
| **EPP vigentes por trabajador** | ¿Qué tiene cada persona hoy? Incluye a quienes **no** tienen nada, que suele ser la mitad más útil |
| **Stock y quiebres** | ¿Qué hay que comprar? Con consumo del período y cobertura estimada en días |

El principio de diseño: **una query por reporte, dos presentaciones**. Cada reporte tiene un único método de repository que devuelve filas; la ruta JSON alimenta la tabla en pantalla y la ruta `.xlsx` pasa **esas mismas filas** por el generador de Excel. La tabla y el archivo exportado no pueden divergir, que es la falla clásica de este tipo de módulo.

El dashboard agrega sobre las mismas tablas, sin tablas de agregación intermedias.

---

## Frontend

React 19 con Vite. Sin gestor de estado global más allá de dos contextos (`AuthContext`, `ThemeContext`).

```
src/
├── pages/          Una por ruta
├── components/     Por dominio: common, dashboard, entregas, inventory, layout, staff
├── services/       Un archivo por dominio; todos usan apiClient
├── context/        AuthContext, ThemeContext
├── hooks/          useThemeColors, useOnlineStatus
├── db/ sync/ api/  Capa offline (Dexie) — ver "Deuda"
└── styles/         index.css con las variables de tema
```

**`apiClient`** (`services/api.js`) es un singleton sobre `fetch`. Manda `credentials: 'include'` en cada llamada para que viaje la cookie de sesión, y sabe devolver `blob` para las descargas de Excel.

**Navegación**: `components/layout/TopNav.jsx`. Cada entrada declara el `modulo` que requiere y se oculta si el usuario no lo tiene. Agregar una página implica tocar `App.jsx` **y** `TopNav.jsx`.

**Tablas**: `components/common/DataTable.jsx`, sobre TanStack Table, con orden y filtros por columna.

**Gráficos**: Recharts. Los componentes de `components/dashboard/` toman sus colores de `useThemeColors`, que lee las variables CSS en tiempo de ejecución — así los gráficos siguen el tema claro/oscuro sin duplicar la paleta en JavaScript.

**Temas**: todo el color sale de variables CSS definidas para claro y oscuro en `styles/index.css`. Los estilos compartidos entre páginas viven ahí y no en el CSS de una página, porque si no dependen de que ese archivo se haya cargado.

### Las páginas

| Ruta | Qué hace |
|---|---|
| `/` | Dashboard: KPI del período, tendencia de 12 meses por motivo, reparto por área y producto, cobertura de personal, alertas de stock |
| `/inventario` | Productos, stock, categorías y tallas |
| `/entregas` | Registrar (carrito) e historial |
| `/importaciones` | Carga masiva por plantilla |
| `/personal` | Nómina sincronizada, solo lectura, con modal de EPP por trabajador |
| `/reportes` | Los tres reportes, con filtros y exportación a Excel |
| `/configuracion` | Preferencias |
| `/superadmin` | Usuarios, roles y asignación de módulos |

---

## Autenticación y permisos

El login recibe `{ username, contrasena }` y responde con una **cookie httpOnly** llamada `authToken`. El token también viaja en el cuerpo, y `security.py` acepta el header `Authorization` como respaldo para Swagger, pero el navegador usa la cookie: no hay JWT en `localStorage`.

El JWT lleva `{ userId, username, role, modulos, exp, jti }` y dura 8 horas. El logout agrega el `jti` a `token_blacklist`, así que un token robado deja de servir aunque no haya expirado.

Los permisos son **por módulo**, no por rol. Un rol es un conjunto de módulos (`dashboard`, `inventario`, `entregas`, `personal`, `reportes`, `configuracion`, `superadmin`), configurable desde SuperAdmin sin tocar código. En el backend se aplica con `require_module("nombre")`; en el frontend, `ProtectedRoute` valida lo mismo y TopNav oculta lo que no corresponde.

Los roles `admin` y `administrador` tienen acceso total por código.

**El frontend nunca es la barrera de seguridad**: ocultar un botón es cosmético. La verificación que cuenta es `require_module` en el endpoint.

---

## Infraestructura

`compose.yml` levanta cinco servicios en el VPS:

| Servicio | Rol |
|---|---|
| `postgres` | Base de datos, con volumen persistente y backups |
| `backend` | La API FastAPI |
| `frontend` | El build estático de Vite |
| `ofelia` | Scheduler de tareas: backup diario de la base a las 03:00, con retención de 30 días |
| `nginx` | Reverse proxy y terminación TLS |

El backend se conecta a la base de RRHH directamente porque corre en el mismo servidor; en desarrollo eso requiere un túnel SSH.

Guía de despliegue: `docs/staging-deploy.md`.

---

## Decisiones de diseño y sus porqués

**Stock por cantidades, no por unidad identificada.** La lavandería rastreaba cada prenda por su chip. Para EPP no tiene sentido: nadie va a serializar cada par de guantes. El costo de esa decisión es que no se puede responder "¿dónde está exactamente este casco?", solo "cuántos hay y quién recibió".

**Stock global aunque el sistema sea multiempresa.** Hay un solo bodegón físico. Segregar el stock por empresa habría agregado una dimensión sin correlato en la realidad. La empresa se denormaliza en la entrega, que es donde sí importa para reportar.

**Toda devolución es una sustitución.** No existe "devolver un EPP" a secas. Refleja cómo funciona en la práctica: un EPP dañado se cambia por otro, no se devuelve a bodega para reutilizarlo.

**El libro mayor de movimientos.** Se podría haber guardado solo `cantidad_actual`. Tener el historial permite auditar, reconstruir y calcular consumo — que es lo que convierte el reporte de stock en algo accionable para comprar.

**Un solo archivo de modelos.** Herencia del proyecto original. Con ~15 tablas sigue siendo manejable y evita el baile de imports circulares.

**Sin sistema de migraciones.** `create_all` alcanza mientras el esquema esté en construcción. Cuando el sistema esté en producción con datos reales, esto va a doler: cualquier cambio de columna hay que aplicarlo a mano.

---

## Deuda conocida

`CLAUDE.md` tiene la lista completa y accionable. Lo que conviene saber al leer el código:

- **Sobrevive código muerto del dominio de lavandería** en ambos lados. Está inventariado; no lo tomes como referencia.
- **La capa offline está montada pero inerte.** Dexie, el `syncManager` y el `OfflineBanner` se inicializan en `main.jsx`, pero nada encola operaciones: la cola nunca se llena. Se conservó porque estaba previsto para entregas en terreno sin red.
- **Los reportes usan el área *actual* del trabajador**, no la que tenía cuando recibió el EPP. Si el negocio necesita la histórica hay que denormalizar `area_id` en `entregas_epp`, y conviene decidirlo pronto: cada día que pasa acumula historial que después no se puede reconstruir.
- **No hay stock valorizado** porque no hay precio en el catálogo de productos.
- Las imágenes Docker del compose todavía apuntan a los nombres de la lavandería.
