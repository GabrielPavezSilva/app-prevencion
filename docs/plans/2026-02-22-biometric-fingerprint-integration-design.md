# Integración Biométrica de Huellas — DigitalPersona U.are.U 4500

**Fecha:** 2026-02-22
**Estado:** Aprobado

---

## Resumen

Integrar identificación (1:N) y enrolamiento (4 capturas) de huellas digitales usando el lector DigitalPersona U.are.U 4500. El backend usa pythonnet para comunicarse con las DLLs .NET del SDK. El frontend integra identificación en WorkerDashboard y enrolamiento en Staff.

## Decisiones de diseño

| Decisión | Elección | Alternativas descartadas |
|----------|----------|--------------------------|
| Patrón de concurrencia | Background thread + polling | Endpoint bloqueante, WebSocket |
| Arquitectura backend | Singleton `BiometriaManager` (patrón RFID) | Service stateless |
| Identificación (UI) | WorkerDashboard tab Asignar | Nueva página Assignments.jsx |
| Enrolamiento (UI) | Staff.jsx (modal existente) | WorkerDashboard |

## Backend

### Archivos nuevos

| Archivo | Propósito |
|---------|-----------|
| `app/services/biometria_manager.py` | Singleton: gestión del lector, sesiones en memoria, threads |
| `app/services/biometria_service.py` | Orquestación entre manager y repository |
| `app/repositories/biometria_repository.py` | Acceso a `personal.huella_digital` |
| `app/schemas/biometria.py` | Pydantic models para request/response |
| `app/api/v1/endpoints/biometria.py` | Endpoints HTTP |

### Registrar en `app/api/v1/api.py`

```python
from app.api.v1.endpoints import biometria
api_router.include_router(biometria.router, prefix="/biometria", tags=["Biometría"])
```

### Singleton: `BiometriaManager`

- `_reader`: instancia del lector U.are.U (lazy init)
- `_reader_lock`: threading.Lock() — una operación a la vez
- `_sesiones`: dict {session_id: SesionCaptura}
- Callbacks como funciones standalone a nivel de módulo (requisito pythonnet)
- Auto-limpieza de sesiones >5min

### Sesión de captura

```python
{
    "session_id": str,
    "tipo": "identificacion" | "enrolamiento",
    "status": "esperando_dedo" | "procesando" | "completado" | "error" | "cancelado",
    "paso_actual": int,
    "pasos_total": 1 | 4,
    "resultado": None | dict,
    "error": None | str,
    "created_at": datetime
}
```

### Endpoints: `/api/biometria/`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/identificar` | Inicia identificación 1:N → `{session_id}` |
| POST | `/enrolar/{rut}` | Inicia enrolamiento 4 capturas → `{session_id}` |
| GET | `/estado/{session_id}` | Polling del estado → `{status, paso_actual, resultado...}` |
| POST | `/cancelar/{session_id}` | Cancela sesión activa |
| GET | `/reader/status` | Estado del lector USB |

### Manejo de errores

| Escenario | Respuesta |
|-----------|-----------|
| Lector no conectado | `reader/status` → `{conectado: false}` |
| Lector ocupado | HTTP 409 Conflict |
| Timeout 15s | `status: "error"`, `error: "Timeout"` |
| Calidad baja | Reintento automático (hasta 3 por paso) |
| Huella no reconocida | `status: "completado"`, `resultado: null` |
| DLLs no encontradas | HTTP 503 |

### Seguridad del lector

```python
try:
    reader.Open(Constants.CapturePriority.DP_PRIORITY_EXCLUSIVE)
    # ... capturas ...
finally:
    reader.CancelCapture()
    reader.Dispose()
```

## Frontend

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `services/huellasService.js` | Reescribir rutas → `/api/biometria/*` |
| `components/fingerprint/FingerprintControl.jsx` | Adaptar para polling + progreso |
| `pages/WorkerDashboard.jsx` | Integrar identificación por huella en tab Asignar |
| `pages/Staff.jsx` | Conectar modal con rutas reales |

### WorkerDashboard — Flujo de identificación

```
[Botón "Identificar con Huella"] → polling /estado → Tarjeta datos empleado → RFID
[Link "Modo Manual (RUT)"] → Input clásico (respaldo)
```

### Staff — Flujo de enrolamiento

```
Botón 👆 en fila → Modal → POST /enrolar/{rut} → Polling → 4 pasos con feedback visual
◉ ◉ ○ ○  →  "Captura 3 de 4..."  →  toast.success al completar
```

## Sin variables de entorno nuevas

El lector se detecta automáticamente por USB via `ReaderCollection.GetReaders()`.
