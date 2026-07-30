import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { AuthContext } from './AuthContextModel';
import { login as authLogin, logout as authLogout } from '../services/authService';
import { setUnauthorizedHandler, SESION_EXPIRADA } from '../services/api';

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Restaurar sesión desde localStorage (solo datos de usuario, no token)
    useEffect(() => {
        const stored = localStorage.getItem('user');
        if (stored) {
            try {
                setUser(JSON.parse(stored));
            } catch {
                localStorage.removeItem('user');
            }
        }
        setLoading(false);
    }, []);

    // Cuando el backend responde 401, apiClient ya limpió localStorage: acá solo
    // bajamos el usuario del estado para que ProtectedRoute redirija a /login.
    useEffect(() => {
        setUnauthorizedHandler(() => {
            setUser(null);
            toast.error(SESION_EXPIRADA);
        });
        return () => setUnauthorizedHandler(null);
    }, []);

    const login = async (username, password) => {
        setError(null);
        setLoading(true);

        try {
            const response = await authLogin(username, password);
            // Token va en cookie httpOnly — no lo tocamos
            localStorage.setItem('user', JSON.stringify(response.user));
            setUser(response.user);
            return response.user;
        } catch (err) {
            setError(err.message || 'Error al iniciar sesión');
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        setLoading(true);
        try {
            await authLogout();
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            localStorage.removeItem('user');
            setUser(null);
            setLoading(false);
        }
    };

    const isAdmin = () => user?.role === 'admin';
    const isWorker = () => user?.role === 'worker_recepcion' || user?.role === 'worker_asignacion';
    const isAuthenticated = () => !!user;

    const value = {
        user,
        loading,
        error,
        login,
        logout,
        isAdmin,
        isWorker,
        isAuthenticated
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
