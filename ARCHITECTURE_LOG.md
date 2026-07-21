# Architecture & Permissions Log

Registro de decisiones arquitectónicas y cambios de permisos/visualización/módulos.  
El hook agrega entradas automáticamente al editar archivos relevantes del Backend.  
Completar los campos **Decisión** y **Descartado** manualmente tras cada entrada.

---

## [2026-05-29] PERMISOS — security.py
- **Archivo:** `app/core/security.py`
- **Decisión:** JWT `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` ahora leen de `settings` (config.py → .env). Eliminado hardcoding `"demo-secret-key-lavanderia-2024"` y `ACCESS_TOKEN_EXPIRE_HOURS = 24`.
- **Descartado:** Mantener constantes hardcodeadas en el módulo (riesgo crítico: cualquiera puede forjar tokens si conoce la clave).

## [2026-05-29] PERMISOS — personal.py
- **Archivo:** `app/api/v1/endpoints/personal.py`
- **Decisión:** `Depends(get_current_user)` agregado a `GET /todos` y `GET /{rut}`. Cualquier usuario autenticado puede listar y buscar personal.
- **Descartado:** Restringir solo a `admin` (se descartó porque el WorkerDashboard también necesita buscar personal por RUT tras identificación biométrica).

## [2026-05-29] PERMISOS — devoluciones.py
- **Archivo:** `app/api/v1/endpoints/devoluciones.py`
- **Decisión:** `Depends(get_current_user)` en los 3 endpoints (`/employees`, `/employees/{id}/items`, `/process`). Acceso para cualquier usuario autenticado.
- **Descartado:** Solo `admin` — se podría refinar en fase de role-based access.

## [2026-05-29] VISUALIZACION — stats.py
- **Archivo:** `app/api/v1/endpoints/stats.py`
- **Decisión:** `Depends(get_current_user)` en `GET /inventario` (dashboard stats). Solo usuarios autenticados ven estadísticas agregadas.
- **Descartado:** Público sin auth (inaceptable: expone volumetría del inventario de la empresa).

## [2026-05-29] BACKEND — inventario.py
- **Archivo:** `app/api/v1/endpoints/inventario.py`
- **Decisión:** Auth en todos los CRUDs de catálogos (tipos, tallas, secciones, temporadas, empresas). Errors 500 ya no exponen `str(e)` — se loguea internamente con `logger.error(exc_info=True)` y se retorna mensaje genérico al cliente.
- **Descartado:** `str(e)` en responses (exponía queries SQL, nombres de tablas y stack traces al cliente).

## [2026-05-29] PERMISOS — biometria.py
- **Archivo:** `app/api/v1/endpoints/biometria.py`
- **Decisión:** Auth en todos los endpoints proxy al middleware: `/status`, `/identificar`, `/enrolar`, `/estado/{id}`, `/cancelar/{id}`, `/templates`, `/guardar-huella/{rut}`.
- **Descartado:** Dejar `/templates` sin auth (el middleware local lo llama directamente — se resuelve porque el middleware usa `hardwareClient` que no pasa por el backend autenticado).

## [2026-05-29] PERMISOS — endpoints_rfid.py
- **Archivo:** `app/api/v1/endpoints/endpoints_rfid.py`
- **Decisión:** Auth en todos los endpoints RFID sin protección previa: log, hardware control (`reader/*`), modo inventario, `GET /inventario`, desvincular tag.
- **Descartado:** Dejar endpoints de hardware sin auth bajo el argumento de que solo son accesibles en red local — se rechazó porque el backend está en VPS público.

## [2026-05-29] PERMISOS — asignaciones.py
- **Archivo:** `app/api/v1/endpoints/asignaciones.py`
- **Decisión:** `Depends(get_current_user)` en `GET /todas` (ya lo importaba pero no lo usaba).
- **Descartado:** Ninguna alternativa considerada.

## [2026-05-29] PERMISOS — prendas_predeterminadas.py
- **Archivo:** `app/api/v1/endpoints/prendas_predeterminadas.py`
- **Decisión:** Auth en todos los endpoints (listar, obtener por cargo/empresa, crear, bulk set, eliminar).
- **Descartado:** Ninguna alternativa considerada.
