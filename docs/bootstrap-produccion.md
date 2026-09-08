# Puesta en marcha: base en el VPS + desarrollo local por túnel

Guía de una sola vez, para dejar la base de producción creada y sembrada, y el
entorno local trabajando contra ella. Al terminar tenés:

- PostgreSQL corriendo en el VPS, escuchando **solo en loopback**.
- El esquema creado y los seeds aplicados (usuario admin, módulos y roles).
- Backend y frontend locales con hot-reload contra esa base, vía túnel SSH.

El backend y el frontend **no** se levantan todavía en el VPS: sus imágenes se
publican en GHCR recién cuando `main` reciba el merge de esta rama. Hasta
entonces, en producción vive solo la base. Está bien: es exactamente lo que
necesitás para empezar a construir features.

> Convenciones: `$` es tu máquina (PowerShell en Windows), `vps$` es la sesión
> SSH en el servidor.

---

## 1. Comprobar el terreno en el VPS

```bash
$ ssh <usuario>@<vps>

vps$ docker --version
vps$ docker compose version        # tiene que ser v2.x — con guion, `docker-compose`, es la v1
```

Los dos puertos que este stack quiere en loopback pueden estar tomados por
lavandería. Miralos antes de crear nada:

```bash
vps$ ss -ltnp | grep -E '5433|8082'
```

- Sin salida → los dos libres, seguí con los valores por defecto.
- Si `5433` aparece → elegí otro (`5434`, `5435`…) y anotalo: va en `DB_HOST_PORT`.
- Si `8082` aparece → lo mismo con `HTTP_PORT`.

## 2. Clonar el repositorio

Elegí una ruta hermana a la de lavandería, no dentro de ella. Esta ruta es la
que después va en la variable `DEPLOY_DIR` del repositorio en GitHub.

```bash
vps$ sudo mkdir -p /opt/prevencion
vps$ sudo chown $USER:$USER /opt/prevencion
vps$ git clone <url-del-repo> /opt/prevencion
vps$ cd /opt/prevencion
vps$ git checkout infra/compose-prcivot     # hasta que esté mergeada a main
```

## 3. Crear el `.env`

```bash
vps$ cp .env.example .env
```

Generá los dos secretos (hex puro, sin caracteres que rompan la URL de
conexión — importa, porque los compose arman `DATABASE_URL` concatenando sin
escapar):

```bash
vps$ echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
vps$ echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
```

Editá `.env` con esos valores y el resto. Debe quedar así:

```dotenv
# ── Base de datos ──
POSTGRES_DB=db_prevencion
POSTGRES_USER=prevencion
POSTGRES_PASSWORD=<el hex generado arriba>

# ── Backend ──
JWT_SECRET_KEY=<el otro hex>
ENVIRONMENT=production

# ── Puertos en loopback (paso 1) ──
DB_HOST_PORT=5433
HTTP_PORT=8082
CORS_ORIGINS=http://prcivot.cramer.cl,https://prcivot.cramer.cl

# ── Base de RRHH (solo lectura; se usa cuando levantes el backend en el VPS) ──
EMPLOYEES_DB_HOST=host.docker.internal
EMPLOYEES_DB_PORT=5432
EMPLOYEES_DB_NAME=rh_cramer
EMPLOYEES_DB_USER=<usuario de lectura de rh_cramer>
EMPLOYEES_DB_PASSWORD=<su contraseña>
```

`POSTGRES_DB` y `POSTGRES_USER` no tienen valor por defecto: si faltan, compose
aborta diciendo cuál. Es a propósito — ver `docs/deploy-prcivot.md`.

**Guardá `POSTGRES_PASSWORD` en tu gestor de contraseñas ahora.** Lo vas a
necesitar en el `.env` local del paso 6, y el `.env` del VPS no se versiona.

## 4. Levantar solo la base

```bash
vps$ docker compose up -d postgres
vps$ docker compose ps
```

