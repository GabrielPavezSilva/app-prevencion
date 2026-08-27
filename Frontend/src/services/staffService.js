import { apiClient } from './api';

/**
 * Personal (solo lectura): la fuente de verdad es la base de RRHH y los datos
 * entran por el sync programado, que corre fuera de la API. No hay CRUD desde
 * la aplicación ni forma de disparar el sync desde acá.
 */

/**
 * Lista el personal. Por defecto solo activos.
 * @param {Object} filters - { search, incluirInactivos }
 * @returns {Promise<Array>} Lista plana de empleados
 */
export const getEmployees = async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.incluirInactivos) params.append('incluir_inactivos', 'true');
    const qs = params.toString();
    return apiClient.get(`/personal/todos${qs ? `?${qs}` : ''}`);
};

/**
 * Busca empleados por nombre o RUT.
 * @param {string} searchTerm
 */
export const searchEmployees = async (searchTerm) => {
    return getEmployees({ search: searchTerm });
};

export const getPersonalByRut = async (rut) => {
    return apiClient.get(`/personal/${encodeURIComponent(rut)}`);
};

/** Fecha de la última sincronización con RRHH. */
export const getEstadoSync = async () => {
    return apiClient.get('/personal/sync/estado');
};
