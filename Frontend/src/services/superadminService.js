import { apiClient } from './api';

const BASE = '/superadmin';

// ── Usuarios ──────────────────────────────────────────────────────────────────

export const getUsuarios = () => apiClient.get(`${BASE}/usuarios`);

export const createUsuario = (data) => apiClient.post(`${BASE}/usuarios`, data);

export const updateUsuario = (userId, data) =>
    apiClient.put(`${BASE}/usuarios/${userId}`, data);

export const resetPassword = (userId, nueva_contrasena) =>
    apiClient.put(`${BASE}/usuarios/${userId}/password`, { nueva_contrasena });

export const cambiarPasswordPropio = (contrasena_actual, nueva_contrasena) =>
    apiClient.put(`${BASE}/usuarios/me/password`, { contrasena_actual, nueva_contrasena });

// ── Roles ─────────────────────────────────────────────────────────────────────

export const getRoles = () => apiClient.get(`${BASE}/roles`);

export const createRol = (data) => apiClient.post(`${BASE}/roles`, data);

export const updateRol = (rolId, data) =>
    apiClient.put(`${BASE}/roles/${rolId}`, data);

export const deleteRol = (rolId) => apiClient.delete(`${BASE}/roles/${rolId}`);

// ── Módulos ───────────────────────────────────────────────────────────────────

export const getModulos = () => apiClient.get(`${BASE}/modulos`);
