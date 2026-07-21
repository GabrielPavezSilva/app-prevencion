# 🧺 Sistema de Lavandería

Sistema de gestión de lavandería industrial con control de inventario, seguimiento de uniformes y gestión de devoluciones.

## 📁 Estructura del Proyecto

```
Lavanderia/
├── Frontend/                    # Aplicación React + Vite
│   ├── src/
│   │   ├── components/          # Componentes reutilizables
│   │   │   ├── dashboard/       # Métricas, gráficos
│   │   │   ├── layout/          # Header, Sidebar
│   │   │   ├── returns/         # Gestión devoluciones
│   │   │   ├── staff/           # Gestión personal
│   │   │   └── worker/          # Portal trabajador
│   │   ├── pages/               # Vistas principales
│   │   ├── services/            # Llamadas a la API
│   │   ├── context/             # Estado global (Auth)
│   │   └── styles/              # CSS global
│   ├── package.json
│   └── vite.config.js
│
├── Backend/                     # API FastAPI
│   ├── main.py                  # Punto de entrada
│   ├── requirements.txt         # Dependencias Python
│   ├── data/                    # Almacenamiento JSON (demo)
│   │   ├── users.json           # Usuarios del sistema
│   │   ├── employees.json       # Empleados
│   │   ├── returns.json         # Devoluciones pendientes
│   │   ├── return_items.json    # Items de devolución
│   │   ├── inventory.json       # Inventario
│   │   └── alerts.json          # Alertas
│   └── app/
│       ├── api/v1/
│       │   ├── api.py           # Router principal
│       │   └── endpoints/       # Endpoints por módulo
│       ├── core/
│       │   └── security.py      # JWT utilities
│       ├── models/
│       │   └── schemas.py       # Modelos Pydantic
│       └── services/
│           └── json_storage.py  # Persistencia JSON
│
└── .venv/                       # Entorno virtual Python
```

---

## 🚀 Despliegue de la Demo

### Requisitos Previos
- Python 3.9+
- Node.js 18+
- npm o yarn

### 1. Configurar el Backend

```bash
# Navegar al directorio del backend
cd Backend

# Crear y activar entorno virtual (si no existe)
python -m venv ../.venv
source ../.venv/bin/activate  # En Mac/Linux
# ..\.venv\Scripts\activate   # En Windows

# Instalar dependencias
pip install -r requirements.txt

# Iniciar el servidor
uvicorn main:app --reload --port 8000
```

El backend estará disponible en: **http://localhost:8000**
- Documentación Swagger: http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc

### 2. Configurar el Frontend

```bash
# En otra terminal, navegar al frontend
cd Frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

El frontend estará disponible en: **http://localhost:5173**

### 3. Credenciales de Prueba

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | admin123 | Administrador |
| jperez | worker123 | Trabajador |
| mrodriguez | worker123 | Trabajador |

---

## 🔧 Agregar Nuevas Funcionalidades

### Agregar un Nuevo Endpoint en el Backend

1. **Crear el schema Pydantic** en `Backend/app/models/schemas.py`:
```python
class NuevoItemRequest(BaseModel):
    nombre: str
    cantidad: int

class NuevoItemResponse(BaseModel):
    id: int
    nombre: str
    cantidad: int
```

2. **Crear el archivo de endpoints** en `Backend/app/api/v1/endpoints/nuevo_modulo.py`:
```python
from fastapi import APIRouter
from app.models.schemas import NuevoItemRequest, NuevoItemResponse

router = APIRouter()

@router.get("/items")
async def get_items():
    return []

@router.post("/items", response_model=NuevoItemResponse)
async def create_item(request: NuevoItemRequest):
    # Lógica aquí
    pass
```

3. **Registrar el router** en `Backend/app/api/v1/api.py`:
```python
from app.api.v1.endpoints import nuevo_modulo

api_router.include_router(
    nuevo_modulo.router, 
    prefix="/nuevo", 
    tags=["Nuevo Módulo"]
)
```

### Agregar un Nuevo Servicio en el Frontend

1. **Crear el servicio** en `Frontend/src/services/nuevoService.js`:
```javascript
import apiClient from './api';

export const getItems = async () => {
    return apiClient.get('/nuevo/items');
};

export const createItem = async (data) => {
    return apiClient.post('/nuevo/items', data);
};

export default { getItems, createItem };
```

2. **Usar en un componente**:
```jsx
import { getItems } from '../services/nuevoService';

useEffect(() => {
    getItems().then(data => setItems(data));
}, []);
```

### Agregar Datos de Prueba

Los datos se almacenan en archivos JSON en `Backend/data/`. Para agregar nuevos datos:

1. Crear archivo `Backend/data/nuevo_modulo.json`
2. Agregar instancia de storage en `Backend/app/services/json_storage.py`:
```python
nuevo_storage = JSONStorage(DATA_DIR / 'nuevo_modulo.json')
```

---

## 📦 Migración a Producción (SQL Server)

1. **Reemplazar** `json_storage.py` con repositorios SQLAlchemy
2. **Configurar** connection string en variables de entorno:
```bash
DATABASE_URL="mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server"
```
3. **Crear modelos ORM** basados en los schemas de Pydantic
4. **Usar Alembic** para migraciones de base de datos

---

## 📚 Endpoints Disponibles

| Módulo | Endpoints |
|--------|-----------|
| Auth | `POST /api/auth/login`, `POST /api/auth/logout` |
| Staff | `GET/POST /api/staff/employees`, `GET/PUT/DELETE /api/staff/employees/{id}` |
| Returns | `GET /api/returns/employees`, `POST /api/returns/process` |
| Inventory | `GET /api/inventory/categories/levels` |
| Alerts | `GET /api/alerts/recent`, `PUT /api/alerts/{id}/read` |
| Stats | `GET /api/stats/inventory` |

---

## 🛠️ Herramientas de Desarrollo

- **Backend**: FastAPI, Pydantic, uvicorn
- **Frontend**: React 18, Vite, CSS Modules
- **Persistencia Demo**: JSON files
- **Persistencia Producción**: SQL Server + SQLAlchemy
