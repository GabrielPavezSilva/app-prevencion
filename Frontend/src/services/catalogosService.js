import { apiClient } from './api';

// ── Tallas ────────────────────────────────────────────────────────────────────
// Único catálogo vivo del módulo. Tipos de prenda, secciones y temporadas eran
// del dominio de lavandería: los endpoints ya no existen en el backend.

export const getTallas = () => apiClient.get('/inventario/tallas');

export const createTalla = (nombreTalla) =>
    apiClient.post('/inventario/tallas', { nombreTalla });

export const updateTalla = (tallaId, nombreTalla) =>
    apiClient.put(`/inventario/tallas/${tallaId}`, { nombreTalla });

export const deleteTalla = (tallaId) =>
    apiClient.delete(`/inventario/tallas/${tallaId}`);
