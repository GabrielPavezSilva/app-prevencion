# Runbook — Sincronización de personal desde RRHH (Fase 4)

Cómo probar, correr y desplegar el sync de `personal`. Sirve tanto para volver a
verificar tras un cambio como para la puesta en producción.

---

## 1. Qué hace

```
rh_cramer (schema rh, SOLO LECTURA)  →  normalizar  →  catálogos  →  upsert  →  bajas
```

RRHH es la fuente de verdad: pisa todos los campos y no hay edición manual desde
la aplicación. Quien sale de la nómina se marca `activo = false` — **nunca se
borra**, porque `entregas_epp` referencia `personal.rut` y el historial de EPP es
el activo del sistema.

| Pieza | Archivo |
|---|---|
| Conexión (engine aparte, read-only, lazy) | `Backend/app/db/session_employees.py` |
| Lectura de la nómina | `Backend/app/repositories/employees_repository.py` |
| Escritura (upsert + catálogos + bajas) | `Backend/app/repositories/personal_sync_repository.py` |
| Orquestación | `Backend/app/services/personal_sync_service.py` |
| Endpoints | `Backend/app/api/v1/endpoints/personal.py` |
| Entrada CLI (la que usa el scheduler) | `Backend/sync_personal.py` |
| Migración de esquema | `Backend/migrations/fase4_jerarquia_areas_y_sync.sql` |
| Smoke test | `Backend/tests/smoke_sync_personal.py` |

**Frecuencia:** diaria a las 04:00 vía Ofelia (label en `compose.yml`).
Además hay botón *Sincronizar ahora* en la página Personal para el alta del día.

---

## 2. Requisitos para correrlo en local

### 2.1 Túnel SSH a la base de RRHH

```bash
ssh -N -L 5434:localhost:5432 gpavezvps@192.9.200.12
```

> **Puerto local 5434, no 5433.** En 5433 vive el `db_prevencion` de desarrollo:
> si el túnel toma ese puerto, el backend se conecta a RRHH creyendo que es su
> propia base.

En producción **no hace falta túnel**: la aplicación corre en el mismo servidor
que la base de RRHH.

### 2.2 Variables en `Backend/.env`

```bash
EMPLOYEES_DB_USER=<usuario postgres de RRHH>
EMPLOYEES_DB_PASSWORD=<contraseña, sin escapar>
EMPLOYEES_DB_HOST=localhost
EMPLOYEES_DB_PORT=5434
EMPLOYEES_DB_NAME=rh_cramer
```

Se prefieren los campos sueltos sobre `EMPLOYEES_DATABASE_URL` porque una
contraseña con `@`, `#`, `%`, `:` o `/` rompe el parseo de la URL.

---

## 3. Correr el sync

### Dry run — calcula todo y revierte, no escribe nada

```bash
cd Backend && venv/Scripts/python.exe sync_personal.py --dry-run
```

Es el primer paso obligatorio contra cualquier base nueva: muestra cuántos se
crearían, actualizarían y **desactivarían** antes de tocar nada.

### Corrida real

```bash
cd Backend && venv/Scripts/python.exe sync_personal.py
```

Salida esperada (nómina de ~590 personas):

```
Sync OK — leídos: 591, creados: 0, actualizados: 3, sin cambios: 588, desactivados: 1, errores: 0
```

Sale con código 1 si falla, para que el scheduler lo marque en rojo.

### Desde la API

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/personal/sync
curl -X POST -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/personal/sync?dry_run=true"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/personal/sync/estado
```

Requiere rol `admin`/`administrador` o el módulo `personal`.

---

## 4. Smoke test (tras cualquier cambio en el sync)

Ejercita Service → Repository sobre una base desechable, leyendo la nómina real.

```bash
# 1. Base desechable
docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine

# 2. Con el túnel arriba, desde Backend/
PYTHONPATH=. PYTHONIOENCODING=utf-8 venv/Scripts/python.exe tests/smoke_sync_personal.py

# 3. Limpiar
docker rm -f pg_smoke
```

> `PYTHONIOENCODING=utf-8` evita que la consola cp1252 de Windows corte la salida
> en el primer carácter acentuado.

Cubre: normalización de RUT, dry-run sin escritura, carga inicial, catálogos sin
fusionar, idempotencia, desvinculación conservando historial, reingreso, RRHH
pisando ediciones locales, guardarraíl de nómina vacía y las lecturas que
consume la página Personal.

**Nunca apuntar `SMOKE_DATABASE_URL` a una base real**: el script hace `drop_all`.

---

## 5. Verificación por API (extremo a extremo)

Con el backend arriba y datos sincronizados:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","contrasena":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/personal/sync/estado
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/personal/todos"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/personal/todos?search=12.261.540"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/personal/todos?incluir_inactivos=true"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/entregas/trabajador/<rut>"
```

Qué mirar:

- `sync/estado` devuelve la fecha de la última corrida (alimenta el encabezado
  de la página Personal).
