const ConfirmDeleteModal = ({ mensaje, errorServidor, onConfirmar, onCerrar, eliminando }) => (
    <div className="modal-overlay" onClick={onCerrar}>
        <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Confirmar eliminación</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>{mensaje}</p>

            {errorServidor && (
                <p className="modal-error" style={{ marginBottom: '1rem' }}>{errorServidor}</p>
            )}

            <div className="modal-actions">
                <button
                    className="catalogo-btn catalogo-btn--cancel"
                    onClick={onCerrar}
                    disabled={eliminando}
                >
                    Cancelar
                </button>
                <button
                    className="catalogo-btn catalogo-btn--delete"
                    onClick={onConfirmar}
                    disabled={eliminando}
                >
                    {eliminando ? 'Eliminando...' : 'Eliminar'}
                </button>
            </div>
        </div>
    </div>
);

export default ConfirmDeleteModal;
