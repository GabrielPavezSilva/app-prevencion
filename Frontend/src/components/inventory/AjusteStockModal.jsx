import { useState, useMemo } from 'react';

/**
 * Ajuste manual de stock. Fija la cantidad a un valor absoluto (el backend
 * registra el delta como movimiento AJUSTE). La observación es obligatoria.
 *
 * - Si `stockRow` viene informado: edita esa fila (producto/talla/recinto bloqueados).
 * - Si no: alta/ajuste eligiendo producto (y talla si el producto la maneja).
 *
 * El recinto es obligatorio y no puede quedar en blanco. Quien tiene recinto
 * propio lo ve fijo; solo los roles sin recinto asignado (admin) lo eligen —
 * misma regla que aplica `resolver_recinto` en el backend.
 */
const AjusteStockModal = ({ stockRow, productos = [], tallas = [], recintos = [],
                            recintoPropio = null, puedeElegirRecinto = false,
                            onGuardar, onCerrar, guardando, errorServidor }) => {
    const esEdicion = !!stockRow;
    const [productoId, setProductoId] = useState(stockRow?.producto_id ?? '');
    const [tallaId, setTallaId] = useState(stockRow?.talla_id ?? '');
    const [recintoId, setRecintoId] = useState(
        stockRow?.recinto_id ?? recintoPropio ?? ''
    );
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
        if (!recintoId) return setErrorLocal('Selecciona el recinto');
        if (requiereTalla && !tallaId) return setErrorLocal('Este producto requiere talla');
        if (cantidad === '' || Number(cantidad) < 0) return setErrorLocal('Cantidad inválida');
        if (!observacion.trim()) return setErrorLocal('La observación es obligatoria');
        setErrorLocal('');
        onGuardar({
            producto_id: Number(productoId),
            talla_id: requiereTalla ? Number(tallaId) : null,
            recinto_id: Number(recintoId),
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
                        <label className="modal-label">Recinto *</label>
                        {esEdicion || !puedeElegirRecinto ? (
                            <input
                                className="modal-input"
                                value={
                                    stockRow?.nombre_recinto
                                    ?? recintos.find((r) => r.recinto_id === Number(recintoId))?.nombre_recinto
                                    ?? ''
                                }
                                disabled
                            />
                        ) : (
                            <select
                                className="modal-input"
                                value={recintoId}
                                onChange={(e) => setRecintoId(e.target.value)}
                                disabled={guardando}
                            >
                                <option value="">— Selecciona —</option>
                                {recintos.map((r) => (
                                    <option key={r.recinto_id} value={r.recinto_id}>{r.nombre_recinto}</option>
                                ))}
                            </select>
                        )}
                    </div>

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
                                autoFocus={!puedeElegirRecinto}
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
