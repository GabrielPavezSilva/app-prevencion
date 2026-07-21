import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContextModel';
import { useTheme } from '../../context/ThemeContext';

const SunIcon = () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
);

const MoonIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
);

const navItems = [
    {
        path: '/',
        label: 'Tablero',
        modulo: 'dashboard',
        end: true,
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
            </svg>
        ),
    },
    {
        path: '/inventario',
        label: 'Inventario',
        modulo: 'inventario',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
        ),
    },
    {
        path: '/personal',
        label: 'Personal',
        modulo: 'personal',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
            </svg>
        ),
    },
    {
        path: '/reportes',
        label: 'Reportes',
        modulo: 'reportes',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
        ),
    },
    {
        path: '/configuracion',
        label: 'Configuración',
        modulo: 'configuracion',
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
            </svg>
        ),
    },
    {
        path: '/superadmin',
        label: 'Superadmin',
        modulo: 'superadmin',
        divider: true,
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
        ),
    },
];

const Sidebar = () => {
    const { user, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const navigate = useNavigate();

    const displayName = user?.username || 'Usuario';
    const initials = displayName.slice(0, 2).toUpperCase();

    const isAdmin = user?.role === 'admin';

    const visibleItems = isAdmin
        ? navItems
        : navItems.filter(item => user?.modulos?.includes(item.modulo));

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <aside style={{
            width: 240,
            minWidth: 240,
            background: 'var(--color-sidebar)',
            borderRight: '1px solid var(--color-card-border)',
            display: 'flex',
            flexDirection: 'column',
            height: '100vh',
            position: 'sticky',
            top: 0,
            overflow: 'hidden',
        }}>
            {/* Logo */}
            <div style={{
                padding: '24px 20px',
                borderBottom: '1px solid var(--color-card-border)',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
            }}>
                <div style={{
                    width: 38,
                    height: 38,
                    background: '#6366f1',
                    borderRadius: 10,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: 15,
                    color: '#fff',
                    flexShrink: 0,
                    letterSpacing: '-0.5px',
                }}>
                    UT
                </div>
                <div>
                    <p style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-text-primary)', lineHeight: 1.2 }}>
                        Prevención EPP
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Sistema de gestión</p>
                </div>
            </div>

            {/* Navigation */}
            <nav style={{ flex: 1, padding: '16px 12px', overflowY: 'auto' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {visibleItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.end ?? false}
                            style={({ isActive }) => ({
                                display: 'flex',
                                alignItems: 'center',
                                gap: 10,
                                padding: '9px 12px',
                                borderRadius: 8,
                                textDecoration: 'none',
                                fontSize: 14,
                                fontWeight: 500,
                                transition: 'all 0.15s ease',
                                background: isActive ? 'var(--color-accent)' : 'transparent',
                                color: isActive ? '#fff' : 'var(--color-text-secondary)',
                                ...(item.divider && {
                                    marginTop: 8,
                                    borderTop: '1px solid var(--color-card-border)',
                                    paddingTop: 16,
                                }),
                            })}
                        >
                            {({ isActive }) => (
                                <>
                                    <span style={{ opacity: isActive ? 1 : 0.7, display: 'flex' }}>
                                        {item.icon}
                                    </span>
                                    {item.label}
                                </>
                            )}
                        </NavLink>
                    ))}
                </div>
            </nav>

            {/* User section */}
            <div style={{ padding: '16px 12px', borderTop: '1px solid var(--color-card-border)' }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 10px',
                    borderRadius: 8,
                    marginBottom: 8,
                    background: 'var(--color-accent-light)',
                }}>
                    <div style={{
                        width: 34,
                        height: 34,
                        background: '#6366f1',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: 13,
                        color: '#fff',
                        flexShrink: 0,
                    }}>
                        {initials}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{
                            fontSize: 13,
                            fontWeight: 600,
                            color: 'var(--color-text-primary)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                        }}>
                            {displayName}
                        </p>
                        <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '1px 8px',
                            borderRadius: 999,
                            fontSize: 10,
                            fontWeight: 500,
                            background: isAdmin ? 'rgba(59,130,246,0.12)' : 'rgba(100,116,139,0.15)',
                            color: isAdmin ? '#3b82f6' : '#94a3b8',
                            border: isAdmin ? '1px solid rgba(59,130,246,0.25)' : '1px solid rgba(100,116,139,0.2)',
                        }}>
                            {user?.role ?? 'sin rol'}
                        </span>
                    </div>
                </div>

                <button
                    onClick={toggleTheme}
                    title={theme === 'light' ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro'}
                    style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '8px 10px',
                        background: 'transparent',
                        border: '1px solid var(--color-border)',
                        borderRadius: 8,
                        color: 'var(--color-text-muted)',
                        fontSize: 13,
                        fontFamily: 'var(--font-family)',
                        cursor: 'pointer',
                        transition: 'border-color 0.15s ease, color 0.15s ease',
                        marginBottom: 6,
                    }}
                    onMouseEnter={e => {
                        e.currentTarget.style.borderColor = '#6366f1';
                        e.currentTarget.style.color = '#6366f1';
                    }}
                    onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'var(--color-border)';
                        e.currentTarget.style.color = 'var(--color-text-muted)';
                    }}
                >
                    {theme === 'light' ? <MoonIcon /> : <SunIcon />}
                    {theme === 'light' ? 'Modo oscuro' : 'Modo claro'}
                </button>

                <button
                    onClick={handleLogout}
                    style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '8px 10px',
                        background: 'transparent',
                        border: '1px solid var(--color-border)',
                        borderRadius: 8,
                        color: 'var(--color-text-muted)',
                        fontSize: 13,
                        fontFamily: 'var(--font-family)',
                        cursor: 'pointer',
                        transition: 'border-color 0.15s ease, color 0.15s ease',
                    }}
                    onMouseEnter={e => {
                        e.currentTarget.style.borderColor = '#ef4444';
                        e.currentTarget.style.color = '#ef4444';
                    }}
                    onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'var(--color-border)';
                        e.currentTarget.style.color = 'var(--color-text-muted)';
                    }}
                >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                    </svg>
                    Cerrar sesión
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
