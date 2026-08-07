import { useState, useMemo } from 'react';

/**
 * Sustitución por daño: reemplaza una entrega vigente por un ítem nuevo.
 * onGuardar recibe { producto_id, talla_id, cantidad, observacion }.
 */
const SustitucionModal = ({ entregaReemplazada, productos = [], tallas = [], onGuardar, onCerrar, guardando, errorServidor }) => {
    const [productoId, setProductoId] = useState('');
    const [tallaId, setTallaId] = useState('');
    const [cantidad, setCantidad] = useState('1');
    const [observacion, setObservacion] = useState('');
    const [errorLocal, setErrorLocal] = useState('');

    const productoSel = useMemo(
        () => productos.find((p) => p.producto_id === Number(productoId)),
        [productos, productoId]
    );
    const requiereTalla = !!productoSel?.talla_aplica;

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!productoId) return setErrorLocal('Selecciona el producto de reemplazo');
        if (requiereTalla && !tallaId) return setErrorLocal('Este producto requiere talla');
        if (cantidad === '' || Number(cantidad) <= 0) return setErrorLocal('Cantidad inválida');
        if (!observacion.trim()) return setErrorLocal('La observación es obligatoria');
        setErrorLocal('');
        onGuardar({
            producto_id: Number(productoId),
            talla_id: requiereTalla ? Number(tallaId) : null,
            cantidad: Number(cantidad),
            observacion: observacion.trim(),
        });
    };

    const dañado = [entregaReemplazada.nombre_producto, entregaReemplazada.nombre_talla]
        .filter(Boolean).join(' · ');

    return (
        <div className="modal-overlay" onClick={onCerrar}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                <h3 className="modal-title">Sustituir por daño</h3>
                <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 16 }}>
                    Se dará de baja: <strong>{dañado}</strong> (cant. {entregaReemplazada.cantidad}) y se entregará el reemplazo.
                </p>

                <form onSubmit={handleSubmit}>
                    <div className="modal-field">
                        <label className="modal-label">Producto de reemplazo *</label>
                        <select className="modal-input" value={productoId} autoFocus disabled={guardando}
                            onChange={(e) => { setProductoId(e.target.value); setTallaId(''); }}>
                            <option value="">— Selecciona —</option>
                            {productos.map((p) => (
                                <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>
                            ))}
                        </select>
                    </div>

                    {requiereTalla && (
                        <div className="modal-field">
                            <label className="modal-label">Talla *</label>
                            <select className="modal-input" value={tallaId} disabled={guardando}
                                onChange={(e) => setTallaId(e.target.value)}>
                                <option value="">— Selecciona —</option>
                                {tallas.map((t) => (
                                    <option key={t.TallaID} value={t.TallaID}>{t.nombreTalla}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    <div className="modal-field">
                        <label className="modal-label">Cantidad *</label>
                        <input className="modal-input" type="number" min="1" value={cantidad}
                            onChange={(e) => setCantidad(e.target.value)} disabled={guardando} />
                    </div>

                    <div className="modal-field">
                        <label className="modal-label">Observación *</label>
                        <input className="modal-input" type="text" value={observacion}
                            onChange={(e) => setObservacion(e.target.value)} disabled={guardando}
                            placeholder="Motivo del daño" />
                    </div>

                    {(errorLocal || errorServidor) && <p className="modal-error">{errorLocal || errorServidor}</p>}

                    <div className="modal-actions">
                        <button type="button" className="catalogo-btn catalogo-btn--cancel" onClick={onCerrar} disabled={guardando}>
                            Cancelar
                        </button>
                        <button type="submit" className="catalogo-btn catalogo-btn--primary" disabled={guardando}>
                            {guardando ? 'Guardando...' : 'Confirmar sustitución'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default SustitucionModal;
