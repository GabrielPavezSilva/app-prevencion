import { useState, useEffect, useCallback } from 'react';
import MetricCard from '../components/dashboard/MetricCard';
import BarChart from '../components/dashboard/BarChart';
import DonutChart from '../components/dashboard/DonutChart';
import TrendChart from '../components/dashboard/TrendChart';
import { getDashboard } from '../services/statsService';
import { getAreas, getEmpresas } from '../services/reportsService';
import { useThemeColors } from '../hooks/useThemeColors';
import './Dashboard.css';

// Los rangos se calculan en hora local del navegador: el backend interpreta
// desde/hasta como fechas locales de Chile y convierte al agregar.
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const RANGOS = [
    {
        id: 'mes', label: 'Mes en curso', meses: 12, calcular: () => {
            const hoy = new Date();
            return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: iso(hoy) };
        },
    },
    {
        id: '3m', label: 'Últimos 3 meses', meses: 12, calcular: () => {
            const hoy = new Date();
            return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth() - 2, 1)), hasta: iso(hoy) };
        },
    },
    {
        id: '6m', label: 'Últimos 6 meses', meses: 12, calcular: () => {
            const hoy = new Date();
            return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth() - 5, 1)), hasta: iso(hoy) };
        },
    },
    {
        id: '12m', label: 'Últimos 12 meses', meses: 12, calcular: () => {
            const hoy = new Date();
            return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth() - 11, 1)), hasta: iso(hoy) };
        },
    },
];

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

const IconEntrega = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
);
const IconPerdida = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="12" r="9" /><line x1="12" y1="8" x2="12" y2="13" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
);
const IconDano = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z" />
    </svg>
);
const IconStock = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8" />
    </svg>
);
const IconSinEpp = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
);

