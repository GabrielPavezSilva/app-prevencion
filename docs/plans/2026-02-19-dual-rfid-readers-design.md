# Diseño: Estaciones RFID Dedicadas (Recepción y Asignación)

**Fecha:** 2026-02-19
**Rama:** `incorporacion_categorias`
**Estado:** Aprobado — listo para implementar

---

## Contexto

El sistema actualmente usa un único lector RFID (`UHFReaderManager` singleton) para todas las operaciones. Se requiere soportar dos lectores físicos independientes:

- **Lector de Recepción** (`COM2`) — exclusivo para recibir prendas en `WorkerDashboard`
- **Lector de Asignación** (`COM3`) — para asignar prendas en `WorkerDashboard` e `InventoryMode`

---

## Decisiones clave

| Pregunta | Decisión |
|----------|----------|
| ¿Qué pasa si un puerto no existe al arrancar? | El backend arranca igual; el lector queda en estado "desconectado" (lazy-connect) |
| ¿Qué lector usan las operaciones admin (write, scan)? | El lector de asignación (COM3) por defecto |
| ¿Cómo indica el frontend qué lector usar? | Query param `?role=reception` o `?role=assignment` |
| Enfoque de implementación | `MultiReaderManager` con diccionario de readers por rol |

---

## Archivos afectados

| Archivo | Tipo de cambio |
|---------|----------------|
| `Backend/.env` | +`RFID_RECEPTION_PORT`, +`RFID_ASSIGNMENT_PORT`, eliminar `RFID_SERIAL_PORT` |
| `Backend/app/core/config.py` | +2 variables, eliminar `RFID_SERIAL_PORT` |
| `Backend/app/services/uhf_reader.py` | `UHFReaderManager` → `MultiReaderManager` |
| `Backend/app/services/rfid_service.py` | Métodos de hardware reciben `role: str` |
| `Backend/app/api/v1/endpoints/endpoints_rfid.py` | Query param `role` en 5 endpoints de hardware |
| `Frontend/src/services/rfidService.js` | 4 funciones reciben `role` |
| `Frontend/src/components/worker/ScanningPanel.jsx` | Pasa `role` según modo, maneja `hardware_error` |

---

## Diseño detallado

### 1. Configuración

**`Backend/.env`:**
```
# Puerto del lector de Recepción (WorkerDashboard modo "Recibir")
# Para cambiar el puerto: editar este archivo y reiniciar el backend
RFID_RECEPTION_PORT=COM2

# Puerto del lector de Asignación (WorkerDashboard modo "Asignar" + InventoryMode)
# Para cambiar el puerto: editar este archivo y reiniciar el backend
RFID_ASSIGNMENT_PORT=COM3

RFID_BAUDRATE=57600
```

**`config.py`:**
```python
RFID_RECEPTION_PORT: str = "COM2"   # Lector de recepción
RFID_ASSIGNMENT_PORT: str = "COM3"  # Lector de asignación
RFID_BAUDRATE: int = 57600
```

---

### 2. Backend — `uhf_reader.py`

`UHFReader` (protocolo serial de bajo nivel) **no cambia**.

`UHFReaderManager` se reemplaza por `MultiReaderManager`:

```python
VALID_ROLES = ("reception", "assignment")

class MultiReaderManager:
    """
    Gestiona múltiples lectores RFID UHF indexados por rol.

    Roles disponibles:
      - "reception"  → puerto RFID_RECEPTION_PORT  (defecto: COM2)
      - "assignment" → puerto RFID_ASSIGNMENT_PORT (defecto: COM3)

    Para cambiar un puerto COM: editar Backend/.env y reiniciar el backend.
    No requiere cambios en código.
    """
    def __init__(self):
        self._readers = {
            "reception":  UHFReader(settings.RFID_RECEPTION_PORT,  settings.RFID_BAUDRATE),
            "assignment": UHFReader(settings.RFID_ASSIGNMENT_PORT, settings.RFID_BAUDRATE),
        }
        # Lock independiente por lector: recepción no bloquea asignación
        self._locks = {role: threading.Lock() for role in VALID_ROLES}

    def _validate_role(self, role: str):
        if role not in VALID_ROLES:
            raise ValueError(f"Rol inválido: '{role}'. Use {VALID_ROLES}")

    def scan(self, role: str) -> Optional[str]:
        """Escanea con el lector del rol indicado. Lazy-connect si no está conectado."""
        self._validate_role(role)
        with self._locks[role]:
            reader = self._readers[role]
            if not reader.conectado:
                reader.conectar()
            return reader.inventario()

    def conectar(self, role: str) -> bool: ...
    def desconectar(self, role: str): ...
    def status(self, role: str) -> dict: ...
    def leer_user(self, role: str, epc_hex: str, palabras: int = 2) -> Optional[str]: ...
    def escribir_user(self, role: str, epc_hex: str, hex_data: str) -> bool: ...

multi_reader_manager = MultiReaderManager()
```

