# Diseño: Consolidación del Módulo de Inventario RFID
**Fecha:** 2026-02-21
**Estado:** Aprobado

---

## Objetivo

Integrar "Modo Inventario RFID" como una pestaña interna dentro de la página Inventario, elevando el estándar visual al estilo "Enterprise Dashboard" (sobrio, charcoal, índigo como acento).

---

## Archivos afectados

| Archivo | Cambio |
|---------|--------|
| `Frontend/src/styles/index.css` | Cambio de paleta: sidebar charcoal `#1e293b`, acento índigo `#6366f1`, rojo solo para marca/errores |
| `Frontend/src/components/layout/Sidebar.jsx` | Eliminar ítem "Modo Inventario" del menú |
| `Frontend/src/App.jsx` | Ruta `/inventario-rfid` → redirect a `/inventario` |
| `Frontend/src/pages/Inventory.jsx` | Añadir 4ª pestaña "Realizar Inventario", migrar alerts → toast, zebra rows |
| `Frontend/src/pages/Inventory.css` | Zebra rows, badges sin emoji, tabla enterprise |
| `Frontend/src/components/inventory/TabRealizarInventario.jsx` | **NUEVO** — lógica RFID polling + LED + summary panel |
| `Frontend/src/main.jsx` | Añadir `<Toaster />` de react-hot-toast |
| `Frontend/package.json` | Añadir dependencia `react-hot-toast` |

**Conservados sin cambio:** `InventoryMode.jsx`, `InventoryMode.css`.

---

## Paleta de Colores

```
--color-bg-sidebar:  #1e293b   (Charcoal Profundo — fondo sidebar)
--color-primary:     #1e293b   (referencia general a dark)
--color-accent:      #6366f1   (tabs activos, botones de acción, focus rings)
--color-brand:       #ef4444   (logo "Uniform Tracker" + indicador error RFID)
--color-bg-main:     #f5f5f5   (sin cambio)
```

---

## Navegación

- **Sidebar:** 5 ítems admin — Tablero, Inventario, Devoluciones, Reportes, Configuración.
- **Ruta `/inventario-rfid`:** redirige a `/inventario` (mantenida para compatibilidad).
- **`InventoryMode.jsx`:** sin tocar, sin entrada en sidebar.

---

## Estructura de Tabs en Inventory.jsx

```
[ Prendas ]  [ Tipos de Prenda ]  [ Tallas ]  [ Realizar Inventario ]
```

Tab activo: `border-bottom: 2px solid #6366f1`, color texto `#6366f1`.

---

## Componente TabRealizarInventario.jsx

### Props
```ts
{
  tipos: { TipoID, nombreTipo }[]
  tallas: { TallaID, nombreTalla }[]
  activo: boolean
}
```

### Ciclo de vida
```
activo=true  → checkReader() + checkEstadoSesion()
activo=false → si sesionActiva: detenerInventario() + stopPolling()
desmonte     → stopPolling()
```

### Estados internos
- `readerStatus: 'connected' | 'disconnected' | 'error'`
- `sesionActiva: boolean`
- `tipoId, tallaId: string`
- `prendasLeidas: { sku, epc, tipo_prenda, talla, hora }[]`
- `duplicados: number`
- `resumen: { cantidad_registrada, duplicadas } | null`  ← nuevo

### Flujo UI

```
[Estado Inactivo]
Panel: LED + selectores + botón "Iniciar Inventario"

[Sesión Activa]
Panel: LED pulsante + labels fijos + botón "Detener" (gris oscuro)
Tabla de prendas leídas (nuevas filas animadas arriba)

[Post-Detener — Resumen]
Tarjeta de resumen:
  ✓ {cantidad_registrada} prendas registradas
  ○ {duplicadas} duplicados ignorados
  [Nuevo Inventario]   ← limpia estado
toast.success('Inventario finalizado')
```

### Indicador LED
```
● Verde (#22c55e)  — status.conectado = true
● Gris  (#94a3b8)  — desconectado (clickeable → conectar)
● Rojo  (#ef4444)  — hardware_error
```

---

## Tablas Enterprise (todas las pestañas)

- **Zebra:** filas pares `background: #f8fafc`.
- **Cabecera:** `background: #f8fafc`, color `#64748b`, uppercase, `letter-spacing: 0.06em`.
- **Bordes:** `border-bottom: 1px solid #f1f5f9` (más fino que antes).
- **Badges de estado:**
  - Disponible → badge verde, texto "Disponible" (sin emoji).
  - Asignado → badge slate `#64748b bg`, texto "Asignado".
- **Sin `alert()`:** todos migrados a `toast.success()` / `toast.error()`.

---

## react-hot-toast

```jsx
// main.jsx
import { Toaster } from 'react-hot-toast';
// dentro de <App>:
<Toaster position="bottom-right" toastOptions={{ duration: 3500 }} />
```

---

## Decisiones descartadas

- **React.lazy (Opción C):** sobreingeniería para ~150 líneas.
- **Toast custom:** react-hot-toast elegido por ser ligero y sin CSS extra.
- **Eliminar InventoryMode.jsx:** mantenido como respaldo.
