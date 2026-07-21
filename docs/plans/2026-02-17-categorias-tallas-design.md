# Diseño: Gestión de Categorías y Tallas desde el Frontend

**Fecha:** 2026-02-17
**Rama:** incorporacion_categorias
**Estado:** Aprobado

---

## Contexto

El sistema de lavandería ya cuenta con los modelos ORM `TipoPrenda` y `Talla` y dos endpoints GET de solo lectura (`/api/inventario/tipos`, `/api/inventario/tallas`). El modo inventario RFID los usa como dropdowns. El commit `2d1379f` deja explícitamente pendiente "crear categorias desde frontend". Este diseño completa esa funcionalidad.

---

## Objetivo

Permitir al administrador crear, editar, eliminar y listar tipos de prenda (categorías) y tallas directamente desde el frontend, sin necesidad de acceso directo a la base de datos.

---

## Decisiones de diseño

| Decisión | Elección | Razón |
|---|---|---|
| Ubicación UI | Dentro de Inventario (tabs) | Mantiene dominio agrupado |
| Patrón tabs | 3 tabs: Prendas / Tipos / Tallas | Separación clara por entidad |
| Patrón formulario | Modal reutilizable | Consistente con estilo actual del proyecto |
| Ubicación endpoints | Extender `/api/inventario` | Consistente con GETs existentes |
| Componentes | Genéricos (`CatalogoTable`, `CatalogoModal`) | Evita duplicar código para tipos y tallas |

---

## Arquitectura Backend

### Opción elegida: Opción A — Extender router `/api/inventario`

### 1. Schemas

**`Backend/app/schemas/tipos_prendas.py`** — agregar:
```python
class TiposPrendasCreate(BaseModel):
    nombreTipo: str

class TiposPrendasUpdate(BaseModel):
    nombreTipo: str

class TiposPrendasResponse(BaseModel):
    TipoID: int
    nombreTipo: str
    model_config = ConfigDict(from_attributes=True)
```

**`Backend/app/schemas/tallas.py`** — espejo exacto con `TallaID` / `nombreTalla`.

### 2. Repositorio (archivo nuevo)

**`Backend/app/repositories/catalogos_repository.py`**

Métodos:
- `get_all_tipos(db)` → lista todos los tipos ordenados por nombre
- `create_tipo(db, nombre)` → inserta, valida unicidad
- `update_tipo(db, tipo_id, nombre)` → actualiza, valida unicidad y existencia
- `delete_tipo(db, tipo_id)` → verifica que no tenga inventario asociado antes de eliminar
- `get_all_tallas(db)` / `create_talla` / `update_talla` / `delete_talla` — mismo patrón

### 3. Servicio (archivo nuevo)

**`Backend/app/services/catalogos_service.py`**

Orquesta el repositorio y maneja las reglas de negocio:
- Nombre vacío o solo espacios → error 400
- Nombre duplicado (case-insensitive) → error 400
- ID inexistente en update/delete → error 404
- Eliminar con prendas vinculadas → error 400

### 4. Endpoints — ampliar existente

