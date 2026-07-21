import { apiClient } from './api';

// ── Tipos de Prenda ───────────────────────────────────────────────────────────

export const getTipos = () => apiClient.get('/inventario/tipos');

export const createTipo = (nombreTipo) =>
    apiClient.post('/inventario/tipos', { nombreTipo });

export const updateTipo = (tipoId, nombreTipo) =>
    apiClient.put(`/inventario/tipos/${tipoId}`, { nombreTipo });

export const deleteTipo = (tipoId) =>
    apiClient.delete(`/inventario/tipos/${tipoId}`);

// ── Tallas ────────────────────────────────────────────────────────────────────

export const getTallas = () => apiClient.get('/inventario/tallas');

export const createTalla = (nombreTalla) =>
    apiClient.post('/inventario/tallas', { nombreTalla });

export const updateTalla = (tallaId, nombreTalla) =>
    apiClient.put(`/inventario/tallas/${tallaId}`, { nombreTalla });

export const deleteTalla = (tallaId) =>
    apiClient.delete(`/inventario/tallas/${tallaId}`);

// ── Secciones ─────────────────────────────────────────────────────────────────

export const getSecciones = () => apiClient.get('/inventario/secciones');

export const createSeccion = (nombreSeccion) =>
    apiClient.post('/inventario/secciones', { nombreSeccion });

export const updateSeccion = (seccionId, nombreSeccion) =>
    apiClient.put(`/inventario/secciones/${seccionId}`, { nombreSeccion });

export const deleteSeccion = (seccionId) =>
    apiClient.delete(`/inventario/secciones/${seccionId}`);

// ── Temporadas ────────────────────────────────────────────────────────────────

export const getTemporadas = () => apiClient.get('/inventario/temporadas');

export const createTemporada = (nombreTemporada) =>
    apiClient.post('/inventario/temporadas', { nombreTemporada });

export const updateTemporada = (temporadaId, nombreTemporada) =>
    apiClient.put(`/inventario/temporadas/${temporadaId}`, { nombreTemporada });

export const deleteTemporada = (temporadaId) =>
    apiClient.delete(`/inventario/temporadas/${temporadaId}`);
