import { apiClient } from './api';

/**
 * @param {string} username
 * @param {string} contrasena
 * @returns {Promise<Object>} { token, user }
 */
export const login = async (username, contrasena) => {
    return apiClient.post('/auth/login', { username, contrasena });
};

export const logout = async () => {
    return apiClient.post('/auth/logout');
};
