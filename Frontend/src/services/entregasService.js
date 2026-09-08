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

// Abre en una pestaña nueva el PDF del acta firmada que quedó guardada.
// Va por apiClient y no por un <a href> porque la sesión viaja en la cookie y
// el endpoint exige autenticación.
const abrirPdf = async (ruta) => {
    const blob = await apiClient.get(ruta, { responseType: 'blob' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener');
    // ponytail: se revoca a los 60 s en vez de rastrear el cierre de la pestaña.
    setTimeout(() => URL.revokeObjectURL(url), 60000);
};

export const abrirActa = (actaId) => abrirPdf(`/entregas/acta/${actaId}`);

// Documento maestro del trabajador: todas sus entregas firmadas en un PDF.
// Se genera en el servidor a partir de la base, así nunca pierde registros.
export const abrirActaMaestra = (rut) =>
    abrirPdf(`/entregas/acta-maestra/${encodeURIComponent(rut)}`);
