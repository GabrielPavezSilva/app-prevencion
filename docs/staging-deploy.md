# Deploy STAGING (rediseño) en paralelo a producción

Stack `lavanderia-staging` — aislado de prod (red, volúmenes y containers propios).
Prod (`compose.yml`, puerto interno 8082) **no se toca**. Staging escucha solo en
`127.0.0.1:8083` y se accede por SSH tunnel (sin DNS ni TLS ni exposición pública).

Backend e imagen son los mismos que prod (el rediseño es solo frontend); la DB de
staging es una copia restaurada del último backup de prod.

## Requisitos
- Correr todos los comandos **en el VPS**, dentro del dir de prod (donde vive `.env`):
  `/opt/etl-bd/proyectos-rrhh/lavanderia/app-lavanderia`
- El `.env` de prod se reusa (mismas credenciales que el dump). No se crea otro.

## 1. Traer la rama con el rediseño
```bash
cd /opt/etl-bd/proyectos-rrhh/lavanderia/app-lavanderia
git fetch origin
git checkout develop && git pull --ff-only origin develop
```

## 2. Levantar solo la DB de staging (vacía)
```bash
docker compose -f compose.staging.yml up -d postgres-staging
# esperar healthy
docker compose -f compose.staging.yml ps
```

## 3. Restaurar el último dump de prod en la DB de staging
Los backups nocturnos de ofelia viven en el volumen de backups de PROD. Confirmá el nombre:
```bash
docker volume ls | grep backups        # p.ej. app-lavanderia_postgres_backups
```
Restaurar el más reciente (ajustá el nombre del volumen si difiere):
```bash
BACKUPS_VOL=app-lavanderia_postgres_backups
docker run --rm -v "$BACKUPS_VOL":/b alpine sh -c 'gunzip -c $(ls -t /b/*.sql.gz | head -1)' \
  | docker compose -f compose.staging.yml exec -T postgres-staging psql -U civot -d civot
```
> Si no hay dump aún, forzá uno en prod:
> `docker compose exec postgres bash -c 'pg_dump -U civot civot | gzip > /backups/manual_$(date +%Y%m%d_%H%M%S).sql.gz'`

## 4. Levantar el resto (backend + frontend rediseñado + nginx)
```bash
docker compose -f compose.staging.yml up -d --build
docker compose -f compose.staging.yml ps
```
`--build` compila el frontend desde la rama pulled con `VITE_API_URL=/api` (relativo).

## 5. Acceder por SSH tunnel (desde tu máquina)
```bash
ssh -L 8083:127.0.0.1:8083 <usuario>@<vps>
# luego abrir en el navegador:
#   http://localhost:8083         → app rediseñada
#   http://localhost:8083/docs    → Swagger del backend staging
```
Login: mismas credenciales que prod (la DB es copia). Cualquier cambio queda en la
DB de staging; **prod no se ve afectado**.

## Actualizar staging tras nuevos commits en develop
```bash
git pull --ff-only origin develop
docker compose -f compose.staging.yml up -d --build frontend-staging nginx-staging
```

## Bajar / limpiar staging
```bash
docker compose -f compose.staging.yml down            # conserva la DB de staging
docker compose -f compose.staging.yml down -v         # borra también la DB de staging
```

## Al aprobar el rediseño
Merge `develop → main` dispara el deploy normal (`.github/workflows/deploy.yml`) y
actualiza prod. Después bajá el stack de staging con `down -v`.
