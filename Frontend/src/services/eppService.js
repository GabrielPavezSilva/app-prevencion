import { apiClient } from './api';

// Construye query string a partir de params no vacíos.
const qs = (params = {}) => {
    const q = Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    return q ? `?${q}` : '';
};

// ── Categorías ──────────────────────────────────────────────────────────────
export const getCategorias = () => apiClient.get('/epp/categorias');
export const createCategoria = (nombre_categoria) =>
    apiClient.post('/epp/categorias', { nombre_categoria });
export const updateCategoria = (id, nombre_categoria) =>
    apiClient.put(`/epp/categorias/${id}`, { nombre_categoria });
export const deleteCategoria = (id) => apiClient.delete(`/epp/categorias/${id}`);

// ── Productos ───────────────────────────────────────────────────────────────
export const getProductos = (params = {}) => apiClient.get(`/epp/productos${qs(params)}`);
export const getProducto = (id) => apiClient.get(`/epp/productos/${id}`);
export const createProducto = (data) => apiClient.post('/epp/productos', data);
export const updateProducto = (id, data) => apiClient.put(`/epp/productos/${id}`, data);
export const deleteProducto = (id) => apiClient.delete(`/epp/productos/${id}`);

// ── Recintos ────────────────────────────────────────────────────────────────
// Catálogo de solo lectura: los recintos se siembran, no se administran desde
// la app (ver seed_recintos.py).
export const getRecintos = () => apiClient.get('/epp/recintos');

// ── Stock y movimientos ─────────────────────────────────────────────────────
// Sin `recinto_id` el listado trae los tres recintos, a propósito: saber dónde
// hay existencias es para lo que sirve.
export const getStock = (params = {}) => apiClient.get(`/epp/stock${qs(params)}`);
export const ajustarStock = (data) => apiClient.post('/epp/stock/ajuste', data);
export const getMovimientos = (params = {}) => apiClient.get(`/epp/movimientos${qs(params)}`);
