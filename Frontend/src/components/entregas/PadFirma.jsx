import { useRef, useEffect, useState, useCallback } from 'react';

/**
 * Pad de firma a pantalla completa.
 *
 * A pantalla completa a propósito: una tableta gráfica en modo absoluto mapea
 * toda su superficie a toda la pantalla, así que firmar dentro de un recuadro
 * chico obliga a trazar en unos pocos centímetros cuadrados de la tableta. Con
 * el lienzo ocupando la ventana, la relación queda casi 1:1.
 *
 * No se usa Pointer Lock: entrega desplazamientos relativos y un digitalizador
 * absoluto los reporta a saltos, con lo que el trazo sale entrecortado.
 *
 * Devuelve el PNG recortado al trazo (`onListo`), no el lienzo completo: si no,
 * la firma viajaría como una mancha chica dentro de una imagen enorme y en el
 * PDF saldría diminuta.
 */
const PADDING = 12;   // margen en px alrededor del trazo al recortar

const PadFirma = ({ onListo, onCancelar }) => {
    const canvasRef = useRef(null);
    const dibujando = useRef(false);
    const dpr = useRef(1);
    // Caja del trazo en px CSS, para recortar al final.
    const caja = useRef(null);
    const [hayTrazo, setHayTrazo] = useState(false);

    useEffect(() => {
        const canvas = canvasRef.current;
        dpr.current = window.devicePixelRatio || 1;
        canvas.width = window.innerWidth * dpr.current;
        canvas.height = window.innerHeight * dpr.current;
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr.current, dpr.current);
        ctx.lineWidth = 2.6;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.strokeStyle = '#0f172a';
    }, []);

    const marcar = (x, y) => {
        const c = caja.current;
        if (!c) caja.current = { x0: x, y0: y, x1: x, y1: y };
        else {
            c.x0 = Math.min(c.x0, x); c.y0 = Math.min(c.y0, y);
            c.x1 = Math.max(c.x1, x); c.y1 = Math.max(c.y1, y);
        }
    };

    const posicion = (e) => {
        const r = canvasRef.current.getBoundingClientRect();
        return { x: e.clientX - r.left, y: e.clientY - r.top };
    };

    const empezar = (e) => {
        e.preventDefault();
        canvasRef.current.setPointerCapture(e.pointerId);
        dibujando.current = true;
        const { x, y } = posicion(e);
        marcar(x, y);
        const ctx = canvasRef.current.getContext('2d');
        ctx.beginPath();
        ctx.moveTo(x, y);
        // Un toque sin arrastre también deja punto: la firma puede tener puntos.
        ctx.lineTo(x, y);
        ctx.stroke();
        setHayTrazo(true);
    };

    const mover = (e) => {
        if (!dibujando.current) return;
        e.preventDefault();
        const ctx = canvasRef.current.getContext('2d');
        // getCoalescedEvents recupera las muestras que el navegador agrupó entre
        // dos frames: una tableta reporta muy por encima de 60 Hz y sin esto el
        // trazo sale poligonal.
        const puntos = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
        for (const p of (puntos.length ? puntos : [e])) {
            const { x, y } = posicion(p);
            marcar(x, y);
            ctx.lineTo(x, y);
        }
        ctx.stroke();
    };

    const terminar = () => { dibujando.current = false; };

    const limpiar = useCallback(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.restore();
        caja.current = null;
        setHayTrazo(false);
    }, []);

    // Recorta al trazo y devuelve el PNG.
    const listo = useCallback(() => {
        const c = caja.current;
        if (!c) return;
        const k = dpr.current;
        const x = Math.max(0, (c.x0 - PADDING) * k);
        const y = Math.max(0, (c.y0 - PADDING) * k);
        const w = Math.max(1, (c.x1 - c.x0 + PADDING * 2) * k);
        const h = Math.max(1, (c.y1 - c.y0 + PADDING * 2) * k);
        const recorte = document.createElement('canvas');
        recorte.width = w;
        recorte.height = h;
        recorte.getContext('2d').drawImage(canvasRef.current, x, y, w, h, 0, 0, w, h);
        onListo(recorte.toDataURL('image/png'));
    }, [onListo]);

    // Atajos: barra espaciadora confirma (el lápiz no tiene botón cómodo a mano),
    // Escape cancela.
    useEffect(() => {
        const onKey = (e) => {
            if (e.key === ' ' && hayTrazo) { e.preventDefault(); listo(); }
            if (e.key === 'Escape') onCancelar();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [hayTrazo, listo, onCancelar]);

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 1000, background: '#fff',
            display: 'flex', flexDirection: 'column',
        }}>
            <canvas ref={canvasRef}
                onPointerDown={empezar} onPointerMove={mover}
                onPointerUp={terminar} onPointerCancel={terminar}
                style={{ position: 'absolute', inset: 0, width: '100%', height: '100%',
                         touchAction: 'none', cursor: 'crosshair' }} />

            {/* Línea de apoyo y textos van en el DOM, no en el lienzo: así no
                terminan dentro del PNG de la firma. */}
            <div style={{ position: 'absolute', left: '10%', right: '10%', bottom: '30%',
                          borderBottom: '2px dashed #cbd5e1', pointerEvents: 'none' }} />
            {!hayTrazo && (
                <p style={{ position: 'absolute', left: 0, right: 0, bottom: 'calc(30% - 34px)',
                            textAlign: 'center', color: '#94a3b8', fontSize: 15,
                            pointerEvents: 'none' }}>
                    Firme sobre la línea con el lápiz
                </p>
            )}

            <div style={{ position: 'absolute', top: 16, left: 0, right: 0, display: 'flex',
                          justifyContent: 'center', gap: 10 }}>
                <button type="button" className="catalogo-btn catalogo-btn--cancel"
                    onClick={onCancelar}>Cancelar (Esc)</button>
                <button type="button" className="catalogo-btn catalogo-btn--cancel"
                    onClick={limpiar} disabled={!hayTrazo}>Borrar</button>
                <button type="button" className="catalogo-btn catalogo-btn--primary"
                    onClick={listo} disabled={!hayTrazo}>Listo (barra espaciadora)</button>
            </div>
        </div>
    );
};

export default PadFirma;
