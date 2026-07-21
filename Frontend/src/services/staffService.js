import { apiClient } from './api';

/**
 * Get employees with pagination and filters
 * @param {number} page - Page number (1-indexed)
 * @param {number} pageSize - Number of items per page
 * @param {Object} filters - Filter options { search, department }
 * @returns {Promise<Object>} Paginated employees response
 */
export const getEmployees = async (_page = 1, _pageSize = 5, filters = {}) => {
    // Backend nuevo usa /api/personal/todos y acepta param 'search'
    // Ignoramos page/pageSize por ahora si el backend no lo soporta en ese endpoint,
    // o asumimos que "todos" es todos. El backend implementado devuelve lista completa filtrada.
    
    const params = new URLSearchParams();
    if (filters.search) {
        params.append('search', filters.search);
    }
    
    return apiClient.get(`/personal/todos?${params.toString()}`);
};

/**
 * Search employees by term
 * @param {string} searchTerm - Search term
 * @param {number} page - Page number
 * @param {number} pageSize - Items per page
 * @returns {Promise<Object>} Search results
 */
export const searchEmployees = async (searchTerm, page = 1, pageSize = 5) => {
    return getEmployees(page, pageSize, { search: searchTerm });
};

export const getPersonalByRut = async (rut) => {
    return apiClient.get(`/personal/${encodeURIComponent(rut)}`);
};

/**
 * Get employee by ID
 * @param {string} id - Employee ID
 * @returns {Promise<Object>} Employee data
 */
export const getEmployeeById = async (id) => {
    return apiClient.get(`/staff/employees/${encodeURIComponent(id)}`);
};

/**
 * Create new employee
 * @param {Object} employeeData - Employee data
 * @returns {Promise<Object>} Created employee
 */
export const createEmployee = async (employeeData) => {
    return apiClient.post('/staff/employees', employeeData);
};

/**
 * Update employee
 * @param {string} id - Employee ID
 * @param {Object} employeeData - Updated data
 * @returns {Promise<Object>} Updated employee
 */
export const updateEmployee = async (id, employeeData) => {
    return apiClient.put(`/staff/employees/${encodeURIComponent(id)}`, employeeData);
};

/**
 * Delete employee
 * @param {string} id - Employee ID
 * @returns {Promise<Object>} Success response
 */
export const deleteEmployee = async (id) => {
    return apiClient.delete(`/staff/employees/${encodeURIComponent(id)}`);
};

/**
 * Get list of departments
 * @returns {Promise<Array>} Array of departments
 */
export const getDepartments = async () => {
    return apiClient.get('/staff/departments');
};

/**
 * Obtiene todas las asignaciones (para cruce con personal: N° prendas asignadas por RUT).
 * @returns {Promise<Array>} Lista de asignaciones con rut, fecha_devolucion, etc.
 */
export const getAsignaciones = async () => {
    return apiClient.get('/asignaciones/todas');
};

/**
 * Export employees data
 * @param {string} format - Export format (csv, excel, pdf)
 * @returns {Promise<Blob>} File blob
 */
export const exportEmployees = async (format = 'csv') => {
    // TODO: Implement export endpoint in backend
    console.log(`Exporting employees as ${format}...`);
    return { success: true, format };
};

