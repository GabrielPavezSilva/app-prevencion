import { useState } from 'react';

const CatalogoModal = ({ titulo, valorInicial = '', onGuardar, onCerrar, guardando, errorServidor }) => {
    const [nombre, setNombre] = useState(valorInicial);
    const [errorLocal, setErrorLocal] = useState('');

    const [prevValorInicial, setPrevValorInicial] = useState(valorInicial);

    if (prevValorInicial !== valorInicial) {
        setNombre(valorInicial);
        setPrevValorInicial(valorInicial);
        setErrorLocal('');
    }

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!nombre.trim()) {
            setErrorLocal('El nombre no puede estar vacío');
            return;
        }
        setErrorLocal('');
        onGuardar(nombre.trim());
    };

    return (
        <div className="modal-overlay" onClick={onCerrar}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                <h3 className="modal-title">{titulo}</h3>

                <form onSubmit={handleSubmit}>
                    <div className="modal-field">
                        <label className="modal-label">Nombre</label>
                        <input
                            className="modal-input"
                            type="text"
                            value={nombre}
                            onChange={(e) => setNombre(e.target.value)}
                            autoFocus
                            disabled={guardando}
                            placeholder="Ingresa el nombre..."
                        />
                        {errorLocal && (
                            <p className="modal-error">{errorLocal}</p>
                        )}
                        {errorServidor && (
                            <p className="modal-error">{errorServidor}</p>
                        )}
                    </div>

                    <div className="modal-actions">
                        <button
                            type="button"
                            className="catalogo-btn catalogo-btn--cancel"
                            onClick={onCerrar}
                            disabled={guardando}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className="catalogo-btn catalogo-btn--primary"
                            disabled={guardando}
                        >
                            {guardando ? 'Guardando...' : 'Guardar'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CatalogoModal;
