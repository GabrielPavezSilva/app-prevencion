# Diseño: Panel de Sincronización Offline (SuperAdmin) + Caché de Personal

**Fecha:** 2026-04-28  
**Alcance:** Frontend únicamente

---

## Contexto

La implementación offline-first existente (IndexedDB via Dexie, `syncManager.js`, `offlineWrapper.js`) encola operaciones cuando no hay red y las sincroniza al reconectar. Sin embargo:

- Las operaciones que fallan 3 veces quedan en `status: 'error'` sin posibilidad de reintento desde la UI.
- No hay visibilidad del estado de la cola para el administrador.
- El modo manual por RUT en `ScanningPanel.jsx` no puede buscar personal offline porque no hay caché local de la tabla `personal`.

---

## Objetivos

1. **Panel de sincronización** visible solo para el rol `admin` (tab nueva en `SuperAdmin.jsx`) que permita inspeccionar y reintentar operaciones fallidas.
2. **Caché de personal** en IndexedDB para que el modo manual por RUT funcione sin conexión.

---

## Requisitos no funcionales

- Auto-sync al reconectar: ya cubierto por `window.addEventListener('online', procesarCola)`.
- Sin conflictos de inserción: ya cubierto por UUID en payload + check en backend.
- El tab de sincronización no carga datos hasta que el usuario lo activa (lazy).

---

## Diseño

### 1. `syncManager.js` — funciones nuevas

```
reintentarErrores(ids?)
  - Si ids es un array: resetea solo esos registros
  - Si ids es undefined: resetea todos los 'error'
  - Reset = { status: 'pending', retries: 0 }
  - Llama procesarCola() al terminar

limpiarSincronizados()
  - Elimina todos los registros con status: 'synced' de syncQueue
```

### 2. Tab "Sincronización" en `SuperAdmin.jsx`

Nueva entrada en el array `tabs`: `{ id: 'sincronizacion', label: 'Sincronización' }`.

**Header del tab:**
- 3 badges resumen: `N pendientes` (azul) | `N con error` (rojo) | `N sincronizados` (verde)
- Botón "Reintentar fallidos" — visible solo si hay items en `error`; resetea todos y dispara sync
- Botón "Limpiar sincronizados" — visible solo si hay items en `synced`

**Tabla de operaciones:**

| Columna | Contenido |
|---------|-----------|
| Operación | `METHOD /endpoint` (ej: `POST /rfid/inventario/scan`) |
| Detalle | Extrae `sku` o `rut` del payload si existe, si no muestra `—` |
| Fecha | `createdAt` formateado (dd/mm/yyyy hh:mm) |
| Reintentos | Número de reintentos fallidos |
| Estado | Badge coloreado: `pending` azul, `error` rojo, `synced` verde |
| Acción | Botón "Reintentar" solo en filas con `status: 'error'` |

**Comportamiento:**
- Carga datos al activar el tab (lazy).
- Se refresca automáticamente al recibir evento `civot:sync-complete`.
- Si la cola está vacía: mensaje vacío "No hay operaciones en cola".

### 3. Caché de personal en IndexedDB

**`localDb.js`:** La tabla `personal` ya está definida con índices `rut, nombre_completo, empresa, cargo`. No requiere cambios.

**`personalCacheService.js`** (archivo nuevo en `src/services/`):
```
poblarCachePersonal()
  - Llama GET /personal/todos
  - Hace bulkPut en db.personal
  - Solo si navigator.onLine

buscarPersonalOffline(searchTerm)
  - Busca en db.personal por nombre_completo o rut (case-insensitive)
  - Retorna array compatible con el formato actual de staffService
```

**Integración en `main.jsx`:** llamar `poblarCachePersonal()` al arrancar si hay red, y al reconectar (junto a `procesarCola()`).

**Integración en `ScanningPanel.jsx`:** cuando `staffService.getEmployees()` falla por falta de red, hacer fallback a `buscarPersonalOffline(searchTerm)`.

---

## Archivos a modificar / crear

| Archivo | Cambio |
|---------|--------|
| `src/sync/syncManager.js` | Agregar `reintentarErrores()` y `limpiarSincronizados()` |
| `src/pages/SuperAdmin.jsx` | Tab "Sincronización" con tabla y acciones |
| `src/services/personalCacheService.js` | Nuevo — poblar y consultar caché offline |
| `src/main.jsx` | Llamar `poblarCachePersonal()` al arrancar y al reconectar |
| `src/components/worker/ScanningPanel.jsx` | Fallback a `buscarPersonalOffline()` en búsqueda manual |

---

## Lo que NO cambia

- Backend: ningún cambio requerido.
- `offlineWrapper.js`, `localDb.js`, `useOnlineStatus.js`, `OfflineBanner.jsx`: sin modificaciones.
- El lector biométrico sigue sin funcionar offline (limitación estructural: matching 1:N requiere PostgreSQL en VPS).
