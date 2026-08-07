# Prevención EPP

Sistema de gestión de **Elementos de Protección Personal** para prevención de riesgos: catálogo de EPP, stock por producto y talla, entregas a trabajadores con motivo trazable, y reportabilidad con exportación a Excel.

El personal no se carga a mano: se sincroniza a diario desde la base de RRHH, que es la fuente de verdad.

- **Backend** — Python 3.13 · FastAPI · SQLAlchemy 2.0 · PostgreSQL
- **Frontend** — React 19 · Vite 7 · React Router 7 · Recharts · TanStack Table
- **Despliegue** — Docker Compose (Postgres + backend + frontend + Nginx + Ofelia para tareas programadas)

UI, comentarios y documentación en español.

> Este repositorio es un fork de un sistema de lavandería industrial del mismo autor, reconvertido por fases. El dominio viejo (RFID, lectores UHF, huella dactilar) fue eliminado. Ver `ARQUITECTURA.md`.

---

## Documentación

| Archivo | Qué contiene |
|---|---|
| `CLAUDE.md` | Guía operativa: comandos, esquema, rutas de la API, invariantes que no se pueden romper, deuda |
| `ARQUITECTURA.md` | Por qué el sistema tiene esta forma: flujos, decisiones de diseño y su costo |
| `docs/runbook-sync-personal.md` | Sincronización de personal desde RRHH |
| `docs/staging-deploy.md` | Despliegue en staging |
| `docs/plans/` | Documentos de diseño por fase (registro histórico) |

---

## Puesta en marcha (desarrollo)

Requisitos: Python 3.13+, Node.js 18+, Docker.

### 1. Base de datos

```bash
docker run -d --name pg-prevencion -e POSTGRES_PASSWORD=<clave> -e POSTGRES_DB=db_prevencion -p 5433:5432 postgres:16-alpine
```

### 2. Backend

```bash
cd Backend
python -m venv venv
venv/Scripts/activate          # Windows · source venv/bin/activate en Linux/Mac
pip install -r requirements.txt
cp .env.example .env           # completar credenciales
uvicorn main:app --reload --port 8000
```

Las tablas se crean solas al arrancar (`Base.metadata.create_all`). Después, los seeds — son idempotentes:

```bash
venv/Scripts/python.exe seed_admin.py       # usuario admin / admin123
venv/Scripts/python.exe seed_modulos.py     # módulos y permisos por rol
```

API en **http://localhost:8000** · Swagger en `/docs`.

### 3. Frontend

```bash
cd Frontend
npm install
npm run dev
```

SPA en **http://localhost:5173**. Entrar por `localhost`, **no** por `127.0.0.1`: la sesión viaja en una cookie `samesite=strict` que no se comparte entre ambos hosts.

---

## Verificación

No hay suite de pytest ni se usa `TestClient` (choque de versión de httpx). El patrón del proyecto es levantar un PostgreSQL efímero en Docker, crear el esquema desde el ORM y ejercitar **Service → Repository** con un script de checks:

```bash
docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine
```

```bash
cd Backend && PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/smoke_reportes.py
```

```bash
docker rm -f pg_smoke
```

`tests/smoke_sync_personal.py` cubre el sync de personal y necesita además el túnel SSH a RRHH. **Ambos scripts hacen `drop_all` sobre la base destino: nunca apuntarlos a una base real.**

En el frontend: `npm run lint` y `npm run build`.

---

## Despliegue

```bash
cp .env.example .env          # completar valores
docker compose up -d --build
docker compose exec backend python seed_admin.py
```

Ofelia corre dos tareas programadas dentro del stack: backup diario de la base a las 03:00 y sincronización de personal desde RRHH a las 04:00.

---

## Módulos de la API

Todo cuelga de `/api`. Cada módulo se protege con `require_module("<nombre>")`; los roles `admin` y `administrador` tienen acceso total.

| Módulo | Prefijo | Contenido |
|---|---|---|
| Auth | `/api/auth` | Login y logout (cookie httpOnly de 8 h) |
| Personal | `/api/personal` | Nómina sincronizada desde RRHH, áreas, sync |
| EPP | `/api/epp` | Categorías, productos, stock, movimientos |
| Entregas | `/api/entregas` | Entrega, sustitución e historial por trabajador |
| Importaciones | `/api/importaciones` | Carga masiva desde planilla |
| Templates | `/api/templates` | Plantillas de importación |
| Inventario | `/api/inventario` | Tallas y empresas |
| Reportes | `/api/reportes` | Trazabilidad, EPP vigentes y stock — cada uno con su ruta `.xlsx` |
| Stats | `/api/stats` | Métricas del dashboard |
| Superadmin | `/api/superadmin` | Usuarios, roles y asignación de módulos |

El detalle de cada ruta está en `CLAUDE.md` y en Swagger.

---

## Estructura

```
app-prevencion/
├── Backend/                 API FastAPI
│   ├── main.py              Entry point: CORS, rate limiting, routers, create_all
│   ├── sync_personal.py     CLI del sync de personal (lo dispara el scheduler)
│   ├── seed_admin.py        Seeds idempotentes
│   ├── seed_modulos.py
│   ├── app/
│   │   ├── api/v1/          Endpoints + router principal (api.py)
│   │   ├── services/        Lógica de negocio
│   │   ├── repositories/    Acceso a datos — SQL crudo con sqlalchemy.text()
│   │   ├── schemas/         Modelos Pydantic
│   │   ├── models/          ORM (todo en inventario.py)
│   │   ├── core/            Config, seguridad, logging
│   │   └── db/              Sesiones: base propia y solo-lectura a RRHH
│   └── tests/               Smoke tests y seed de datos de demo
│
├── Frontend/                SPA React + Vite
│   └── src/
│       ├── pages/           Una por ruta
│       ├── components/      Por dominio + layout y comunes
│       ├── services/        Llamadas a la API (todas vía apiClient)
│       ├── context/         Auth y tema
│       └── styles/          Variables CSS, tema claro y oscuro
│
├── docs/                    Runbooks y documentos de diseño
├── nginx/                   Configuración del reverse proxy
├── airflow/                 DAG de backup
└── compose.yml              Stack de producción
```

La arquitectura del backend es **Endpoint → Service → Repository → PostgreSQL**. Los repositories usan SQL crudo con `sqlalchemy.text()`, no la query API del ORM.

---

## Credenciales por defecto

`admin` / `admin123` — cambiarlas antes de cualquier despliegue real.
