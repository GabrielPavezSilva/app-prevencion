# Diseño: Modal de Prendas Activas en Personal (reemplaza Devoluciones)

**Fecha:** 2026-04-28

---

## Objetivo

Integrar la gestión de devoluciones dentro del módulo Personal. El badge de "Prendas Activas" se vuelve clickeable y abre un modal para ver y procesar devoluciones. El módulo Devoluciones se elimina del sidebar y sus rutas se remueven de App.jsx.

## Backend

Sin cambios. Los endpoints existentes ya cubren todo:
- `GET /api/returns/employees/{rut}/items` → prendas activas del trabajador
- `POST /api/returns/process` → registrar devolución de SKUs seleccionados

## Componentes a crear

### `PrendasModal.jsx`

Modal overlay (fixed, backdrop oscuro) con:
- **Header**: nombre + RUT del trabajador, badge con total prendas, botón ×
- **Tabla**: SKU | Tipo / Talla | Fecha asignación | Devolver (checkbox)
- **Footer**: resumen "X de Y seleccionadas" + botones Cancelar / Procesar devolución
- **Estados**: loading (skeleton 3 filas), vacío, error (toast), éxito (toast + cierre + refresh)
- Ancho máximo 720px, alto máximo 80vh con scroll interno

## Componentes a modificar

| Archivo | Cambio |
|---------|--------|
| `EmployeeRow.jsx` | Badge prendas activas → `<button>` que llama `onVerPrendas(employee)` |
| `EmployeeTable.jsx` | Recibe y propaga prop `onVerPrendas` |
| `Staff.jsx` | Estado modal + fetch prendas + handler procesarDevolucion |
| `Sidebar.jsx` | Eliminar entrada "Devoluciones" |
| `App.jsx` | Eliminar rutas `/devoluciones` y `/devoluciones/:employeeId` |
