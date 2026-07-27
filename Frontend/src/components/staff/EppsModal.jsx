import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import { getVigentes } from '../../services/entregasService';

const MOTIVO_LABEL = {
    NUEVA: 'Primera entrega',
    PERDIDA: 'Reposición por pérdida',
    DANO: 'Sustitución por daño',
};

const formatearFecha = (valor) => {
    if (!valor) return '—';
    const d = new Date(valor);
    return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('es-CL');
};

/**
 * EPP vigentes de un trabajador (entregas no reemplazadas por una sustitución).
 * Solo lectura: entregar y sustituir viven en la página Entregas.
 */
const EppsModal = ({ employee, onClose }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        let vigente = true;
        const cargar = async () => {
            try {
                setLoading(true);
                const data = await getVigentes(employee.rut);
                if (vigente) setItems(Array.isArray(data) ? data : []);
            } catch {
                toast.error('No se pudieron cargar los EPP del trabajador.');
                if (vigente) setItems([]);
            } finally {
                if (vigente) setLoading(false);
            }
        };
        cargar();
        return () => { vigente = false; };
    }, [employee.rut]);

    const totalUnidades = items.reduce((acc, i) => acc + (i.cantidad ?? 0), 0);

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-box" style={{ maxWidth: 620 }} onClick={(e) => e.stopPropagation()}>
                <h3 className="modal-title">EPP vigentes</h3>
                <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 16 }}>
                    <strong>{employee.name}</strong> · {employee.rut}
                    {employee.area && employee.area !== '—' ? ` · ${employee.area}` : ''}
                </p>

                {loading ? (
                    <p style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>Cargando…</p>
                ) : items.length === 0 ? (
                    <p style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>
                        Este trabajador no tiene EPP vigentes.
                    </p>
                ) : (
                    <>
                        <div style={{ maxHeight: 340, overflowY: 'auto' }}>
                            <table className="epps-modal-table">
                                <thead>
                                    <tr>
                                        <th style={{ textAlign: 'left' }}>Producto</th>
                                        <th style={{ textAlign: 'center' }}>Talla</th>
                                        <th style={{ textAlign: 'center' }}>Cant.</th>
                                        <th style={{ textAlign: 'left' }}>Motivo</th>
                                        <th style={{ textAlign: 'center' }}>Entrega</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((i) => (
                                        <tr key={i.entrega_id}>
                                            <td>{i.nombre_producto ?? `#${i.producto_id}`}</td>
                                            <td style={{ textAlign: 'center' }}>{i.nombre_talla ?? '—'}</td>
                                            <td style={{ textAlign: 'center' }}>{i.cantidad}</td>
                                            <td style={{ color: 'var(--color-text-secondary)' }}>
                                                {MOTIVO_LABEL[i.motivo] ?? i.motivo}
                                            </td>
                                            <td style={{ textAlign: 'center' }}>{formatearFecha(i.fecha_entrega)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 10 }}>
                            {items.length} {items.length === 1 ? 'entrega vigente' : 'entregas vigentes'} · {totalUnidades} unidades
                        </p>
                    </>
                )}

                <div className="modal-actions">
                    <button type="button" className="catalogo-btn catalogo-btn--cancel" onClick={onClose}>
                        Cerrar
                    </button>
                    <button
                        type="button"
                        className="catalogo-btn catalogo-btn--primary"
                        onClick={() => navigate('/entregas', { state: { rut: employee.rut } })}
                    >
                        Registrar entrega
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EppsModal;