**`Backend/app/api/v1/endpoints/inventario.py`** — agregar 6 rutas:

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/inventario/tipos` | Crear tipo de prenda |
| `PUT` | `/api/inventario/tipos/{tipo_id}` | Editar tipo de prenda |
| `DELETE` | `/api/inventario/tipos/{tipo_id}` | Eliminar tipo de prenda |
| `POST` | `/api/inventario/tallas` | Crear talla |
| `PUT` | `/api/inventario/tallas/{talla_id}` | Editar talla |
| `DELETE` | `/api/inventario/tallas/{talla_id}` | Eliminar talla |

Todos requieren autenticación (`get_current_user`). Los dos GET existentes no cambian.

---

## Arquitectura Frontend

### 1. Servicio (archivo nuevo)

**`Frontend/src/services/catalogosService.js`**

```javascript
getTipos()
createTipo(nombre)
updateTipo(id, nombre)
deleteTipo(id)
getTallas()
createTalla(nombre)
updateTalla(id, nombre)
deleteTalla(id)
```

### 2. Componentes nuevos

Ubicación: `Frontend/src/components/inventory/`

| Componente | Responsabilidad |
|---|---|
| `CatalogoTable.jsx` | Tabla genérica: columna Nombre + botones Editar/Eliminar por fila |
| `CatalogoModal.jsx` | Modal genérico: campo Nombre, validación inline, botones Cancelar/Guardar |
| `ConfirmDeleteModal.jsx` | Modal de confirmación antes de eliminar (reutilizable en el proyecto) |

`CatalogoTable` y `CatalogoModal` son genéricos — reciben props (`titulo`, `items`, `onSave`, `onDelete`, `loading`) y sirven para ambas entidades.

### 3. Página `Inventory.jsx` — refactorizar

- Agregar sistema de tabs con estado `activeTab` (valores: `'prendas'`, `'tipos'`, `'tallas'`).
- Tab **Prendas**: tabla actual. Se corrige para mostrar nombre resuelto de tipo y talla (lookup map construido al cargar la página) en lugar del ID numérico.
- Tab **Tipos de Prenda**: `CatalogoTable` + botón "Agregar Tipo" → abre `CatalogoModal` en modo crear.
- Tab **Tallas**: idéntico en estructura.

---

## Flujo de datos

### Crear / Editar
```
Click "Agregar" / "Editar"
  → Abrir CatalogoModal (vacío o pre-cargado)
    → Usuario ingresa nombre
      → Validación cliente (campo vacío)
        → catalogosService.createTipo(nombre) / updateTipo(id, nombre)
          → POST / PUT /api/inventario/tipos
            → 201 OK: cerrar modal + refetch lista
            → 400 nombre duplicado: mostrar error inline en modal
```

### Eliminar
```
Click "Eliminar"
  → Abrir ConfirmDeleteModal
    → Usuario confirma
      → catalogosService.deleteTipo(id)
        → DELETE /api/inventario/tipos/{id}
          → 200 OK: refetch lista
          → 400 tiene prendas: mostrar error en modal (no cerrar)
          → 404: mostrar error
```

---

## Manejo de errores

### Backend — respuestas HTTP

| Situación | HTTP | Mensaje |
|---|---|---|
| Nombre duplicado | 400 | `"Ya existe un tipo con ese nombre"` |
| Eliminar con prendas asociadas | 400 | `"No se puede eliminar: tiene prendas vinculadas"` |
| ID no encontrado (PUT/DELETE) | 404 | `"Tipo/Talla no encontrado"` |
| Éxito creación | 201 | Objeto creado |
| Éxito update/delete | 200 | Objeto / mensaje confirmación |

### Frontend — feedback al usuario

- Validación de campo vacío: **inline en modal**, antes de llamar al API.
- Errores del servidor (400/404): **mensaje de error dentro del modal**, no se cierra.
- Éxito: **cierre automático del modal** + refresco de tabla.
- Botón "Guardar" **deshabilitado mientras la petición está en vuelo** (evita doble submit).

---

## Archivos a crear / modificar

### Nuevos
- `Backend/app/repositories/catalogos_repository.py`
- `Backend/app/services/catalogos_service.py`
- `Frontend/src/services/catalogosService.js`
- `Frontend/src/components/inventory/CatalogoTable.jsx`
- `Frontend/src/components/inventory/CatalogoModal.jsx`
- `Frontend/src/components/inventory/ConfirmDeleteModal.jsx`

### Modificados
- `Backend/app/schemas/tipos_prendas.py` — agregar Create/Update/Response
- `Backend/app/schemas/tallas.py` — agregar Create/Update/Response
- `Backend/app/api/v1/endpoints/inventario.py` — agregar 6 rutas CRUD
- `Frontend/src/pages/Inventory.jsx` — refactorizar con tabs + fix nombres

---

## Fuera de alcance (este sprint)

- Vista de "status de inventario" (mencionada en el commit `2d1379f`) — tarea separada
- Gestión de inventario individual (crear/editar prendas) — tarea separada
- Roles: solo admin puede gestionar catálogos (ya cubierto por `get_current_user`)