Esperá a que la columna de estado diga `healthy` (unos 10 segundos). Si dice
`unhealthy` o el contenedor reinicia:

```bash
vps$ docker compose logs postgres
```

## 5. Verificar que la base quedó bien

```bash
vps$ docker compose exec postgres psql -U prevencion -d db_prevencion -c '\l'
```

Tienen que aparecer `db_prevencion` y su dueño `prevencion`. Todavía no hay
tablas — las crea el backend al arrancar, en el paso 7.

> Si en vez de `db_prevencion` ves una base llamada `civot`, este volumen viene
> de un intento anterior con los defaults viejos. `POSTGRES_DB` solo se aplica
> al **crear** el volumen, así que no la renombra. Con la base todavía vacía, lo
> más limpio es empezar de cero:
> `docker compose down -v` y volver al paso 4.
> **`-v` borra el volumen de datos.** Solo mientras la base esté vacía.

Confirmá que quedó escuchando en loopback y no expuesta a internet:

```bash
vps$ ss -ltnp | grep 5433        # debe decir 127.0.0.1:5433, nunca 0.0.0.0:5433
```

---

## 6. Del lado local: `.env` y túnel

En tu máquina, en el checkout del proyecto:

```powershell
$ Copy-Item .env.example .env
```

Editá el `.env` local. Las tres variables de la base tienen que ser
**idénticas** a las del VPS — es la misma base, vista por el túnel:

```dotenv
POSTGRES_DB=db_prevencion
POSTGRES_USER=prevencion
POSTGRES_PASSWORD=<el mismo hex del VPS>

JWT_SECRET_KEY=<cualquier valor; en dev no importa>

# Extremo local del túnel
DEV_DB_HOST=host.docker.internal
DEV_DB_PORT=5433
```

Abrí el túnel y **dejá esa terminal abierta** — mientras corra, el `5433` de tu
máquina es el `5433` del VPS:

```powershell
$ ssh -N -L 5433:localhost:5433 <usuario>@<vps>
```

Si en el paso 1 elegiste otro puerto en el VPS, el mapeo es
`-L 5433:localhost:<puerto_del_vps>`: el lado izquierdo es local y no hace falta
cambiarlo.

En otra terminal, comprobá que el túnel realmente llega:

```powershell
$ Test-NetConnection localhost -Port 5433
```

`TcpTestSucceeded : True` y seguimos.

## 7. Crear el esquema

Levantá el stack de desarrollo. El backend corre `Base.metadata.create_all` al
arrancar y crea todas las tablas que falten:

```powershell
$ docker compose -f compose.dev.yml up --build
```

En los logs del backend tiene que aparecer `Tablas verificadas/creadas.` y
después el arranque de uvicorn. Si en cambio ves un error de conexión, el túnel
se cayó o la contraseña no coincide con la del VPS.

Verificá desde el VPS que las tablas están:

```bash
vps$ docker compose exec postgres psql -U prevencion -d db_prevencion -c '\dt'
```

## 8. Sembrar usuario y módulos

Con el stack de dev arriba, en otra terminal local:

```powershell
$ docker compose -f compose.dev.yml exec backend python seed_admin.py
$ docker compose -f compose.dev.yml exec backend python seed_modulos.py
```

Los dos son idempotentes. Escriben en la base de producción a través del túnel,
que es justamente lo que queremos acá.

## 9. Probar

Abrí <http://localhost:5173> y entrá con `admin` / `admin123`.

**Cambiá esa contraseña antes de que la aplicación reciba tráfico real.** El
seed la deja en el valor por defecto, público en el repositorio: sirve para
arrancar, no para producción. Se cambia desde `/superadmin`.

Swagger queda en <http://localhost:8000/docs> (habilitado porque el stack de dev
corre con `ENVIRONMENT=development`).

---

## Trabajo del día a día

Una vez hecho todo lo anterior, arrancar es:

```powershell
# terminal 1
$ ssh -N -L 5433:localhost:5433 <usuario>@<vps>

# terminal 2
$ docker compose -f compose.dev.yml up
```