- `/todos` trae `nombre_area`, `nombre_subarea` y `epp_vigentes` por fila.
- La búsqueda por RUT funciona **con** puntos y guión.
- `entregas/trabajador/{rut}` responde también para desvinculados — son
  justamente los que pueden tener EPP sin devolver. Crear una entrega nueva a un
  desvinculado sí está bloqueado.

> `uvicorn` sin `--reload` **no** recarga el código: tras editar hay que
> reiniciarlo o los cambios no se ven.

### Consultas útiles sobre la base

```sql
SELECT COUNT(*) FILTER (WHERE activo) AS activos, COUNT(*) AS total FROM personal;
SELECT MAX(sync_at) FROM personal;

-- Historial de corridas
SELECT fecha, filas_ok, filas_error, detalle_errores
FROM importaciones WHERE template_id = 'personal_sync' ORDER BY fecha DESC LIMIT 10;

-- Distribución por empresa
SELECT e.nombre_empresa, COUNT(*) FROM personal p
JOIN empresa e ON e.empresa_id = p.empresa_id WHERE p.activo GROUP BY 1 ORDER BY 2 DESC;

-- Desvinculados que todavía tienen EPP sin devolver
SELECT p.rut, p.nombre_completo, COUNT(*) AS epp
FROM personal p JOIN entregas_epp en ON en.rut = p.rut
WHERE NOT p.activo
  AND NOT EXISTS (SELECT 1 FROM entregas_epp r WHERE r.entrega_reemplazada_id = en.entrega_id)
GROUP BY 1, 2;
```

---

## 6. Puesta en producción

1. **Migrar el esquema** (obligatorio en bases creadas antes de la Fase 4;
   `create_all` no altera tablas existentes):

   ```bash
   docker exec -i <contenedor_postgres> psql -U <usuario> -d db_prevencion \
     < Backend/migrations/fase4_jerarquia_areas_y_sync.sql
   ```

   Es idempotente. Verificar después:

   ```sql
   \d areas      -- debe tener empresa_id, origen_id y uq_areas_nombre_empresa
   \d subareas   -- area_id, origen_id UNIQUE
   \d personal   -- cargo VARCHAR(100)
   ```

2. **Variables de entorno** en el `.env` del servidor:

   ```bash
   EMPLOYEES_DB_USER=<usuario>
   EMPLOYEES_DB_PASSWORD=<contraseña>
   ```

   El resto (`HOST`, `PORT`, `NAME`) tiene valores por defecto en `compose.yml`,
   apuntando al host de Docker en el puerto 5432.

3. **Levantar y probar la conectividad con un dry-run**, antes de la primera
   corrida real:

   ```bash
   docker compose up -d --build backend
   docker compose exec backend python sync_personal.py --dry-run
   ```

4. **Primera corrida real** y verificación:

   ```bash
   docker compose exec backend python sync_personal.py
   ```

5. **Confirmar el job diario**: Ofelia lee los labels del servicio `backend` al
   levantar. `docker compose logs ofelia` debe mostrar el job `sync-personal`
   registrado.

---

## 7. Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| `503` / `Falta la configuración de la base de RRHH` | Sin `EMPLOYEES_DB_USER`/`PASSWORD` | Completar el `.env` y reiniciar |
| `502` / `No se pudo conectar a la base de RRHH` | Túnel caído o credenciales malas | Reabrir el túnel en 5434; probar la conexión aparte |
| `409` / `La nómina llegó vacía` | La fuente devolvió 0 filas | **No forzar.** Es el guardarraíl que evita desactivar a todo el personal; revisar el ETL de RRHH |
| `password authentication failed` | Contraseña con caracteres especiales en la URL | Usar los campos `EMPLOYEES_DB_*` sueltos |
| Se desactiva gente que sí trabaja | Cambió el filtro `status='activo'` o el RUT cambió de formato | Correr `--dry-run` y revisar `ruts_desactivados` antes de escribir |
| Aparecen áreas duplicadas | Se corrió el sync sin aplicar la migración | Aplicar `fase4_jerarquia_areas_y_sync.sql` y limpiar duplicados |

---

## 8. Volver a cero en desarrollo

```sql
TRUNCATE personal, areas, subareas, empresa CASCADE;
```

Borra también entregas y stock por el `CASCADE`. Solo en desarrollo.

---

## 9. Notas sobre la fuente

Detalle del esquema de `rh_cramer`, los hallazgos que motivaron el diseño
(colisión de nombres de área, DV en minúscula, `updated_at` inservible para
incremental) y la query original están en
`docs/plans/2026-07-21-clon-prevencion-epp-design.md` y en el propio código de
`employees_repository.py`.

Puntos que conviene recordar:

- El ETL de RRHH **reescribe la tabla entera** en cada corrida, así que
  `updated_at` no sirve para sync incremental. El sync es full (~590 filas).
- La empresa `PRUEBA` está excluida a propósito (`EMPRESAS_EXCLUIDAS` en
  `employees_repository.py`).
- `buk_id` guarda `person_id`, no `id`: el id de contrato cambia si alguien
  reingresa, el de persona no.
