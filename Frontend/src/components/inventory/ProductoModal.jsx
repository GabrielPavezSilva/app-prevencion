import { useState } from 'react';

/**
 * Modal de alta/edición de producto EPP.
 * onGuardar recibe el objeto con los campos del producto.
 */
const ProductoModal = ({ producto, categorias = [], onGuardar, onCerrar, guardando, errorServidor }) => {
    const esEdicion = !!producto;
    const [form, setForm] = useState({
        nombre: producto?.nombre ?? '',
        categoria_id: producto?.categoria_id ?? '',
        talla_aplica: producto?.talla_aplica ?? false,
        certificacion: producto?.certificacion ?? '',
        descripcion: producto?.descripcion ?? '',
        activo: producto?.activo ?? true,
    });
    const [errorLocal, setErrorLocal] = useState('');

    const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!form.nombre.trim()) {
            setErrorLocal('El nombre es obligatorio');
            return;
        }
        setErrorLocal('');
        onGuardar({
            nombre: form.nombre.trim(),
            categoria_id: form.categoria_id === '' ? null : Number(form.categoria_id),
            talla_aplica: form.talla_aplica,
            certificacion: form.certificacion.trim() || null,
            descripcion: form.descripcion.trim() || null,
            ...(esEdicion ? { activo: form.activo } : {}),
        });
    };

    return (
        <div className="modal-overlay" onClick={onCerrar}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                <h3 className="modal-title">{esEdicion ? 'Editar producto' : 'Nuevo producto'}</h3>

                <form onSubmit={handleSubmit}>
                    <div className="modal-field">
                        <label className="modal-label">Nombre *</label>
                        <input
                            className="modal-input"
                            type="text"
                            value={form.nombre}
                            onChange={(e) => set('nombre', e.target.value)}
                            autoFocus
                            disabled={guardando}
                            placeholder="Ej: Casco de seguridad"
                        />
                    </div>

                    <div className="modal-field">
                        <label className="modal-label">Categoría</label>
                        <select
                            className="modal-input"
                            value={form.categoria_id}
                            onChange={(e) => set('categoria_id', e.target.value)}
                            disabled={guardando}
                        >
                            <option value="">— Sin categoría —</option>
                            {categorias.map((c) => (
                                <option key={c.categoria_id} value={c.categoria_id}>{c.nombre_categoria}</option>
                            ))}
                        </select>
                    </div>

                    <div className="modal-field">
                        <label className="modal-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={form.talla_aplica}
                                onChange={(e) => set('talla_aplica', e.target.checked)}
                                disabled={guardando}
                            />
                            El producto maneja tallas
                        </label>
                    </div>

                    <div className="modal-field">
                        <label className="modal-label">Certificación</label>
                        <input
                            className="modal-input"
                            type="text"
                            value={form.certificacion}
                            onChange={(e) => set('certificacion', e.target.value)}
                            disabled={guardando}
                            placeholder="Ej: EN-397, ANSI Z87"
                        />
                    </div>

                    <div className="modal-field">
                        <label className="modal-label">Descripción</label>
                        <input
                            className="modal-input"
                            type="text"
                            value={form.descripcion}
                            onChange={(e) => set('descripcion', e.target.value)}
                            disabled={guardando}
                            placeholder="Opcional"
                        />
                    </div>

                    {esEdicion && (
                        <div className="modal-field">
                            <label className="modal-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={form.activo}
                                    onChange={(e) => set('activo', e.target.checked)}
                                    disabled={guardando}
                                />
                                Activo
                            </label>
                        </div>
                    )}

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

export default ProductoModal;
