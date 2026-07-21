import { apiClient } from './api';

/**
 * Get employees with pending returns
 * @param {Object} filters - Filter options { status, department }
 * @returns {Promise<Array>} Array of employees with pending returns
 */
export const getEmployeesWithReturns = async (filters = {}) => {
    const params = new URLSearchParams();

    if (filters.status) {
        params.append('status', filters.status);
    }
    if (filters.department && filters.department !== 'all') {
        params.append('department', filters.department);
    }

    const queryString = params.toString();
    const url = queryString ? `/returns/employees?${queryString}` : '/returns/employees';

    return apiClient.get(url);
};

/**
 * Get employee return details with items
 * @param {string} employeeId - Employee ID
 * @returns {Promise<Object>} Employee details with items
 */
export const getEmployeeReturnItems = async (employeeId) => {
    return apiClient.get(`/returns/employees/${encodeURIComponent(employeeId)}/items`);
};

/**
 * Update return quantity for an item
 * @param {number} itemId - Item ID
 * @param {number} quantity - Quantity returned
 * @returns {Promise<Object>} Updated item
 */
export const updateReturnQuantity = async (itemId, quantity) => {
    return apiClient.put(`/returns/items/${itemId}/quantity`, { quantity });
};

/**
 * Update item status
 * @param {number} itemId - Item ID
 * @param {string} status - Item status
 * @returns {Promise<Object>} Updated item
 */
export const updateItemStatus = async (itemId, status) => {
    return apiClient.put(`/returns/items/${itemId}/status`, { status });
};

/**
 * Process return transaction
 * @param {string} employeeId - Employee ID
 * @param {Array} items - Array of items with quantities and statuses
 * @param {string} notes - Additional notes
 * @returns {Promise<Object>} Processing result
 */
export const processReturn = async (employeeId, items, notes) => {
    return apiClient.post('/returns/process', { employeeId, items, notes });
};

/**
 * Get return history for employee
 * @param {string} employeeId - Employee ID
 * @returns {Promise<Array>} Array of previous returns
 */
export const getReturnHistory = async (employeeId) => {
    return apiClient.get(`/returns/employees/${encodeURIComponent(employeeId)}/history`);
};

/**
 * Update employee return status
 * @param {string} employeeId - Employee ID
 * @param {string} status - New status
 * @returns {Promise<Object>} Updated employee
 */
export const updateEmployeeReturnStatus = async (employeeId, status) => {
    // This is handled by processReturn in the backend
    return { success: true, employeeId, status };
};

