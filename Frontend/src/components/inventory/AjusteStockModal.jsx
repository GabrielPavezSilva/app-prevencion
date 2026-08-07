import { useState, useMemo } from 'react';

/**
 * Ajuste manual de stock. Fija la cantidad a un valor absoluto (el backend
 * registra el delta como movimiento AJUSTE). La observación es obligatoria.
 *
 * - Si `stockRow` viene informado: edita esa fila (producto/talla bloqueados).
 * - Si no: alta/ajuste eligiendo producto (y talla si el producto la maneja).
 */
const AjusteStockModal = ({ stockRow, productos = [], tallas = [], onGuardar, onCerrar, guardando, errorServidor }) => {
    const esEdicion = !!stockRow;
    const [productoId, setProductoId] = useState(stockRow?.producto_id ?? '');
    const [tallaId, setTallaId] = useState(stockRow?.talla_id ?? '');
    const [cantidad, setCantidad] = useState(stockRow ? String(stockRow.cantidad_actual) : '');
    const [observacion, setObservacion] = useState('');
    const [errorLocal, setErrorLocal] = useState('');

    const productoSel = useMemo(
        () => productos.find((p) => p.producto_id === Number(productoId)),
        [productos, productoId]
    );
    const requiereTalla = esEdicion ? stockRow.talla_id != null : !!productoSel?.talla_aplica;

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!productoId) return setErrorLocal('Selecciona un producto');
        if (requiereTalla && !tallaId) return setErrorLocal('Este producto requiere talla');
        if (cantidad === '' || Number(cantidad) < 0) return setErrorLocal('Cantidad inválida');
        if (!observacion.trim()) return setErrorLocal('La observación es obligatoria');
        setErrorLocal('');
        onGuardar({
            producto_id: Number(productoId),
            talla_id: requiereTalla ? Number(tallaId) : null,
            cantidad_nueva: Number(cantidad),
            observacion: observacion.trim(),
        });
    };

    return (
        <div className="modal-overlay" onClick={onCerrar}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                <h3 className="modal-title">{esEdicion ? 'Ajustar stock' : 'Cargar / ajustar stock'}</h3>

                <form onSubmit={handleSubmit}>
                    <div className="modal-field">
                        <label className="modal-label">Producto *</label>
                        {esEdicion ? (
                            <input className="modal-input" value={stockRow.nombre_producto} disabled />
                        ) : (
                            <select
                                className="modal-input"
                                value={productoId}
                                onChange={(e) => { setProductoId(e.target.value); setTallaId(''); }}
                                disabled={guardando}
                                autoFocus
                            >
                                <option value="">— Selecciona —</option>
                                {productos.map((p) => (
                                    <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>
                                ))}
                            </select>
                        )}
                    </div>

                    {requiereTalla && (
                        <div className="modal-field">
                            <label className="modal-label">Talla *</label>
                            {esEdicion ? (
                                <input className="modal-input" value={stockRow.nombre_talla ?? ''} disabled />
                            ) : (
                                <select
                                    className="modal-input"
                                    value={tallaId}
                                    onChange={(e) => setTallaId(e.target.value)}
                                    disabled={guardando}
                                >
                                    <option value="">— Selecciona —</option>
                                    {tallas.map((t) => (
                                        <option key={t.TallaID} value={t.TallaID}>{t.nombreTalla}</option>
                                    ))}
                                </select>
                            )}
                        </div>
                    )}

                    <div className="modal-field">
                        <label className="modal-label">Cantidad {esEdicion && '(nueva cantidad total)'} *</label>
                        <input
                            className="modal-input"
                            type="number"
                            min="0"
                            value={cantidad}
                            onChange={(e) => setCantidad(e.target.value)}
                            disabled={guardando}
                        />
                    </div>

                    <div className="modal-field">
                        <label className="modal-label">Observación *</label>
                        <input
                            className="modal-input"
                            type="text"
                            value={observacion}
                            onChange={(e) => setObservacion(e.target.value)}
                            disabled={guardando}
                            placeholder="Motivo del ajuste (queda en el libro mayor)"
                        />
                    </div>

                    {(errorLocal || errorServidor) && (
                        <p className="modal-error">{errorLocal || errorServidor}</p>
                    )}

                    <div className="modal-actions">
                        <button type="button" className="catalogo-btn catalogo-btn--cancel" onClick={onCerrar} disabled={guardando}>
                            Cancelar
                        </button>
                        <button type="submit" className="catalogo-btn catalogo-btn--primary" disabled={guardando}>
                            {guardando ? 'Guardando...' : 'Guardar'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AjusteStockModal;
