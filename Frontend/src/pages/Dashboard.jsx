import { useState, useEffect, useCallback } from 'react';
import MetricCard from '../components/dashboard/MetricCard';
import BarChart from '../components/dashboard/BarChart';
import DonutChart from '../components/dashboard/DonutChart';
import { getStatsInventario } from '../services/statsService';
import { getTipos, getTallas, getSecciones, getTemporadas } from '../services/catalogosService';
import { apiClient } from '../services/api';
import { useThemeColors } from '../hooks/useThemeColors';
import './Dashboard.css';

const FILTROS_VACIOS = {
    tipo_id: null, talla_id: null,
    empresa_id: null, seccion_id: null, temporada_id: null,
};

const toBarData = (items) =>
    (items || []).map((item) => ({ name: item.nombre, value: item.cantidad }));

function CardSkeleton() {
    return (
        <div className="kpi-skeleton">
            <div className="skeleton" style={{ height: 12, width: '50%', marginBottom: 16 }} />
            <div className="skeleton" style={{ height: 28, width: '40%' }} />
        </div>
    );
}

const Chevron = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="9 18 15 12 9 6" />
    </svg>
);

/** Sección colapsable (native <details>, accesible, con estado recordado). */
function Section({ id, title, chip, defaultOpen = false, children }) {
    const storeKey = `dash-open:${id}`;
    const [open, setOpen] = useState(() => {
        const s = typeof localStorage !== 'undefined' ? localStorage.getItem(storeKey) : null;
        return s === null ? defaultOpen : s === '1';
    });

    const onToggle = (e) => {
        setOpen(e.currentTarget.open);
        try { localStorage.setItem(storeKey, e.currentTarget.open ? '1' : '0'); } catch { /* ignore */ }
    };

    return (
        <details className="dash-section" open={open} onToggle={onToggle}>
            <summary className="dash-section__head">
                <span className="dash-section__chev"><Chevron /></span>
                <h2 className="dash-section__title">{title}</h2>
                {chip != null && <span className="dash-section__chip">{chip}</span>}
            </summary>
            <div className="dash-section__body">{children}</div>
        </details>
    );
}

function Panel({ title, subtitle, children }) {
    return (
        <section className="dash-panel">
            <div className="dash-panel__head">
                <h3 className="dash-panel__title">{title}</h3>
                {subtitle && <p className="dash-panel__sub">{subtitle}</p>}
            </div>
            {children}
        </section>
    );
}

