import { apiClient } from './api';

/**
 * Reportes EPP (Fase 5).
 *
 * Cada reporte tiene dos rutas en el backend que comparten la misma query: la
 * JSON alimenta la tabla en pantalla y la `.xlsx` la descarga. Por eso no hay
 * transformación de datos acá — lo que se ve es lo que se exporta.
 */

const qs = (filtros = {}) => {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') params.append(k, v);
    });
    const s = params.toString();
    return s ? `?${s}` : '';
};

// ── Consultas (tabla en pantalla) ────────────────────────────────────────────

export const getTrazabilidad = (filtros) => apiClient.get(`/reportes/entregas${qs(filtros)}`);

export const getEppVigentes = (filtros) => apiClient.get(`/reportes/epp-vigentes${qs(filtros)}`);

export const getStock = (filtros) => apiClient.get(`/reportes/stock${qs(filtros)}`);

// ── Catálogos para los filtros ───────────────────────────────────────────────

export const getAreas = (empresa_id) => apiClient.get(`/personal/areas${qs({ empresa_id })}`);

export const getSubareas = (area_id) => apiClient.get(`/personal/subareas${qs({ area_id })}`);

export const getEmpresas = () => apiClient.get('/inventario/empresas');

// ── Descarga de Excel ────────────────────────────────────────────────────────

/**
 * Descarga el Excel del reporte. Se hace por fetch y no con un <a href> para
 * poder avisarle al usuario si falla: un href fallido descarga un archivo con
 * el JSON del error adentro, sin ninguna señal de que algo salió mal.
 */
const descargar = async (ruta, filtros, nombreBase) => {
    const blob = await apiClient.get(`${ruta}${qs(filtros)}`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${nombreBase}_${new Date().toISOString().slice(0, 10)}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
};

export const descargarTrazabilidad = (filtros) =>
    descargar('/reportes/entregas.xlsx', filtros, 'trazabilidad_entregas');

export const descargarEppVigentes = (filtros) =>
    descargar('/reportes/epp-vigentes.xlsx', filtros, 'epp_vigentes');

export const descargarStock = (filtros) =>
    descargar('/reportes/stock.xlsx', filtros, 'stock_epp');