---

### 3. Backend — `rfid_service.py`

Métodos de hardware actualizados:

```python
from app.services.uhf_reader import multi_reader_manager

class RFIDService:
    def get_reader_status(self, role: str = "assignment") -> RFIDReaderStatus:
        status = multi_reader_manager.status(role)
        return RFIDReaderStatus(
            conectado=status["conectado"],
            puerto=status["puerto"],
            baudrate=settings.RFID_BAUDRATE,
        )

    def scan_tag(self, role: str = "assignment") -> RFIDScanResponse:
        epc = multi_reader_manager.scan(role)
        if not epc:
            lector_conectado = multi_reader_manager.status(role)["conectado"]
            return RFIDScanResponse(
                encontrado=False,
                hardware_error=not lector_conectado,
                hardware_role=role,
            )
        # ... enriquece con info de BD (igual que hoy)

    def write_sku_to_tag(self, epc: str, sku: str, role: str = "assignment") -> bool:
        # Admin siempre usa lector de asignación
        ...

    def scan_modo_inventario(self) -> InventarioModoScanResponse:
        # InventoryMode siempre usa lector de asignación
        epc = multi_reader_manager.scan("assignment")
        ...
```

---

### 4. Backend — `endpoints_rfid.py`

5 endpoints de hardware reciben `role` como query param:

```python
from fastapi import Query

@router.post("/reader/scan")
async def reader_scan(
    role: str = Query(default="assignment", description="Rol: reception | assignment"),
    db: Session = Depends(get_mysql_db)
):
    service = RFIDService(db)
    return service.scan_tag(role=role)

# Mismo patrón en: /reader/status, /reader/connect, /reader/disconnect, /reader/read/{epc}, /reader/write
```

Endpoints que **no cambian**: `/lectura`, `/buscar/{epc}`, `/vincular`, `/log`, `/inventario/*`

---

### 5. Frontend — `rfidService.js`

```javascript
// Funciones actualizadas — role por defecto "assignment" para no romper llamadas existentes
export const scanTag = async (role = 'assignment') =>
    apiClient.post(`/rfid/reader/scan?role=${role}`);

export const connectReader = async (role = 'assignment') =>
    apiClient.post(`/rfid/reader/connect?role=${role}`);

export const disconnectReader = async (role = 'assignment') =>
    apiClient.post(`/rfid/reader/disconnect?role=${role}`);

export const getReaderStatus = async (role = 'assignment') =>
    apiClient.get(`/rfid/reader/status?role=${role}`);
```

---

### 6. Frontend — `ScanningPanel.jsx`

Lógica de rol según modo activo:

```javascript
// El panel ya sabe si está en modo "receive" o "assign"
const rfidRole = mode === 'receive' ? 'reception' : 'assignment';
const result = await scanTag(rfidRole);

if (result.hardware_error) {
    const roleName = result.hardware_role === 'reception' ? 'Recepción (COM2)' : 'Asignación (COM3)';
    setHardwareError(`Error de Hardware: Lector de ${roleName} no disponible. Contacte a Soporte.`);
    return;
}
setHardwareError(null); // limpiar si el escaneo fue exitoso
```

El error solo aparece en el panel del modo afectado. El otro modo sigue operativo.

---

## Flujo completo post-implementación

```
Operario selecciona modo "Recibir"
    → ScanningPanel determina role = "reception"
    → POST /api/rfid/reader/scan?role=reception
    → MultiReaderManager.scan("reception")
    → UHFReader(COM2).inventario()
    → Retorna EPC o hardware_error si COM2 no responde

Operario selecciona modo "Asignar"
    → ScanningPanel determina role = "assignment"
    → POST /api/rfid/reader/scan?role=assignment
    → MultiReaderManager.scan("assignment")
    → UHFReader(COM3).inventario()
    → Retorna EPC o hardware_error si COM3 no responde

InventoryMode (admin)
    → scan_modo_inventario() siempre usa "assignment" internamente
    → No requiere cambios en el frontend
```

---

## Guía de mantenimiento

**¿Cómo cambiar los puertos COM en el futuro?**

1. Editar `Backend/.env`:
   ```
   RFID_RECEPTION_PORT=COM4    # Cambiar al nuevo puerto
   RFID_ASSIGNMENT_PORT=COM5
   ```
2. Reiniciar el backend (`uvicorn main:app --reload --port 8000`)
3. No se requieren cambios en código.

**¿Cómo agregar un tercer lector en el futuro?**

1. Agregar `RFID_NUEVO_PORT=COMX` en `.env` y `config.py`
2. En `MultiReaderManager.__init__`, agregar `"nuevo_rol": UHFReader(settings.RFID_NUEVO_PORT, ...)`
3. Agregar `"nuevo_rol"` a `VALID_ROLES`
4. Los endpoints ya aceptan cualquier string como `role`, sin cambios adicionales
