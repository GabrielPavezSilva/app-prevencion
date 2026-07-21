export const MODULE_ROUTES = {
    dashboard: '/',
    inventario: '/inventario',
    entregas: '/entregas',
    personal: '/personal',
    reportes: '/reportes',
    configuracion: '/configuracion',
    superadmin: '/superadmin',
};

/**
 * Devuelve la ruta home para un usuario según su rol y módulos.
 * - admin → siempre '/'
 * - otros → primera ruta que coincida con sus módulos asignados
 * - sin módulos → '/sin-acceso'
 */
export const getHomeForUser = (user) => {
    if (!user) return '/login';
    if (user.role === 'admin') return '/';
    const firstRoute = (user.modulos ?? [])
        .map((m) => MODULE_ROUTES[m])
        .find((r) => r != null);
    return firstRoute ?? '/sin-acceso';
};
