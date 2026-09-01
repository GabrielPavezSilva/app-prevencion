import { useState } from 'react';
import PadFirma from './PadFirma';

/**
 * Acta de entrega: detalle de lo que se entrega + firma del trabajador.
 * Sin firma no se habilita la confirmación.
 *
 * El PDF no se genera acá: al confirmar se manda la firma al backend, que arma
 * el acta y la guarda. Así el documento existe aunque nadie lo descargue.
 *
 * La firma se captura en `PadFirma`, a pantalla completa — ver el porqué ahí.
 */
const ActaEntrega = ({ trabajador, lineas, motivos, onConfirmar, onCerrar, confirmando }) => {
    const [firma, setFirma] = useState(null);      // PNG data URL, recortado al trazo
    const [firmando, setFirmando] = useState(false);
    const [ahora] = useState(() => new Date());

    const fmt = (d) => d.toLocaleDateString('es-CL');
    const hora = (d) => d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
    const nombreItem = (l) => [l.nombre, l.nombre_talla].filter(Boolean).join(' · ');

    if (firmando) {
        return (
            <PadFirma
                onListo={(png) => { setFirma(png); setFirmando(false); }}
                onCancelar={() => setFirmando(false)} />
        );
    }

    return (
        <div className="modal-overlay" onClick={confirmando ? undefined : onCerrar}>
            <style>{`
                .acta-fila { display: flex; justify-content: space-between; gap: 12px;
                             padding: 6px 0; border-bottom: 1px solid var(--color-card-border);
                             font-size: 14px; }
                .acta-dato { font-size: 13px; color: var(--color-text-secondary); }
                .acta-dato strong { color: var(--color-text-primary); }
            `}</style>

            <div className="modal-box" style={{ maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
                <h3 className="modal-title">Acta de entrega de EPP</h3>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 16 }}>
                    <p className="acta-dato">Empresa: <strong>{trabajador.empresa}</strong></p>
                    <p className="acta-dato">Fecha: <strong>{fmt(ahora)}</strong></p>
                    <p className="acta-dato">Trabajador: <strong>{trabajador.nombre_completo}</strong></p>
                    <p className="acta-dato">Hora: <strong>{hora(ahora)}</strong></p>
                    <p className="acta-dato">RUT: <strong>{trabajador.rut}</strong></p>
                    {trabajador.cargo && <p className="acta-dato">Cargo: <strong>{trabajador.cargo}</strong></p>}
                </div>

                <div style={{ marginBottom: 16 }}>
                    {lineas.map((l, i) => (
                        <div key={i} className="acta-fila">
                            <span>{nombreItem(l)} × {l.cantidad}</span>
                            <span className="acta-dato">{motivos.find((m) => m.v === l.motivo)?.label}</span>
                        </div>
                    ))}
                </div>

                <p className="acta-dato" style={{ marginBottom: 6 }}>
                    Firma del trabajador — declara recibir conforme los EPP detallados.
                </p>

                <div style={{
                    border: '1px solid var(--color-card-border)', borderRadius: 8, background: '#fff',
                    height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    {firma
                        ? <img src={firma} alt="Firma del trabajador"
                               style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }} />
                        : <button type="button" className="catalogo-btn catalogo-btn--edit"
                                  onClick={() => setFirmando(true)} disabled={confirmando}>
                              Firmar acta
                          </button>}
                </div>

                <div className="modal-actions">
                    <button type="button" className="catalogo-btn catalogo-btn--cancel"
                        onClick={() => setFirmando(true)} disabled={confirmando || !firma}>
                        Volver a firmar
                    </button>
                    <button type="button" className="catalogo-btn catalogo-btn--cancel"
                        onClick={onCerrar} disabled={confirmando}>Cancelar</button>
                    <button type="button" className="catalogo-btn catalogo-btn--primary"
                        onClick={() => onConfirmar(firma)} disabled={!firma || confirmando}>
                        {confirmando ? 'Registrando…' : 'Confirmar entrega'}
                    </button>
                </div>
                {!firma && (
                    <p className="modal-error">El acta debe estar firmada para confirmar la entrega.</p>
                )}
            </div>
        </div>
    );
};

export default ActaEntrega;
