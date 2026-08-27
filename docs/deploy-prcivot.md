# Despliegue en `prcivot.cramer.cl`

> Primera vez en un servidor limpio: `docs/bootstrap-produccion.md` tiene el
> paso a paso para crear y sembrar la base, y dejar el entorno local trabajando
> contra ella por túnel SSH. Este documento es la referencia del despliegue ya
> montado.

Dos stacks, un solo `.env`:

| Archivo | Para qué | Cómo se levanta |
|---|---|---|
| `compose.yml` | Producción en el VPS | `docker compose up -d` |
| `compose.dev.yml` | Desarrollo local contra la BD de producción vía túnel SSH | `docker compose -f compose.dev.yml up --build` |
| `compose.staging.yml` | Stack de staging aislado (sin cambios en esta iteración) | ver `docs/staging-deploy.md` |

## Producción

El stack publica **un solo puerto, en loopback**: `127.0.0.1:8082` (variable
`HTTP_PORT`). El registro A y el certificado de `prcivot.cramer.cl` se
gestionan fuera del compose; el proxy del host reenvía a ese puerto.

Bloque de ejemplo para el nginx del host:

```nginx
server {
    listen 443 ssl http2;
    server_name prcivot.cramer.cl;

    # El wildcard *.cramer.cl ya cubre este nombre — mismo certificado que
    # sirve civot.cramer.cl, sin emitir nada nuevo. Ajustá la ruta a la real.
    ssl_certificate     /etc/letsencrypt/live/cramer.cl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cramer.cl/privkey.pem;

    client_max_body_size 25M;

    location / {
        proxy_pass         http://127.0.0.1:8082;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}

server {
    listen 80;
    server_name prcivot.cramer.cl;
    return 301 https://$host$request_uri;
}
```

`X-Forwarded-Proto` no es opcional: con `ENVIRONMENT=production` la cookie de
sesión sale con `Secure`, y sin HTTPS efectivo en el navegador el login no
persiste.

### Por qué `prcivot` y no `pr.civot`

Por el certificado. Un wildcard de TLS matchea **una sola etiqueta**: `*.cramer.cl`
cubre `prcivot.cramer.cl`, pero no `pr.civot.cramer.cl`, que tiene un nivel más.
Ese nombre habría exigido un certificado propio o un wildcard
`*.civot.cramer.cl` con validación DNS-01. Con `prcivot` el wildcard que ya
existe alcanza y no hay que emitir nada.

Si alguna vez se cambia a un nombre de dos niveles, hay que resolver el
certificado primero.

### Convivencia con lavandería

Las dos apps quedan en hosts distintos del mismo dominio padre, así que las
sesiones no se pisan: FastAPI emite la cookie sin atributo `Domain`, o sea
*host-only*, y una cookie de `civot.cramer.cl` no viaja a `prcivot.cramer.cl`.

La única forma de romper eso sería que lavandería emitiera la suya con
`Domain=.cramer.cl`: ahí sí llegaría a este host y,
como las dos se llaman `authToken`, habría ambigüedad. Vale la pena confirmarlo
una vez en el otro repositorio; si fuera el caso, renombrar la cookie de esta
app en `auth.py` y `security.py` lo resuelve.

Para el "elegir módulo" desde el login de lavandería alcanza con un enlace a
`https://prcivot.cramer.cl` en esa pantalla — cambio que va en el otro
repositorio.

### Antes del primer deploy

1. `cp .env.example .env` y completar (ver "Variables" abajo).
2. Definir la variable de repositorio `DEPLOY_DIR` (Settings → Variables) con
   la ruta del checkout en el VPS. Sin ella `deploy.yml` falla a propósito.
3. Definir el secreto `VITE_API_URL` **con el valor `/api`**. El SPA se sirve
   del mismo origen que la API; con una URL absoluta el navegador haría CORS
   contra sí mismo y la cookie `SameSite=Strict` se caería.
4. Seeds la primera vez:

```bash
docker compose exec backend python seed_admin.py
docker compose exec backend python seed_modulos.py
```

## Desarrollo local contra la base de producción

`compose.dev.yml` no levanta PostgreSQL: se conecta al que expone el stack de
producción en `127.0.0.1:5433`, alcanzado por un túnel SSH.

```bash
# terminal 1 — túnel a la BD de la app en el VPS
ssh -N -L 5433:localhost:5433 <usuario>@<vps>

# terminal 2 — túnel a RRHH, solo si vas a probar el sync de personal
ssh -N -L 5434:localhost:5432 <usuario>@192.9.200.12

# terminal 3
docker compose -f compose.dev.yml up --build
```

- Backend: <http://localhost:8000> (Swagger en `/docs`, habilitado porque
  `ENVIRONMENT=development`)
- Frontend: <http://localhost:5173>

Ambos con hot-reload: el código va montado desde el checkout.

**Esto escribe sobre datos reales.** El backend corre
`Base.metadata.create_all` al arrancar — idempotente, solo crea tablas que
faltan — pero entregas, ajustes de stock y sync de personal quedan en
producción. Para trabajar sin ese riesgo, levantá el contenedor local
`pg-prevencion` y apuntá `DEV_DB_PORT` a él en vez de al túnel.

Usar `localhost`, no `127.0.0.1`: la cookie httpOnly no se comparte entre los
dos hosts.

## De dónde sale el nombre de la base

Una sola fuente: el `.env` del repositorio, con `POSTGRES_DB`, `POSTGRES_USER` y
`POSTGRES_PASSWORD`. Los tres compose las leen, arman con ellas el
`DATABASE_URL` del backend y se lo inyectan como variable de entorno.

En el backend, `Settings.get_database_url()` devuelve `DATABASE_URL` si está
definida y solo cae a los campos `DB_HOST_PG / DB_PORT_PG / DB_USER_PG /
DB_PASSWORD_PG / DB_NAME_PG` cuando está vacía. Dentro de Docker nunca lo está:
esos campos aplican únicamente al levantar `uvicorn` a mano fuera del
contenedor, contra el `pg-prevencion` de desarrollo.

Los defaults `${POSTGRES_DB:-civot}` que había antes eran restos de la
lavandería (`civot` es esa otra base, no esta). La sintaxis `${VAR:-x}` usa `x`
cuando `VAR` está vacía o no existe, así que un `.env` incompleto levantaba
silenciosamente una base con el nombre equivocado. Ahora se declaran con
`${VAR:?mensaje}`: sin la variable, `docker compose` aborta e indica cuál falta.

## Variables

`.env.example` no incluye todavía las nuevas; agregarlas a mano al `.env`:

```dotenv
# Producción
HTTP_PORT=8082
CORS_ORIGINS=http://prcivot.cramer.cl,https://prcivot.cramer.cl

# Desarrollo local (compose.dev.yml) — extremos locales de los túneles SSH
DEV_DB_HOST=host.docker.internal
DEV_DB_PORT=5433
EMPLOYEES_DB_HOST_DEV=host.docker.internal
EMPLOYEES_DB_PORT_DEV=5434
```

`POSTGRES_PASSWORD` y `JWT_SECRET_KEY` ahora son obligatorias: si faltan,
`docker compose` aborta con un mensaje claro en vez de arrancar con una base
sin contraseña o con la clave JWT por defecto.
