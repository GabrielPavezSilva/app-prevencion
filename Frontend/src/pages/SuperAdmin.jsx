import { useState, useEffect, useCallback, useRef } from 'react';
import toast from 'react-hot-toast';
import {
    getUsuarios, createUsuario, updateUsuario, resetPassword,
    getRoles, createRol, updateRol, deleteRol, getModulos,
} from '../services/superadminService';
import db from '../db/localDb';
import { reintentarErrores, limpiarSincronizados, procesarCola } from '../sync/syncManager';

// ── Helpers ────────────────────────────────────────────────────────────────────

const MODULO_LABELS = {
    dashboard: 'Tablero',
    inventario: 'Inventario',
    personal: 'Personal',
    devoluciones: 'Devoluciones',
    reportes: 'Reportes',
    configuracion: 'Configuración',
    worker_recepcion: 'Recepción',
    worker_asignacion: 'Asignación',
    superadmin: 'Superadmin',
};

const label = (nombre) => MODULO_LABELS[nombre] ?? nombre;

// ── Estilos compartidos ────────────────────────────────────────────────────────

const card = {
    background: 'var(--color-card)',
    border: '1px solid var(--color-card-border)',
    borderRadius: 12,
    padding: 24,
};

const btnPrimary = {
    background: 'var(--color-accent)',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
};

const btnGhost = {
    background: 'transparent',
    color: 'var(--color-text-muted)',
    border: '1px solid var(--color-card-border)',
    borderRadius: 8,
    padding: '7px 14px',
    fontSize: 13,
    cursor: 'pointer',
};

const inputStyle = {
    width: '100%',
    padding: '9px 12px',
    background: 'var(--color-input-bg)',
    border: '1px solid var(--color-card-border)',
    borderRadius: 8,
    color: 'var(--color-text-primary)',
    fontSize: 14,
    boxSizing: 'border-box',
    fontFamily: 'var(--font-family)',
};

const labelStyle = {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--color-text-muted)',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const thStyle = {
    padding: '10px 14px',
    fontSize: 13,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    color: 'var(--color-text-muted)',
    textAlign: 'left',
    borderBottom: '1px solid var(--color-card-border)',
};

const tdStyle = {
    padding: '12px 14px',
    fontSize: 13,
    color: 'var(--color-text-primary)',
    borderBottom: '1px solid var(--color-card-border)',
    verticalAlign: 'middle',
};

// ── Overlay Modal ──────────────────────────────────────────────────────────────

