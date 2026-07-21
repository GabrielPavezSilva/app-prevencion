# Diseño: Sistema de temas global + Rediseño páginas worker

**Fecha:** 2026-04-19  
**Rama:** ajuste-diseno  
**Estado:** Aprobado

---

## Contexto

Las páginas `RecepcionDashboard` y `AsignacionDashboard` se usan en computadores físicos en la lavandería. Las operarias necesitan una interfaz de alto contraste (fondo blanco) que les permita distinguir rápidamente en qué portal están. El panel admin mantiene el tema oscuro como default pero puede cambiar. Se agrega un sistema de toggle global claro/oscuro para toda la app.

---

## Decisiones de diseño

| Pregunta | Decisión |
|----------|----------|
| ¿El tema afecta solo worker o toda la app? | Toda la app — toggle global |
| ¿Qué tema por defecto? | Claro (light) en primera visita |
| ¿Cómo se persiste? | `localStorage` con clave `app-theme` |
| ¿Cómo se aplica al DOM? | `data-theme="light|dark"` en `<html>` |
| ¿Las páginas worker siempre son claras? | No — respetan el tema global |
| ¿Diferencia visual entre RecepcionDashboard y AsignacionDashboard? | Sí — color de acento diferente por página |
| ¿Tamaño de botones de acción? | Doble del tamaño actual (~80-84px de alto) |

---

## Sistema de tema global

### ThemeContext
- Estado: `theme: 'light' | 'dark'`
- Default: `'light'` (primera visita, si no hay valor en localStorage)
- Al cambiar tema: `document.documentElement.setAttribute('data-theme', theme)`
- Hook: `useTheme()` → `{ theme, toggleTheme }`

### CSS variables de tema claro
Bloque `[data-theme="light"]` en `index.css` que redefine:

| Variable | Valor oscuro | Valor claro |
|----------|-------------|-------------|
| `--color-bg` | `#0f1117` | `#f8fafc` |
| `--color-card` | `#1e2535` | `#ffffff` |
| `--color-card-border` | `#2a3147` | `#e2e8f0` |
| `--color-input-bg` | `#141926` | `#f1f5f9` |
| `--color-border` | `#2a3147` | `#e2e8f0` |
| `--color-text-primary` | `#f1f5f9` | `#0f172a` |
| `--color-text-secondary` | `#94a3b8` | `#475569` |
| `--color-text-muted` | `#64748b` | `#94a3b8` |
| `--color-sidebar` | `#1a1f2e` | `#ffffff` |
| `--color-primary` | `#1a1f2e` | `#f1f5f9` |
| `--color-accent-light` | `rgba(99,102,241,0.12)` | `rgba(99,102,241,0.10)` |

---

## Acento por página worker

Cada dashboard pasa prop `accentClass` a `WorkerLayout`:

| Dashboard | `accentClass` | Color acento | Significado visual |
|-----------|--------------|--------------|-------------------|
| `RecepcionDashboard` | `accent-recepcion` | `#10b981` (esmeralda) | Devolver = completar |
| `AsignacionDashboard` | `accent-asignacion` | `#6366f1` (índigo) | Asignar = acción nueva |

El `WorkerLayout` aplica la clase al div raíz, que redefine `--color-accent` dentro de ese scope. El header muestra una **franja de 4px** en `--color-accent` como borde inferior — identificador visual desde lejos.

---

## Toggle de tema

- **Admin sidebar:** ícono sol/luna junto al logo o al pie del menú
- **Worker header:** ícono sol/luna entre buscador y avatar
- Ambos usan `useTheme()` del contexto

---

## Botones de acción — especificaciones

| Propiedad | Actual | Nuevo |
|-----------|--------|-------|
| Altura | ~42px | ~84px |
| Font size | 14px | 18px |
| Font weight | 600 | 700 |
| Ancho | variable | 100% del contenedor |
| Texto | mezcla | TODO MAYÚSCULAS |
| Border radius | 10px | 12px |

Botones afectados: `RECIBIR PRENDAS`, `DETENER RECEPCIÓN`, `Identificar con Huella`, `Buscar`, `INICIAR ASIGNACIÓN`.

---

## Archivos modificados

| Archivo | Tipo | Cambio |
|---------|------|--------|
| `src/context/ThemeContext.jsx` | Nuevo | Provider + hook `useTheme` |
| `src/styles/index.css` | Modificado | Agrega bloque `[data-theme="light"]` |
| `src/main.jsx` | Modificado | Envuelve app con `ThemeProvider` |
| `src/components/layout/Sidebar.jsx` | Modificado | Botón toggle sol/luna |
| `src/components/worker/WorkerLayout.jsx` | Modificado | Prop `accentClass` + toggle + franja color |
| `src/components/worker/WorkerTheme.css` | Nuevo | Clases `.accent-recepcion` / `.accent-asignacion` |
| `src/components/worker/ScanningPanel.css` | Modificado | Botones ×2 tamaño |
| `src/pages/RecepcionDashboard.jsx` | Modificado | Pasa `accentClass="accent-recepcion"` |
| `src/pages/AsignacionDashboard.jsx` | Modificado | Pasa `accentClass="accent-asignacion"` |

---

## Lo que NO cambia

- Lógica de negocio en ScanningPanel (loops RFID, biometría, registrarLectura)
- Estructura de componentes WorkerProfile, ScanHistory, WardrobeVisualizer
- APIs y servicios backend
- Rutas y protección por rol (definidas en plan anterior)
- CSS del panel admin (solo se agrega el bloque light, no se modifica el oscuro)
