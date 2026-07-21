import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { getEmployeeReturnItems, processReturn } from '../../services/returnsService';

const PrendasModal = ({ employee, onClose, onSuccess }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [procesando, setProcesando] = useState(false);
    const [seleccionados, setSeleccionados] = useState({});

    useEffect(() => {
        const fetchPrendas = async () => {
            try {
                setLoading(true);
                const data = await getEmployeeReturnItems(employee.rut);
                setItems(data.items || []);
            } catch {
                toast.error('No se pudieron cargar las prendas asignadas.');
                onClose();
            } finally {
                setLoading(false);
            }
        };
        fetchPrendas();
    }, [employee.rut, onClose]);

    const toggleItem = (sku) => {
        setSeleccionados((prev) => ({ ...prev, [sku]: !prev[sku] }));
    };

    const itemsSeleccionados = items.filter((i) => seleccionados[i.sku]);
    const totalSeleccionados = itemsSeleccionados.length;

    const handleProcesar = async () => {
        if (totalSeleccionados === 0) return;
        setProcesando(true);
        try {
            await processReturn(
                employee.rut,
                itemsSeleccionados.map((i) => ({ id: i.id, sku: i.sku, quantityReturned: 1, status: '' })),
                ''
            );
            toast.success(`${totalSeleccionados} prenda${totalSeleccionados !== 1 ? 's' : ''} devuelta${totalSeleccionados !== 1 ? 's' : ''} correctamente.`);
            onSuccess();
        } catch (err) {
            toast.error(err.message || 'Error al procesar la devolución.');
        } finally {
            setProcesando(false);
        }
    };

    const formatFecha = (fecha) => {
        if (!fecha) return '—';
        return new Date(fecha).toLocaleDateString('es-CL');
    };

    return (
        <div style={styles.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div style={styles.modal}>
                {/* Header */}
                <div style={styles.header}>
                    <div>
                        <h3 style={styles.titulo}>{employee.name}</h3>
                        <p style={styles.subtitulo}>
                            {employee.rut}
                            <span style={styles.badge}>{items.length} prenda{items.length !== 1 ? 's' : ''} activa{items.length !== 1 ? 's' : ''}</span>
                        </p>
                    </div>
                    <button onClick={onClose} style={styles.closeBtn}>×</button>
                </div>

                {/* Body */}
                <div style={styles.body}>
                    {loading ? (
                        <>
                            {[1, 2, 3].map((n) => (
                                <div key={n} style={styles.skeleton} />
                            ))}
                        </>
                    ) : items.length === 0 ? (
                        <p style={styles.empty}>Este trabajador no tiene prendas activas.</p>
                    ) : (
                        <table style={styles.table}>
                            <thead>
                                <tr>
                                    {['SKU', 'Tipo / Talla', 'Fecha asignación', 'Devolver'].map((h) => (
                                        <th key={h} style={styles.th}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {items.map((item) => {
                                    const checked = !!seleccionados[item.sku];
                                    return (
                                        <tr
                                            key={item.sku}
                                            style={{ background: checked ? 'rgba(99,102,241,0.07)' : 'transparent', transition: 'background 0.15s' }}
                                        >
                                            <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: 13, color: 'var(--color-text-primary)', fontWeight: 600 }}>
                                                {item.sku}
                                            </td>
                                            <td style={styles.td}>
                                                {[item.name, item.size].filter(Boolean).join(' / ') || '—'}
                                            </td>
                                            <td style={{ ...styles.td, fontSize: 13, color: 'var(--color-text-muted)' }}>
                                                {formatFecha(item.fecha_entrega)}
                                            </td>
                                            <td style={{ ...styles.td, textAlign: 'center' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={checked}
                                                    onChange={() => toggleItem(item.sku)}
                                                    style={{ width: 16, height: 16, cursor: 'pointer', accentColor: 'var(--color-accent-bright)' }}
                                                />
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Footer */}
                {!loading && items.length > 0 && (
                    <div style={styles.footer}>
                        <p style={styles.resumen}>
                            {totalSeleccionados > 0
                                ? <><strong style={{ color: 'var(--color-text-primary)' }}>{totalSeleccionados}</strong> de {items.length} seleccionada{totalSeleccionados !== 1 ? 's' : ''} para devolver</>
                                : <span style={{ color: '#475569' }}>Seleccione las prendas a devolver</span>
                            }
                        </p>
                        <div style={styles.footerActions}>
                            <button onClick={onClose} style={styles.btnCancel} disabled={procesando}>
                                Cancelar
                            </button>
                            <button
                                onClick={handleProcesar}
                                style={{ ...styles.btnProcesar, opacity: totalSeleccionados === 0 || procesando ? 0.45 : 1 }}
                                disabled={totalSeleccionados === 0 || procesando}
                            >
                                {procesando ? 'Procesando…' : 'Procesar devolución'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

const styles = {
    overlay: {
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 24,
    },
    modal: {
        background: 'var(--color-card-bg, var(--color-card))',
        border: '1px solid var(--color-card-border, var(--color-border))',
        borderRadius: 14,
        width: '100%',
        maxWidth: 720,
        maxHeight: '80vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        padding: '24px 28px 20px',
        borderBottom: '1px solid var(--color-card-border, var(--color-border))',
    },
    titulo: {
        fontSize: 17,
        fontWeight: 700,
        color: 'var(--color-text-primary, var(--color-text-primary))',
        margin: 0,
    },
    subtitulo: {
        fontSize: 13,
        color: 'var(--color-text-muted, var(--color-text-muted))',
        marginTop: 4,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
    },
    badge: {
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: 999,
        fontSize: 13,
        fontWeight: 600,
        background: 'rgba(99,102,241,0.12)',
        color: 'var(--color-accent-bright)',
        border: '1px solid rgba(99,102,241,0.25)',
    },
    closeBtn: {
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        color: 'var(--color-text-muted, var(--color-text-muted))',
        fontSize: 22,
        lineHeight: 1,
        padding: '2px 4px',
        flexShrink: 0,
    },
    body: {
        overflowY: 'auto',
        padding: '0 28px',
        flex: 1,
        minHeight: 120,
    },
    skeleton: {
        height: 44,
        background: 'rgba(42,49,71,0.5)',
        borderRadius: 6,
        margin: '12px 0',
        animation: 'pulse 1.5s ease-in-out infinite',
    },
    empty: {
        textAlign: 'center',
        color: 'var(--color-text-muted, var(--color-text-muted))',
        fontSize: 14,
        padding: '40px 0',
    },
    table: {
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: 14,
    },
    th: {
        padding: '14px 12px',
        fontSize: 13,
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        color: 'var(--color-text-muted, var(--color-text-muted))',
        textAlign: 'left',
        borderBottom: '1px solid var(--color-card-border, var(--color-border))',
        whiteSpace: 'nowrap',
        position: 'sticky',
        top: 0,
        background: 'var(--color-card-bg, var(--color-card))',
    },
    td: {
        padding: '13px 12px',
        color: 'var(--color-text-secondary, var(--color-text-secondary))',
        borderBottom: '1px solid rgba(42,49,71,0.4)',
        verticalAlign: 'middle',
    },
    footer: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 28px',
        borderTop: '1px solid var(--color-card-border, var(--color-border))',
        gap: 16,
        flexWrap: 'wrap',
    },
    resumen: {
        fontSize: 13,
        color: 'var(--color-text-secondary, var(--color-text-secondary))',
        margin: 0,
    },
    footerActions: {
        display: 'flex',
        gap: 8,
    },
    btnCancel: {
        background: 'transparent',
        border: '1px solid var(--color-card-border, var(--color-border))',
        borderRadius: 8,
        padding: '8px 16px',
        fontSize: 13,
        color: 'var(--color-text-muted, var(--color-text-muted))',
        cursor: 'pointer',
        fontFamily: 'var(--font-family)',
    },
    btnProcesar: {
        background: 'var(--color-accent-bright)',
        border: 'none',
        borderRadius: 8,
        padding: '8px 18px',
        fontSize: 13,
        fontWeight: 600,
        color: '#fff',
        cursor: 'pointer',
        fontFamily: 'var(--font-family)',
        transition: 'opacity 0.15s',
    },
};

export default PrendasModal;