const Dashboard = () => {
    const [data, setData] = useState(null);
    const [rango, setRango] = useState('mes');
    const [empresaId, setEmpresaId] = useState(null);
    const [areaId, setAreaId] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [empresas, setEmpresas] = useState([]);
    const [areas, setAreas] = useState([]);

    const chartTheme = useThemeColors({
        grid:          ['--color-border', '#e2e8f0'],
        axis:          ['--color-text-muted', '#5a6b80'],
        tooltipBg:     ['--color-card', '#ffffff'],
        tooltipBorder: ['--color-card-border', '#e2e8f0'],
        tooltipText:   ['--color-text-secondary', '#475569'],
    });

    const cargar = useCallback(async (rangoId, empresa, area) => {
        setLoading(true);
        setError(null);
        try {
            const def = RANGOS.find((r) => r.id === rangoId) || RANGOS[0];
            const { desde, hasta } = def.calcular();
            setData(await getDashboard({
                desde, hasta, meses: def.meses,
                empresa_id: empresa, area_id: area,
            }));
        } catch (err) {
            console.error('Error cargando dashboard:', err);
            setError(err.message || 'Error al conectar con el servidor');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        Promise.all([
            getEmpresas().catch(() => []),
            getAreas().catch(() => []),
        ]).then(([e, a]) => {
            setEmpresas(Array.isArray(e) ? e : []);
            setAreas(Array.isArray(a) ? a : []);
        }).catch(() => {});
    }, []);

    useEffect(() => { cargar(rango, empresaId, areaId); }, [cargar, rango, empresaId, areaId]);

    // Al elegir empresa, el área seleccionada puede no pertenecerle: se limpia.
    const cambiarEmpresa = (valor) => {
        setEmpresaId(valor);
        setAreaId(null);
    };

    if (error && !data) {
        return (
            <div className="dash-error">
                <p>{error}</p>
                <button className="btn btn-primary" onClick={() => cargar(rango, empresaId, areaId)}>
                    Reintentar
                </button>
            </div>
        );
    }

    const k = data?.kpis;
    const areasVisibles = empresaId == null
        ? areas
        : areas.filter((a) => a.empresa_id === empresaId);
    const hayFiltro = empresaId != null || areaId != null || rango !== 'mes';
    const n = (arr) => (arr || []).length;
    const pctSinEpp = k?.trabajadores_activos
        ? Math.round((k.trabajadores_sin_epp / k.trabajadores_activos) * 100)
        : 0;

    return (
        <div className="dashboard">
            {/* ── Barra de filtros ── */}
            <div className="dash-toolbar">
                <span className="dash-toolbar__label">Periodo</span>
                <select className="dash-filter" value={rango} onChange={(e) => setRango(e.target.value)}>
                    {RANGOS.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
                </select>
                <select className="dash-filter" value={empresaId ?? ''}
                    onChange={(e) => cambiarEmpresa(e.target.value === '' ? null : Number(e.target.value))}>
                    <option value="">Todas las empresas</option>
                    {empresas.map((e) => (
                        <option key={e.empresa_id} value={e.empresa_id}>{e.nombre_empresa}</option>
                    ))}
                </select>
                <select className="dash-filter" value={areaId ?? ''}
                    onChange={(e) => setAreaId(e.target.value === '' ? null : Number(e.target.value))}
                    disabled={areasVisibles.length === 0}>
                    <option value="">Todas las áreas</option>
                    {areasVisibles.map((a) => (
                        <option key={a.area_id} value={a.area_id}>
                            {empresaId == null && a.nombre_empresa
                                ? `${a.nombre_area} · ${a.nombre_empresa}`
                                : a.nombre_area}
                        </option>
                    ))}
                </select>
                {hayFiltro && (
                    <button className="dash-btn-clear" onClick={() => {
                        setRango('mes'); setEmpresaId(null); setAreaId(null);
                    }}>Limpiar</button>
                )}
                {loading && data && <span className="dash-updating">Actualizando…</span>}
            </div>

            {/* ── KPIs del periodo ── */}
            <div className="dash-kpis">
                {loading && !data ? (
                    <><CardSkeleton /><CardSkeleton /><CardSkeleton /><CardSkeleton /></>
                ) : (
                    <>
                        <MetricCard title="Entregas del periodo" value={k.entregas_periodo} color="teal" index={0}
                            subtitle={`${k.lineas_periodo} ${k.lineas_periodo === 1 ? 'registro' : 'registros'} · ${k.trabajadores_atendidos} trabajadores`}
                            icon={<IconEntrega />} />
                        <MetricCard title="Reposiciones por pérdida" value={k.reposiciones_perdida} color="amber" index={1}
                            subtitle="unidades repuestas en el periodo" icon={<IconPerdida />} />
                        <MetricCard title="Sustituciones por daño" value={k.sustituciones_dano} color="red" index={2}
                            subtitle="unidades sustituidas en el periodo" icon={<IconDano />} />
                        <MetricCard title="Productos bajo mínimo" value={k.productos_bajo_minimo} color="blue" index={3}
                            subtitle={k.productos_en_quiebre > 0
                                ? `${k.productos_en_quiebre} en quiebre total`
                                : 'sin quiebres'}
                            icon={<IconStock />} />
                    </>
                )}
            </div>

            {/* ── Secciones ── */}
            {data && (
                <div className="dash-sections">
                    <Section id="tendencia" title="Tendencia de entregas" defaultOpen
                        chip={`${n(data.serie_mensual)} meses`}>
                        <Panel title="Entregas por mes"
                            subtitle="Unidades entregadas, apiladas por motivo. La ventana es independiente del periodo de las tarjetas.">
                            <TrendChart data={data.serie_mensual} theme={chartTheme} />
                        </Panel>
                    </Section>

                    <Section id="motivos" title="Motivos" chip={`${n(data.por_motivo)} motivos`}>
                        <div className="dash-grid dash-grid--split">
                            <Panel title="Distribución por motivo" subtitle="Nueva · pérdida · daño en el periodo">
                                <DonutChart data={data.por_motivo} theme={chartTheme} />
                            </Panel>
                        </div>
                    </Section>

                    <Section id="distribucion" title="Distribución"
                        chip={`${n(data.por_area)} áreas`}>
                        <div className="dash-grid dash-grid--2">
                            <Panel title="Por área" subtitle="Dónde se está consumiendo el EPP">
                                <BarChart data={toBarData(data.por_area)} color="#0d9488" theme={chartTheme} />
                            </Panel>
                            <Panel title="Productos más entregados" subtitle="Top 10 del periodo">
                                <BarChart data={toBarData(data.top_productos)} color="#6366f1" theme={chartTheme} />
                            </Panel>
                        </div>
                    </Section>

                    <Section id="cobertura" title="Cobertura de personal"
                        chip={`${k.trabajadores_sin_epp} sin EPP`}>
                        <div className="dash-kpis" style={{ marginBottom: 0 }}>
                            <MetricCard title="Trabajadores activos" value={k.trabajadores_activos}
                                color="teal" subtitle="según la última sincronización con RRHH"
                                icon={<IconSinEpp />} />
                            <MetricCard title="Sin ningún EPP vigente" value={k.trabajadores_sin_epp}
                                color={k.trabajadores_sin_epp > 0 ? 'red' : 'green'}
                                subtitle={`${pctSinEpp}% de la dotación activa`} icon={<IconSinEpp />} />
                            <MetricCard title="Unidades en bodega" value={k.unidades_en_bodega}
                                color="blue" subtitle="stock disponible total" icon={<IconStock />} />
                        </div>
                    </Section>

                    <Section id="alertas" title="Alertas de stock"
                        chip={`${n(data.alertas_stock)} productos`}>
                        <Panel title="En o bajo el mínimo"
                            subtitle="Los 10 más críticos. El detalle completo está en Reportes → Stock.">
                            {data.alertas_stock.length === 0 ? (
                                <p style={{ color: 'var(--color-text-muted)', fontSize: 13, padding: '8px 0' }}>
                                    Ningún producto está bajo su stock mínimo.
                                </p>
                            ) : (
                                <table className="dash-alertas">
                                    <thead>
                                        <tr>
                                            <th>Producto</th><th>Talla</th>
                                            <th style={{ textAlign: 'right' }}>Actual</th>
                                            <th style={{ textAlign: 'right' }}>Mínimo</th>
                                            <th style={{ textAlign: 'center' }}>Estado</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.alertas_stock.map((r, i) => (
                                            <tr key={i}>
                                                <td>{r.producto}</td>
                                                <td>{r.talla || '—'}</td>
                                                <td style={{ textAlign: 'right' }}>{r.cantidad_actual}</td>
                                                <td style={{ textAlign: 'right' }}>{r.stock_minimo}</td>
                                                <td style={{ textAlign: 'center' }}>
                                                    <span className={`dash-badge dash-badge--${r.estado.toLowerCase()}`}>
                                                        {r.estado}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </Panel>
                    </Section>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