Backend y frontend recargan solos al guardar. Recordá que **lo que hagas desde
la UI queda en la base de producción**: entregas, ajustes de stock, personal.
Mientras no haya usuarios reales da lo mismo; cuando los haya, conviene volver
al postgres local (`pg-prevencion`) apuntando `DEV_DB_PORT` a él, y dejar el
túnel para consultar.

Un cambio de columna sobre una tabla que ya existe **no se aplica solo** — no
hay migraciones. `create_all` solo crea tablas que faltan. Ese `ALTER TABLE` va
a mano contra la base.

## Lo que queda pendiente para el stack completo

**Los tres primeros puntos requieren permiso de administrador sobre el
repositorio** (`GabrielPavezSilva/app-prevencion`): un colaborador sin ese
permiso no puede ni generar el token del runner ni crear variables o secretos.

1. **Registrar el runner de este proyecto en el VPS.** El job `deploy` corre en
   `runs-on: [self-hosted, prevencion]` y hoy **no existe ningún runner**
   registrado en este repositorio: los de `/home/admin/actions-runner-*`
   pertenecen a otros repos y no toman estos jobs. Como el dueño es una cuenta
   personal y no una organización, tampoco hay runners heredados. Sin runner el
   job queda encolado ~24 h y falla por timeout.

   ```bash
   mkdir -p /home/admin/actions-runner-prevencion && cd $_
   # Verificar la última versión en github.com/actions/runner/releases
   curl -o actions-runner-linux-x64.tar.gz -L      https://github.com/actions/runner/releases/download/v2.331.0/actions-runner-linux-x64-2.331.0.tar.gz
   tar xzf actions-runner-linux-x64.tar.gz
   # El token sale de Settings -> Actions -> Runners -> New self-hosted runner
   # y dura una hora.
   ./config.sh --url https://github.com/GabrielPavezSilva/app-prevencion      --token <TOKEN> --name prevencion-vps --labels prevencion --unattended
   sudo ./svc.sh install admin && sudo ./svc.sh start
   ```

   La label `prevencion` no es decorativa: con `self-hosted` a secas el job
   podía caer en el runner de otro proyecto del mismo dueño y reiniciar el
   stack equivocado.

2. Definir `DEPLOY_DIR=/opt/prevencion` en Settings → Variables del repositorio.
3. Definir el secreto `VITE_API_URL` con el valor `/api`.
4. En el VPS: `git pull && docker compose up -d` — ahí se suman backend,
   frontend, nginx y ofelia.
5. Configurar el `server` de nginx del host y el registro A, según
   `docs/deploy-prcivot.md`.

### Mientras tanto: deploy manual

El job `deploy` está apagado con `if: vars.DEPLOY_DIR != ''`, así que hoy se
salta y ningún merge deja un job encolado. El job `build` **sí corre**: publica
`prevencion-backend` y `prevencion-frontend` en GHCR con las etiquetas `latest`
y el SHA del commit. El deploy se hace a mano en el VPS:

```bash
cd /opt/prevencion
git pull
docker compose pull backend frontend     # baja las imágenes que publicó el CI
docker compose up -d --no-deps --wait backend frontend
docker image prune -f
```

Definir la variable `DEPLOY_DIR` es lo único que vuelve a encender el job
automático — junto con el runner, sin el cual quedaría encolado igual.

### Runner self-hosted en un repositorio público

El repositorio es público, y un runner self-hosted en un repo público es el
caso que GitHub desaconseja: un PR desde un fork podría ejecutar código ajeno
en el VPS. Hoy no ocurre porque `deploy.yml` solo se dispara con `push` a
`main` y `ci.yml` corre en `ubuntu-latest`. Para que siga así:

- Ningún workflow con trigger `pull_request` debe usar `runs-on: self-hosted`.
- Settings → Actions → General: mantener "Require approval for all external
  contributors".
- Si el repositorio no necesita ser público, pasarlo a privado elimina el
  problema de raíz.