const Modal = ({ title, onClose, children, width = 480 }) => {
    const panelRef = useRef(null);

    // Enfocar el primer CAMPO al abrir (no el botón ×, que va antes en el DOM).
    // Guard: no robar foco si ya hay un elemento enfocado dentro del panel.
    useEffect(() => {
        const panel = panelRef.current;
        if (!panel || panel.contains(document.activeElement)) return;
        panel.querySelector('input, select, textarea')?.focus();
    }, []);

    useEffect(() => {
        const onKeyDown = (e) => {
            if (e.key === 'Escape') { onClose(); return; }
            // Focus trap: mantener el tab dentro del modal
            if (e.key !== 'Tab') return;
            const foco = panelRef.current?.querySelectorAll(
                'input, select, textarea, button, [href], [tabindex]:not([tabindex="-1"])'
            );
            if (!foco || foco.length === 0) return;
            const primero = foco[0];
            const ultimo = foco[foco.length - 1];
            if (e.shiftKey && document.activeElement === primero) {
                e.preventDefault();
                ultimo.focus();
            } else if (!e.shiftKey && document.activeElement === ultimo) {
                e.preventDefault();
                primero.focus();
            }
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [onClose]);

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 'var(--z-modal)',
            background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(2px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24,
        }} onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div ref={panelRef} role="dialog" aria-modal="true" aria-label={title} style={{
                background: 'var(--color-card)',
                border: '1px solid var(--color-card-border)',
                borderRadius: 14, padding: 28, width, maxWidth: '100%',
                maxHeight: '90vh', overflowY: 'auto',
                boxShadow: 'var(--shadow-modal)',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>
                        {title}
                    </h3>
                    <button onClick={onClose} aria-label="Cerrar" style={{
                        background: 'transparent', border: 'none', cursor: 'pointer',
                        color: 'var(--color-text-muted)', fontSize: 20, lineHeight: 1, padding: 2,
                    }}>×</button>
                </div>
                {children}
            </div>
        </div>
    );
};

// ── Componente Principal ───────────────────────────────────────────────────────

const SuperAdmin = () => {
    const [activeTab, setActiveTab] = useState('usuarios');

    // Datos
    const [usuarios, setUsuarios] = useState([]);
    const [roles, setRoles] = useState([]);
    const [modulos, setModulos] = useState([]);
    const [loading, setLoading] = useState(true);

    // Modales usuarios
    const [showUserModal, setShowUserModal] = useState(false);
    const [showPwdModal, setShowPwdModal] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [userForm, setUserForm] = useState({ username: '', correo: '', contrasena: '', rol_id: '', activo: true });
    const [pwdForm, setPwdForm] = useState({ nueva_contrasena: '', confirmar: '' });
    const [targetUserId, setTargetUserId] = useState(null);

    // Modales roles
    const [showRolModal, setShowRolModal] = useState(false);
    const [editingRol, setEditingRol] = useState(null);
    const [rolForm, setRolForm] = useState({ nombre_rol: '', modulo_ids: [] });

    const [saving, setSaving] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    // ── Carga de datos ───────────────────────────────────────────────────────

    const loadAll = useCallback(async () => {
        setLoading(true);
        try {
            const [u, r, m] = await Promise.all([getUsuarios(), getRoles(), getModulos()]);
            setUsuarios(Array.isArray(u) ? u : []);
            setRoles(Array.isArray(r) ? r : []);
            setModulos(Array.isArray(m) ? m : []);
        } catch (e) {
            toast.error('Error al cargar datos: ' + e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadAll(); }, [loadAll]);

    // ── Handlers Usuarios ────────────────────────────────────────────────────

    const openCreateUser = () => {
        setEditingUser(null);
        setUserForm({ username: '', correo: '', contrasena: '', rol_id: roles[0]?.rol_id ?? '', activo: true });
        setShowUserModal(true);
    };

    const openEditUser = (u) => {
        setEditingUser(u);
        setUserForm({ correo: u.correo, rol_id: u.rol_id, activo: u.activo });
        setShowUserModal(true);
    };

    const openPwdModal = (userId) => {
        setTargetUserId(userId);
        setPwdForm({ nueva_contrasena: '', confirmar: '' });
        setShowPwdModal(true);
    };

    const handleSaveUser = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (editingUser) {
                await updateUsuario(editingUser.user_id, {
                    correo: userForm.correo,
                    rol_id: Number(userForm.rol_id),
                    activo: userForm.activo,
                });
                toast.success('Usuario actualizado');
            } else {
                if (!userForm.contrasena) return toast.error('La contraseña es obligatoria');
                await createUsuario({
                    username: userForm.username,
                    correo: userForm.correo,
                    contrasena: userForm.contrasena,
                    rol_id: Number(userForm.rol_id),
                    activo: userForm.activo,
                });
                toast.success('Usuario creado');
            }
            setShowUserModal(false);
            loadAll();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleResetPassword = async (e) => {
        e.preventDefault();
        if (pwdForm.nueva_contrasena !== pwdForm.confirmar) {
            return toast.error('Las contraseñas no coinciden');
        }
        if (pwdForm.nueva_contrasena.length < 6) {
            return toast.error('Mínimo 6 caracteres');
        }
        setSaving(true);
        try {
            await resetPassword(targetUserId, pwdForm.nueva_contrasena);
            toast.success('Contraseña actualizada');
            setShowPwdModal(false);
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    // ── Handlers Roles ───────────────────────────────────────────────────────

    const openCreateRol = () => {
        setEditingRol(null);
        setRolForm({ nombre_rol: '', modulo_ids: [] });
        setShowRolModal(true);
    };

    const openEditRol = (r) => {
        setEditingRol(r);
        setRolForm({
            nombre_rol: r.nombre_rol,
            modulo_ids: r.modulos.map((m) => m.modulo_id),
        });
        setShowRolModal(true);
    };

    const toggleModulo = (modulo_id) => {
        setRolForm((prev) => ({
            ...prev,
            modulo_ids: prev.modulo_ids.includes(modulo_id)
                ? prev.modulo_ids.filter((id) => id !== modulo_id)
                : [...prev.modulo_ids, modulo_id],
        }));
    };

    const handleSaveRol = async (e) => {
        e.preventDefault();
        if (!rolForm.nombre_rol.trim()) return toast.error('El nombre del rol es obligatorio');
        setSaving(true);
        try {
            if (editingRol) {
                await updateRol(editingRol.rol_id, {
                    nombre_rol: rolForm.nombre_rol,
                    modulo_ids: rolForm.modulo_ids,
                });
                toast.success('Rol actualizado');
            } else {
                await createRol({ nombre_rol: rolForm.nombre_rol, modulo_ids: rolForm.modulo_ids });
                toast.success('Rol creado');
            }
            setShowRolModal(false);
            loadAll();
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteRol = async (rol) => {
        if (!window.confirm(`¿Eliminar el rol "${rol.nombre_rol}"? Esta acción no se puede deshacer.`)) return;
        try {
            await deleteRol(rol.rol_id);
            toast.success('Rol eliminado');
            loadAll();
        } catch (e) {
            toast.error(e.message);
        }
    };

    // ── Filtro usuarios ──────────────────────────────────────────────────────

    const filteredUsuarios = usuarios.filter((u) =>
        u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.correo.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.nombre_rol.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // ── Sincronización offline ───────────────────────────────────────────────

    const [syncItems, setSyncItems] = useState([]);
    const [syncLoading, setSyncLoading] = useState(false);

    const loadSyncQueue = useCallback(async () => {
        setSyncLoading(true);
        try {
            const items = await db.syncQueue.orderBy('createdAt').reverse().toArray();
            setSyncItems(items);
        } finally {
            setSyncLoading(false);
        }
    }, []);

    useEffect(() => {
        if (activeTab === 'sincronizacion') loadSyncQueue();
    }, [activeTab, loadSyncQueue]);

    useEffect(() => {
        const handler = () => {
            if (activeTab === 'sincronizacion') loadSyncQueue();
        };
        window.addEventListener('civot:sync-complete', handler);
        return () => window.removeEventListener('civot:sync-complete', handler);
    }, [activeTab, loadSyncQueue]);

    const handleReintentarTodos = async () => {
        await reintentarErrores();
        toast.success('Reintentando operaciones fallidas...');
        setTimeout(loadSyncQueue, 800);
    };

    const handleReintentarItem = async (id) => {
        await reintentarErrores([id]);
        toast.success('Operación encolada para reintento');
        setTimeout(loadSyncQueue, 800);
    };

    const handleLimpiarSincronizados = async () => {
        await limpiarSincronizados();
        toast.success('Registros sincronizados eliminados');
        loadSyncQueue();
    };

    const handleForzarSync = async () => {
        await procesarCola();
        setTimeout(loadSyncQueue, 800);
    };

    const syncPending = syncItems.filter((i) => i.status === 'pending').length;
    const syncErrors = syncItems.filter((i) => i.status === 'error').length;
    const syncDone = syncItems.filter((i) => i.status === 'synced').length;

    const formatFecha = (ts) => {
        if (!ts) return '—';
        const d = new Date(ts);
        return `${d.toLocaleDateString('es-CL')} ${d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })}`;
    };

    const extractDetalle = (payloadStr) => {
        try {
            const p = JSON.parse(payloadStr);
            if (p.sku) return `SKU: ${p.sku}`;
            if (p.rut) return `RUT: ${p.rut}`;
            if (p.tag_epc) return `EPC: ${p.tag_epc}`;
            return '—';
        } catch {
            return '—';
        }
    };

    const statusBadge = (status) => {
        const map = {
            pending: { bg: 'rgba(59,130,246,0.12)', color: 'var(--color-info)', border: 'rgba(59,130,246,0.3)', label: 'Pendiente' },
            error: { bg: 'rgba(239,68,68,0.12)', color: 'var(--color-error)', border: 'rgba(239,68,68,0.3)', label: 'Error' },
            synced: { bg: 'rgba(34,197,94,0.12)', color: 'var(--color-success)', border: 'rgba(34,197,94,0.3)', label: 'Sincronizado' },
        };
        const s = map[status] || map.pending;
        return (
            <span style={{
                display: 'inline-block', padding: '3px 10px', borderRadius: 999,
                fontSize: 13, fontWeight: 600,
                background: s.bg, color: s.color, border: `1px solid ${s.border}`,
            }}>{s.label}</span>
        );
    };

    // ── Render ───────────────────────────────────────────────────────────────

    const tabs = [
        { id: 'usuarios', label: 'Usuarios' },
        { id: 'roles', label: 'Roles y Módulos' },
        { id: 'sincronizacion', label: 'Sincronización' },
    ];

    return (
        <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: 28 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>
                    Administración del sistema
                </h1>
                <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Gestión de usuarios, roles y permisos de acceso
                </p>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--color-card-border)', paddingBottom: 0 }}>
                {tabs.map((t) => (
                    <button
                        key={t.id}
                        onClick={() => setActiveTab(t.id)}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            borderBottom: activeTab === t.id ? '2px solid var(--color-accent)' : '2px solid transparent',
                            padding: '10px 18px',
                            fontSize: 14,
                            fontWeight: activeTab === t.id ? 600 : 400,
                            color: activeTab === t.id ? 'var(--color-accent)' : 'var(--color-text-muted)',
                            cursor: 'pointer',
                            marginBottom: -1,
                            fontFamily: 'var(--font-family)',
                        }}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
                    <div className="loading" />
                </div>
            ) : (
                <>
                    {/* ── Tab Usuarios ─────────────────────────────────────── */}
                    {activeTab === 'usuarios' && (
                        <div style={card}>
                            {/* Toolbar */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, gap: 12 }}>
                                <input
                                    type="text"
                                    placeholder="Buscar por nombre, correo o rol..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    style={{ ...inputStyle, maxWidth: 320 }}
                                />
                                <button style={btnPrimary} onClick={openCreateUser}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                                    </svg>
                                    Nuevo usuario
                                </button>
                            </div>

                            {/* Tabla */}
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr>
                                            {['Usuario', 'Correo', 'Rol', 'Estado', 'Acciones'].map((h) => (
                                                <th key={h} style={thStyle}>{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredUsuarios.length === 0 ? (
                                            <tr>
                                                <td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: 'var(--color-text-muted)', padding: 32 }}>
                                                    No hay usuarios
                                                </td>
                                            </tr>
                                        ) : filteredUsuarios.map((u) => (
                                            <tr key={u.user_id} style={{ transition: 'background 0.1s' }}
                                                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-accent-light)'}
                                                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                                                <td style={tdStyle}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                        <div style={{
                                                            width: 32, height: 32, borderRadius: '50%',
                                                            background: 'var(--color-accent)', display: 'flex',
                                                            alignItems: 'center', justifyContent: 'center',
                                                            fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0,
                                                        }}>
                                                            {u.username[0].toUpperCase()}
                                                        </div>
                                                        <span style={{ fontWeight: 600 }}>{u.username}</span>
                                                    </div>
                                                </td>
                                                <td style={{ ...tdStyle, color: 'var(--color-text-secondary)' }}>{u.correo}</td>
                                                <td style={tdStyle}>
                                                    <span style={{
                                                        display: 'inline-block', padding: '3px 10px', borderRadius: 999,
                                                        fontSize: 13, fontWeight: 600,
                                                        background: 'var(--color-accent-light)', color: 'var(--color-accent)',
                                                        border: '1px solid rgba(13,148,136,0.25)',
                                                    }}>
                                                        {u.nombre_rol}
                                                    </span>
                                                </td>
                                                <td style={tdStyle}>
                                                    <span style={{
                                                        display: 'inline-block', padding: '3px 10px', borderRadius: 999,
                                                        fontSize: 13, fontWeight: 600,
                                                        background: u.activo ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                                                        color: u.activo ? 'var(--color-success)' : 'var(--color-error)',
                                                        border: u.activo ? '1px solid rgba(34,197,94,0.25)' : '1px solid rgba(239,68,68,0.25)',
                                                    }}>
                                                        {u.activo ? 'Activo' : 'Inactivo'}
                                                    </span>
                                                </td>
                                                <td style={tdStyle}>
                                                    <div style={{ display: 'flex', gap: 6 }}>
                                                        <ActionBtn title="Editar" color="var(--color-accent)" onClick={() => openEditUser(u)}>
                                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                                                                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                                                            </svg>
                                                        </ActionBtn>
                                                        <ActionBtn title="Cambiar contraseña" color="var(--color-warning)" onClick={() => openPwdModal(u.user_id)}>
                                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                                                <path d="M7 11V7a5 5 0 0110 0v4" />
                                                            </svg>
                                                        </ActionBtn>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* ── Tab Roles ─────────────────────────────────────────── */}
                    {activeTab === 'roles' && (
                        <div style={card}>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
                                <button style={btnPrimary} onClick={openCreateRol}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                                    </svg>
                                    Nuevo rol
                                </button>
                            </div>

                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr>
                                            {['Nombre del rol', 'Módulos asignados', 'Acciones'].map((h) => (
                                                <th key={h} style={thStyle}>{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {roles.map((r) => (
                                            <tr key={r.rol_id}
                                                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-accent-light)'}
                                                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                                                <td style={{ ...tdStyle, fontWeight: 600 }}>{r.nombre_rol}</td>
                                                <td style={tdStyle}>
                                                    {r.nombre_rol === 'admin' ? (
                                                        <span style={{ fontSize: 13, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                                                            Acceso total (bypass)
                                                        </span>
                                                    ) : r.modulos.length === 0 ? (
                                                        <span style={{ fontSize: 13, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                                                            Sin módulos asignados
                                                        </span>
                                                    ) : (
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                                            {r.modulos.map((m) => (
                                                                <span key={m.modulo_id} style={{
                                                                    padding: '2px 8px', borderRadius: 6,
                                                                    fontSize: 13, fontWeight: 500,
                                                                    background: 'var(--color-accent-light)',
                                                                    color: 'var(--color-accent)',
                                                                    border: '1px solid rgba(13,148,136,0.25)',
                                                                }}>
                                                                    {label(m.nombre_modulo)}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </td>
                                                <td style={tdStyle}>
                                                    <div style={{ display: 'flex', gap: 6 }}>
                                                        <ActionBtn title="Editar" color="var(--color-accent)" onClick={() => openEditRol(r)}>
                                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                                                                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                                                            </svg>
                                                        </ActionBtn>
                                                        {r.nombre_rol !== 'admin' && (
                                                            <ActionBtn title="Eliminar" color="var(--color-error)" onClick={() => handleDeleteRol(r)}>
                                                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                    <polyline points="3 6 5 6 21 6" />
                                                                    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
                                                                    <path d="M10 11v6M14 11v6" />
                                                                    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
                                                                </svg>
                                                            </ActionBtn>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                    {/* ── Tab Sincronización ───────────────────────────────── */}
                    {activeTab === 'sincronizacion' && (
                        <div>
                            {/* Resumen */}
                            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
                                <div style={{ ...card, padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 10, flex: '1 1 140px' }}>
                                    <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-info)' }}>{syncPending}</span>
                                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Pendiente{syncPending !== 1 ? 's' : ''}</span>
                                </div>
                                <div style={{ ...card, padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 10, flex: '1 1 140px' }}>
                                    <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-error)' }}>{syncErrors}</span>
                                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Con error</span>
                                </div>
                                <div style={{ ...card, padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 10, flex: '1 1 140px' }}>
                                    <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-success)' }}>{syncDone}</span>
                                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Sincronizado{syncDone !== 1 ? 's' : ''}</span>
                                </div>
                                <div style={{ flex: '1 1 auto', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flexWrap: 'wrap' }}>
                                    {syncPending > 0 && (
                                        <button style={btnGhost} onClick={handleForzarSync}>
                                            Forzar sincronización
                                        </button>
                                    )}
                                    {syncErrors > 0 && (
                                        <button style={{ ...btnPrimary, background: 'var(--color-error)' }} onClick={handleReintentarTodos}>
                                            Reintentar fallidos ({syncErrors})
                                        </button>
                                    )}
                                    {syncDone > 0 && (
                                        <button style={btnGhost} onClick={handleLimpiarSincronizados}>
                                            Limpiar sincronizados
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Tabla */}
                            <div style={card}>
                                {syncLoading ? (
                                    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
                                        <div className="loading" />
                                    </div>
                                ) : syncItems.length === 0 ? (
                                    <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-text-muted)', fontSize: 14 }}>
                                        No hay operaciones en cola
                                    </div>
                                ) : (
                                    <div style={{ overflowX: 'auto' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr>
                                                    {['Operación', 'Detalle', 'Fecha', 'Reintentos', 'Estado', 'Acción'].map((h) => (
                                                        <th key={h} style={thStyle}>{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {syncItems.map((item) => (
                                                    <tr key={item.id}
                                                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-accent-light)'}
                                                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                                                        <td style={tdStyle}>
                                                            <span style={{
                                                                display: 'inline-block', padding: '2px 7px', borderRadius: 5,
                                                                fontSize: 13, fontWeight: 700, marginRight: 6,
                                                                background: 'var(--color-accent-light)', color: 'var(--color-accent)',
                                                            }}>{item.method}</span>
                                                            <span style={{ fontSize: 13, color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>
                                                                {item.endpoint}
                                                            </span>
                                                        </td>
                                                        <td style={{ ...tdStyle, color: 'var(--color-text-secondary)', fontSize: 13 }}>
                                                            {extractDetalle(item.payload)}
                                                        </td>
                                                        <td style={{ ...tdStyle, fontSize: 13, color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                                                            {formatFecha(item.createdAt)}
                                                        </td>
                                                        <td style={{ ...tdStyle, textAlign: 'center' }}>
                                                            <span style={{ fontSize: 13, color: item.retries > 0 ? 'var(--color-error)' : 'var(--color-text-muted)' }}>
                                                                {item.retries ?? 0}
                                                            </span>
                                                        </td>
                                                        <td style={tdStyle}>{statusBadge(item.status)}</td>
                                                        <td style={tdStyle}>
                                                            {item.status === 'error' && (
                                                                <ActionBtn title="Reintentar" color="var(--color-accent)" onClick={() => handleReintentarItem(item.id)}>
                                                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                        <polyline points="1 4 1 10 7 10" />
                                                                        <path d="M3.51 15a9 9 0 1 0 .49-3.34" />
                                                                    </svg>
                                                                </ActionBtn>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* ── Modal: Crear/Editar Usuario ──────────────────────────────── */}
            {showUserModal && (
                <Modal
                    title={editingUser ? `Editar usuario: ${editingUser.username}` : 'Nuevo usuario'}
                    onClose={() => setShowUserModal(false)}
                >
                    <form onSubmit={handleSaveUser} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        {!editingUser && (
                            <div>
                                <label style={labelStyle}>Username</label>
                                <input
                                    style={inputStyle}
                                    value={userForm.username}
                                    onChange={(e) => setUserForm((p) => ({ ...p, username: e.target.value }))}
                                    required
                                    autoComplete="off"
                                />
                            </div>
                        )}
                        <div>
                            <label style={labelStyle}>Correo electrónico</label>
                            <input
                                type="email"
                                style={inputStyle}
                                value={userForm.correo}
                                onChange={(e) => setUserForm((p) => ({ ...p, correo: e.target.value }))}
                                required
                            />
                        </div>
                        {!editingUser && (
                            <div>
                                <label style={labelStyle}>Contraseña</label>
                                <input
                                    type="password"
                                    style={inputStyle}
                                    value={userForm.contrasena}
                                    onChange={(e) => setUserForm((p) => ({ ...p, contrasena: e.target.value }))}
                                    required
                                    minLength={6}
                                    autoComplete="new-password"
                                />
                                <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4 }}>Mínimo 6 caracteres</p>
                            </div>
                        )}
                        <div>
                            <label style={labelStyle}>Rol</label>
                            <select
                                style={{ ...inputStyle, appearance: 'none' }}
                                value={userForm.rol_id}
                                onChange={(e) => setUserForm((p) => ({ ...p, rol_id: e.target.value }))}
                                required
                            >
                                <option value="">Seleccionar rol...</option>
                                {roles.map((r) => (
                                    <option key={r.rol_id} value={r.rol_id}>{r.nombre_rol}</option>
                                ))}
                            </select>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <input
                                type="checkbox"
                                id="activo-check"
                                checked={userForm.activo}
                                onChange={(e) => setUserForm((p) => ({ ...p, activo: e.target.checked }))}
                                style={{ width: 16, height: 16, cursor: 'pointer' }}
                            />
                            <label htmlFor="activo-check" style={{ ...labelStyle, margin: 0, textTransform: 'none', letterSpacing: 0, fontSize: 13, cursor: 'pointer' }}>
                                Usuario activo
                            </label>
                        </div>
                        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
                            <button type="button" style={btnGhost} onClick={() => setShowUserModal(false)}>Cancelar</button>
                            <button type="submit" style={btnPrimary} disabled={saving}>
                                {saving ? 'Guardando...' : editingUser ? 'Guardar cambios' : 'Crear usuario'}
                            </button>
                        </div>
                    </form>
                </Modal>
            )}

            {/* ── Modal: Resetear contraseña ───────────────────────────────── */}
            {showPwdModal && (
                <Modal title="Cambiar contraseña" onClose={() => setShowPwdModal(false)} width={400}>
                    <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: 0 }}>
                            Establece una nueva contraseña para este usuario. No se requiere la contraseña actual.
                        </p>
                        <div>
                            <label style={labelStyle}>Nueva contraseña</label>
                            <input
                                type="password"
                                style={inputStyle}
                                value={pwdForm.nueva_contrasena}
                                onChange={(e) => setPwdForm((p) => ({ ...p, nueva_contrasena: e.target.value }))}
                                required
                                minLength={6}
                                autoComplete="new-password"
                            />
                        </div>
                        <div>
                            <label style={labelStyle}>Confirmar contraseña</label>
                            <input
                                type="password"
                                style={inputStyle}
                                value={pwdForm.confirmar}
                                onChange={(e) => setPwdForm((p) => ({ ...p, confirmar: e.target.value }))}
                                required
                                minLength={6}
                                autoComplete="new-password"
                            />
                        </div>
                        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
                            <button type="button" style={btnGhost} onClick={() => setShowPwdModal(false)}>Cancelar</button>
                            <button type="submit" style={{ ...btnPrimary, background: 'var(--color-warning)' }} disabled={saving}>
                                {saving ? 'Guardando...' : 'Actualizar contraseña'}
                            </button>
                        </div>
                    </form>
                </Modal>
            )}

            {/* ── Modal: Crear/Editar Rol ──────────────────────────────────── */}
            {showRolModal && (
                <Modal
                    title={editingRol ? `Editar rol: ${editingRol.nombre_rol}` : 'Nuevo rol'}
                    onClose={() => setShowRolModal(false)}
                    width={520}
                >
                    <form onSubmit={handleSaveRol} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                        <div>
                            <label style={labelStyle}>Nombre del rol</label>
                            <input
                                style={inputStyle}
                                value={rolForm.nombre_rol}
                                onChange={(e) => setRolForm((p) => ({ ...p, nombre_rol: e.target.value }))}
                                required
                                disabled={editingRol?.nombre_rol === 'admin'}
                            />
                        </div>

                        <div>
                            <label style={{ ...labelStyle, marginBottom: 12 }}>Módulos con acceso</label>
                            {editingRol?.nombre_rol === 'admin' ? (
                                <p style={{ fontSize: 13, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                                    El rol admin tiene acceso total por diseño del sistema.
                                </p>
                            ) : (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                    {modulos.map((m) => {
                                        const checked = rolForm.modulo_ids.includes(m.modulo_id);
                                        return (
                                            <label key={m.modulo_id} style={{
                                                display: 'flex', alignItems: 'center', gap: 8,
                                                padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
                                                border: `1px solid ${checked ? 'var(--color-accent)' : 'var(--color-card-border)'}`,
                                                background: checked ? 'var(--color-accent-light)' : 'transparent',
                                                transition: 'all 0.15s ease',
                                            }}>
                                                <input
                                                    type="checkbox"
                                                    checked={checked}
                                                    onChange={() => toggleModulo(m.modulo_id)}
                                                    style={{ width: 14, height: 14 }}
                                                />
                                                <span style={{ fontSize: 13, color: checked ? 'var(--color-accent)' : 'var(--color-text-secondary)', fontWeight: checked ? 600 : 400 }}>
                                                    {label(m.nombre_modulo)}
                                                </span>
                                            </label>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                            <button type="button" style={btnGhost} onClick={() => setShowRolModal(false)}>Cancelar</button>
                            <button type="submit" style={btnPrimary} disabled={saving}>
                                {saving ? 'Guardando...' : editingRol ? 'Guardar cambios' : 'Crear rol'}
                            </button>
                        </div>
                    </form>
                </Modal>
            )}
        </div>
    );
};

// ── Botón de acción pequeño ────────────────────────────────────────────────────

const ActionBtn = ({ onClick, title, color, children }) => (
    <button
        onClick={onClick}
        title={title}
        style={{
            background: 'transparent',
            border: `1px solid color-mix(in srgb, ${color} 25%, transparent)`,
            borderRadius: 6,
            padding: '5px 8px',
            cursor: 'pointer',
            color,
            display: 'flex',
            alignItems: 'center',
            transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = `color-mix(in srgb, ${color} 12%, transparent)`}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
    >
        {children}
    </button>
);

export default SuperAdmin;
