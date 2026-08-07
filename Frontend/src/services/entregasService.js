import { apiClient } from './api';

const qs = (params = {}) => {
    const q = Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    return q ? `?${q}` : '';
};

// Historial de entregas con filtros (rut, motivo, area_id, desde, hasta)
export const getEntregas = (params = {}) => apiClient.get(`/entregas/${qs(params)}`);

// Carrito de entregas (motivos NUEVA/PERDIDA) -> descuenta stock
export const crearEntregas = (payload) => apiClient.post('/entregas/', payload);

// Sustitución por daño (motivo DANO)
export const crearSustitucion = (payload) => apiClient.post('/entregas/sustitucion', payload);

// EPP vigentes de un trabajador
export const getVigentes = (rut) => apiClient.get(`/entregas/trabajador/${encodeURIComponent(rut)}`);
