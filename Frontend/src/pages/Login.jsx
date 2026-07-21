import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContextModel';
import { getHomeForUser } from '../utils/routes';
import toast from 'react-hot-toast';
import './Login.css';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!username || !password) {
            toast.error('Completa todos los campos');
            return;
        }
        setLoading(true);
        try {
            const user = await login(username, password);
            navigate(getHomeForUser(user));
        } catch (err) {
            toast.error(err.message || 'Credenciales incorrectas');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--color-bg)',
            display: 'flex',
            alignItems: 'stretch',
        }}>
            {/* Left panel */}
            <div
                style={{
                    flex: 1,
                    // ponytail: panel oscuro fijo en ambos temas — el texto es blanco fijo.
                    // NO usar --color-card: es #fff en tema claro => texto blanco invisible.
                    background: 'linear-gradient(155deg, #0f3d38 0%, #0a2624 100%)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    justifyContent: 'center',
                    padding: '60px',
                    position: 'relative',
                    overflow: 'hidden',
                }}
                className="login-left-panel"
            >
                {/* Decorative circles */}
                <div style={{
                    position: 'absolute', top: -80, right: -80,
                    width: 320, height: 320, borderRadius: '50%',
                    border: '1px solid rgba(45,212,191,0.20)',
                    pointerEvents: 'none',
                }} />
                <div style={{
                    position: 'absolute', top: -40, right: -40,
                    width: 200, height: 200, borderRadius: '50%',
                    border: '1px solid rgba(45,212,191,0.14)',
                    pointerEvents: 'none',
                }} />
                <div style={{
                    position: 'absolute', bottom: -100, left: -60,
                    width: 360, height: 360, borderRadius: '50%',
                    border: '1px solid rgba(45,212,191,0.10)',
                    pointerEvents: 'none',
                }} />

                {/* Logo */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 48 }}>
                    <div style={{
                        width: 48, height: 48,
                        background: 'var(--color-accent)',
                        borderRadius: 14,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 800, fontSize: 18,
                        color: '#fff', letterSpacing: '-0.5px',
                    }}>
                        UT
                    </div>
                    <div>
                        <p style={{ fontWeight: 700, fontSize: 18, color: '#fff' }}>
                            Prevención EPP
                        </p>
                        <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>Gestión de EPP y prevención de riesgos</p>
                    </div>
                </div>

                {/* Copy de marca — no es encabezado semántico; el h1 es "Iniciar sesión" */}
                <p style={{
                    fontSize: 44, fontWeight: 800,
                    color: '#fff', lineHeight: 1.15,
                    marginBottom: 20, maxWidth: 420,
                }}>
                    Sistema de gestión de indumentaria industrial
                </p>
                <p style={{
                    fontSize: 16, color: 'rgba(255,255,255,0.55)',
                    maxWidth: 360, lineHeight: 1.7,
                }}>
                    Control centralizado de inventario, asignaciones y devoluciones de prendas de trabajo para tu empresa.
                </p>

                <div style={{ marginTop: 48, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {['Control de inventario en tiempo real', 'Gestión de asignaciones y devoluciones', 'Reportes exportables a Excel'].map((feat) => (
                        <div key={feat} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div style={{
                                width: 20, height: 20,
                                background: 'rgba(34,197,94,0.15)',
                                border: '1px solid rgba(34,197,94,0.3)',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                flexShrink: 0,
                            }}>
                                <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                                    <path d="M2 6l3 3 5-5" stroke="#22c55e" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </div>
                            <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.65)' }}>{feat}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right panel */}
            <main className="login-right-panel">
                <div className="login-card-enter" style={{ width: '100%', maxWidth: 360 }}>
                    <div style={{ marginBottom: 32 }}>
                        <h1 style={{
                            fontSize: 24, fontWeight: 700,
                            color: 'var(--color-text-primary)',
                            marginBottom: 6,
                        }}>
                            Iniciar sesión
                        </h1>
                        <p style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>
                            Ingresa tus credenciales para continuar
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                        <div className="form-group">
                            <label className="form-label" htmlFor="login-username">Usuario</label>
                            <input
                                id="login-username"
                                type="text"
                                className="form-input"
                                placeholder="Ingrese su usuario"
                                value={username}
                                onChange={e => setUsername(e.target.value)}
                                disabled={loading}
                                autoComplete="username"
                                autoFocus
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label" htmlFor="login-password">Contraseña</label>
                            <input
                                id="login-password"
                                type="password"
                                className="form-input"
                                placeholder="••••••••"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                disabled={loading}
                                autoComplete="current-password"
                            />
                        </div>

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={loading}
                            style={{ width: '100%', justifyContent: 'center', padding: '11px 20px', marginTop: 4 }}
                        >
                            {loading ? (
                                <>
                                    <div className="spinner" />
                                    Iniciando sesión...
                                </>
                            ) : 'Iniciar sesión'}
                        </button>
                    </form>

                </div>
            </main>
        </div>
    );
};

export default Login;
