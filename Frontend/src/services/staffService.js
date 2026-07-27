import { apiClient } from './api';

/**
 * Personal (solo lectura): la fuente de verdad es la base de RRHH y los datos
 * entran por el sync (POST /personal/sync). No hay CRUD desde la aplicación.
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

/**
 * Dispara la sincronización con RRHH. Corre sola a diario; esto es para el
 * alta del día.
 * @param {boolean} dryRun - calcula el resultado sin escribir
 * @returns {Promise<Object>} Resumen { creados, actualizados, desactivados, errores… }
 */
export const sincronizarPersonal = async (dryRun = false) => {
    return apiClient.post(`/personal/sync${dryRun ? '?dry_run=true' : ''}`);
};

/** Fecha de la última sincronización con RRHH. */
export const getEstadoSync = async () => {
    return apiClient.get('/personal/sync/estado');
};