const Dashboard = () => {
    const [stats, setStats]       = useState(null);
    const [filtros, setFiltros]   = useState(FILTROS_VACIOS);
    const [loading, setLoading]   = useState(true);
    const [error, setError]       = useState(null);

    const [tipos, setTipos]           = useState([]);
    const [tallas, setTallas]         = useState([]);
    const [secciones, setSecciones]   = useState([]);
    const [temporadas, setTemporadas] = useState([]);
    const [empresas, setEmpresas]     = useState([]);

    const chartTheme = useThemeColors({
        grid:          ['--color-border', '#e2e8f0'],
        axis:          ['--color-text-muted', '#5a6b80'],
        tooltipBg:     ['--color-card', '#ffffff'],
        tooltipBorder: ['--color-card-border', '#e2e8f0'],
        tooltipText:   ['--color-text-secondary', '#475569'],
    });

    const cargar = useCallback(async (f) => {
        setLoading(true);
        setError(null);
        try {
            const data = await getStatsInventario(f);
            setStats(data);
        } catch (err) {
            console.error('Error cargando dashboard:', err);
            setError(err.message || 'Error al conectar con el servidor');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        Promise.all([
            getTipos(),
            getTallas(),
            getSecciones(),
            getTemporadas(),
            apiClient.get('/inventario/empresas').catch(() => []),
        ]).then(([t, ta, s, temp, e]) => {
            setTipos(t);
            setTallas(ta);
            setSecciones(s);
            setTemporadas(temp);
            setEmpresas(Array.isArray(e) ? e : []);
        }).catch(() => {});
        cargar(FILTROS_VACIOS);
    }, [cargar]);

    const setFiltro = (key, value) => {
        const nuevos = { ...filtros, [key]: value };
        if (key === 'tipo_id') nuevos.talla_id = null;
        setFiltros(nuevos);
        cargar(nuevos);
    };

    const limpiarFiltros = () => {
        setFiltros(FILTROS_VACIOS);
        cargar(FILTROS_VACIOS);
    };

    if (error && !stats) {
        return (
            <div className="dash-error">
                <p>{error}</p>
                <button className="btn btn-primary" onClick={() => cargar(filtros)}>Reintentar</button>
            </div>
        );
    }

    const total       = stats?.total       ?? 0;
    const disponibles = stats?.disponibles ?? 0;
    const en_uso      = stats?.en_uso      ?? 0;
    const pctDisp     = total > 0 ? Math.round(disponibles / total * 100) : 0;

    const tallasConStock = new Set((stats?.por_talla || []).map((t) => t.nombre));
    const tallaOpciones = filtros.tipo_id !== null
        ? tallas.filter((ta) => tallasConStock.has(ta.nombreTalla))
        : tallas;

    const hayFiltro = Object.values(filtros).some((v) => v !== null);
    const n = (arr) => (arr || []).length;

    return (
        <div className="dashboard">
            {/* ── Barra de filtros (estilo control BI) ── */}
            <div className="dash-toolbar">
                <span className="dash-toolbar__label">Filtros</span>
                <select className="dash-filter" value={filtros.tipo_id ?? ''}
                    onChange={(e) => setFiltro('tipo_id', e.target.value === '' ? null : Number(e.target.value))}>
                    <option value="">Todos los tipos</option>
                    {tipos.map((t) => <option key={t.TipoID} value={t.TipoID}>{t.nombreTipo}</option>)}
                </select>
                <select className="dash-filter" value={filtros.talla_id ?? ''}
                    onChange={(e) => setFiltro('talla_id', e.target.value === '' ? null : Number(e.target.value))}
                    disabled={tallaOpciones.length === 0}>
                    <option value="">Todas las tallas</option>
                    {tallaOpciones.map((ta) => <option key={ta.TallaID} value={ta.TallaID}>{ta.nombreTalla}</option>)}
                </select>
                <select className="dash-filter" value={filtros.empresa_id ?? ''}
                    onChange={(e) => setFiltro('empresa_id', e.target.value === '' ? null : Number(e.target.value))}>
                    <option value="">Todas las empresas</option>
                    {empresas.map((e) => <option key={e.empresa_id} value={e.empresa_id}>{e.nombre_empresa}</option>)}
                </select>
                <select className="dash-filter" value={filtros.seccion_id ?? ''}
                    onChange={(e) => setFiltro('seccion_id', e.target.value === '' ? null : Number(e.target.value))}>
                    <option value="">Todas las secciones</option>
                    {secciones.map((s) => <option key={s.SeccionID} value={s.SeccionID}>{s.nombreSeccion}</option>)}
                </select>
                <select className="dash-filter" value={filtros.temporada_id ?? ''}
                    onChange={(e) => setFiltro('temporada_id', e.target.value === '' ? null : Number(e.target.value))}>
                    <option value="">Todas las temporadas</option>
                    {temporadas.map((t) => <option key={t.TemporadaID} value={t.TemporadaID}>{t.nombreTemporada}</option>)}
                </select>
                {hayFiltro && (
                    <button className="dash-btn-clear" onClick={limpiarFiltros}>Limpiar</button>
                )}
                {loading && stats && <span className="dash-updating">Actualizando…</span>}
            </div>

            {/* ── Resumen (siempre visible) ── */}
            <div className="dash-kpis">
                {loading && !stats ? (
                    <><CardSkeleton /><CardSkeleton /><CardSkeleton /></>
                ) : (
                    <>
                        <MetricCard title="Existencias totales" value={total} color="teal" index={0}
                            subtitle={hayFiltro ? 'prendas filtradas' : 'prendas en el sistema'}
                            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8" /></svg>} />
                        <MetricCard title="Disponibles" value={disponibles} color="green" index={1}
                            subtitle={total > 0 ? `${pctDisp}% del total` : 'sin asignar'}
                            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M20 6L9 17l-5-5" /></svg>} />
                        <MetricCard title="En uso" value={en_uso} color="amber" index={2}
                            subtitle={total > 0 ? `${100 - pctDisp}% del total` : 'asignadas'}
                            icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>} />
                    </>
                )}
            </div>

            {/* ── Categorías colapsables ── */}
            <div className="dash-sections">
                <Section id="disponibilidad" title="Disponibilidad" chip={`${pctDisp}% disp.`}>
                    <div className="dash-grid dash-grid--split">
                        <Panel title="Disponibles vs. en uso" subtitle="Estado actual del inventario">
                            <DonutChart disponibles={disponibles} en_uso={en_uso} theme={chartTheme} />
                        </Panel>
                    </div>
                </Section>

                <Section id="distribucion" title="Distribución de prendas" chip={`${n(stats?.por_tipo)} tipos`}>
                    <div className="dash-grid dash-grid--2">
                        <Panel title="Por tipo de prenda" subtitle={filtros.tipo_id ? 'Tipo seleccionado' : 'Por categoría'}>
                            <BarChart data={toBarData(stats?.por_tipo)} color="#0d9488" theme={chartTheme} />
                        </Panel>
                        <Panel title="Por talla" subtitle={filtros.tipo_id ? 'Tallas del tipo' : 'Distribución de tallas'}>
                            <BarChart data={toBarData(stats?.por_talla)} color="#2563eb" theme={chartTheme} />
                        </Panel>
                    </div>
                </Section>

                <Section id="empresa" title="Por empresa" chip={`${n(stats?.por_empresa)} empresas`}>
                    <Panel title="Prendas por empresa cliente" subtitle="Reparto del inventario">
                        <BarChart data={toBarData(stats?.por_empresa)} color="#14b8a6" theme={chartTheme} />
                    </Panel>
                </Section>

                <Section id="seccion" title="Por área / sección" chip={`${n(stats?.por_seccion)} secciones`}>
                    <Panel title="Distribución por sección" subtitle="Dónde se usan las prendas">
                        <BarChart data={toBarData(stats?.por_seccion)} color="#f59e0b" theme={chartTheme} />
                    </Panel>
                </Section>

                <Section id="temporada" title="Por temporada" chip={`${n(stats?.por_temporada)} temporadas`}>
                    <Panel title="Distribución por temporada" subtitle="Verano / invierno">
                        <BarChart data={toBarData(stats?.por_temporada)} color="#8b5cf6" theme={chartTheme} />
                    </Panel>
                </Section>
            </div>
        </div>
    );
};

export default Dashboard;
