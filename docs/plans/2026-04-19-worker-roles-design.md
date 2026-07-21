# Diseño: Separación del WorkerDashboard en roles dedicados

**Fecha:** 2026-04-19  
**Rama:** ajuste-diseno  
**Estado:** Aprobado

---

## Contexto

El sistema se desplegará en dos computadores físicos distintos en la lavandería:
- **Computador 1:** Solo recibe prendas devueltas por trabajadores
- **Computador 2:** Solo asigna prendas a trabajadores

El `WorkerDashboard.jsx` actual combina ambas funciones en un solo componente con tabs internos. El `ScanningPanel.jsx` alterna entre modo `receive` y modo `assign`. Se requiere separar en páginas independientes, con acceso controlado por rol.

---

## Decisiones de diseño

| Pregunta | Decisión |
|----------|----------|
| ¿Cómo distinguir qué página ve cada computador? | Por rol de usuario en BD |
| ¿Qué pasa con el rol `worker` actual? | Se elimina; reemplazado por dos roles nuevos |
| ¿Qué componentes lleva cada página? | Completas pero enfocadas (ver detalle abajo) |
| ¿Puede el admin acceder a las páginas worker? | Sí, sin restricción |
| ¿Pueden los workers acceder al panel admin? | No; redirigen a su propia página |

---

## Roles nuevos

| `nombre_rol` | Acceso |
|-------------|--------|
| `worker_recepcion` | Solo `/worker/recibir` |
| `worker_asignacion` | Solo `/worker/asignar` |
| `admin` | Todo, incluyendo `/worker/recibir` y `/worker/asignar` |

El rol `worker` (existente) se elimina o deja sin uso.

---

## Rutas

| Ruta | Rol requerido | Componente |
|------|--------------|------------|
| `/worker/recibir` | `worker_recepcion` o `admin` | `RecepcionDashboard.jsx` |
| `/worker/asignar` | `worker_asignacion` o `admin` | `AsignacionDashboard.jsx` |
| `/worker` | — | Redirect según rol |

---

## Páginas

### `RecepcionDashboard.jsx` (`/worker/recibir`)

Layout de dos columnas, igual al actual:

- **Izquierda:**
  - `WorkerProfile` — datos del usuario logueado (operario de recepción)
  - `ScanHistory` — historial filtrado por acción `RECEPCION`

- **Derecha:**
  - Panel de escaneo masivo: botón Iniciar/Detener + lista de prendas escaneadas en la sesión
  - Usa lector `RFID_ROLES.RECEPTION` (COM2)
  - Sin biometría, sin búsqueda de trabajador, sin botón "Asignar"

### `AsignacionDashboard.jsx` (`/worker/asignar`)

Layout de dos columnas, igual al actual:

- **Izquierda:**
  - `WorkerProfile` — datos del **trabajador identificado** (se actualiza tras biometría/RUT)
  - `WardrobeVisualizer` — prendas asignadas al trabajador identificado

- **Derecha:**
  - Identificación biométrica (huella) + fallback manual por RUT
  - Panel de escaneo de asignación + lista de prendas asignadas en la sesión
  - `ScanHistory` — historial general de asignaciones
  - Usa lector `RFID_ROLES.ASSIGNMENT` (COM3)

---

## Cambios por archivo

### Backend

| Archivo / Acción | Detalle |
|-----------------|---------|
| SQL / seed | Insertar roles `worker_recepcion` (id=3) y `worker_asignacion` (id=4) en tabla `roles` |
| `seed_admin.py` | Opcional: agregar usuarios de prueba para los nuevos roles |
| `app/core/security.py` | Verificar que la validación de JWT acepta los nuevos nombres de rol |

### Frontend

| Archivo | Cambio |
|---------|--------|
| `App.jsx` | Rutas `/worker/recibir` y `/worker/asignar`; `ProtectedRoute` restringe por rol; redirect post-login actualizado; `/worker` redirige según rol |
| `AuthContext.jsx` | Mapa de redirección post-login extendido con los dos roles nuevos |
| `WorkerDashboard.jsx` | Refactorizar → `RecepcionDashboard.jsx` (modo recibir únicamente) |
| `ScanningPanel.jsx` | Agregar prop `mode: 'receive' | 'assign'`; eliminar tabs internos; renderizar solo el bloque del modo recibido |
| Nueva página | `AsignacionDashboard.jsx` — página dedicada al modo asignación |
| `WorkerDashboard.css` | Renombrar o duplicar según estructura final |

---

## Flujo de acceso post-login

```
login exitoso
    ├── role === 'admin'             → /  (sidebar completo)
    ├── role === 'worker_recepcion'  → /worker/recibir
    └── role === 'worker_asignacion' → /worker/asignar
```

```
navegación directa a ruta protegida
    ├── admin                        → pasa siempre
    ├── worker_recepcion intentando /worker/asignar o / → redirect /worker/recibir
    └── worker_asignacion intentando /worker/recibir o / → redirect /worker/asignar
```

---

## Lo que NO cambia

- Lógica de escaneo RFID (loops, hardware errors, registrarLectura)
- Lógica biométrica (FingerprintControl, polling, huellasService)
- CSS variables y estilos generales
- WorkerLayout, WorkerProfile, ScanHistory, WardrobeVisualizer (sin modificaciones)
- Endpoint `/api/asignaciones/todas` y demás APIs backend
