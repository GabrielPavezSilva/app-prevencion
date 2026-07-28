import {
    BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import './BarChart.css';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

// 'YYYY-MM' -> 'jul 26'. Se formatea desde el string y no con new Date(): un
// Date('2026-07') se interpreta en UTC y en Chile retrocede al mes anterior.
const etiquetaMes = (mes) => {
    const [anio, m] = (mes || '').split('-');
    return `${MESES[Number(m) - 1] ?? mes} ${anio?.slice(2) ?? ''}`;
};

const SERIES = [
    { key: 'nueva', label: 'Nueva', color: '#0d9488' },
    { key: 'perdida', label: 'Reposición por pérdida', color: '#f59e0b' },
    { key: 'dano', label: 'Sustitución por daño', color: '#ef4444' },
];

/**
 * Entregas por mes, apiladas por motivo.
 *
 * El backend devuelve todos los meses de la ventana, incluidos los que no
 * tuvieron entregas (en 0): si faltaran, Recharts dibujaría un hueco y se
 * leería como un error de datos.
 */
const TrendChart = ({ data, theme = {} }) => {
    const grid = theme.grid || '#e2e8f0';
    const axis = theme.axis || '#5a6b80';
    const tipBg = theme.tooltipBg || '#ffffff';
    const tipBorder = theme.tooltipBorder || '#e2e8f0';
    const tipText = theme.tooltipText || '#475569';

    if (!data || data.length === 0) {
        return <div className="bar-chart-empty">Sin datos disponibles</div>;
    }

    const filas = data.map((p) => ({ ...p, etiqueta: etiquetaMes(p.mes) }));

    return (
        <div className="bar-chart-container">
            <ResponsiveContainer width="100%" height={280}>
                <RechartsBarChart data={filas} margin={{ top: 16, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={grid} vertical={false} />
                    <XAxis dataKey="etiqueta" tick={{ fill: axis, fontSize: 12 }}
                        axisLine={{ stroke: grid }} tickLine={false} />
                    <YAxis tick={{ fill: axis, fontSize: 13 }} axisLine={false}
                        tickLine={false} width={36} allowDecimals={false} />
                    <Tooltip
                        cursor={{ fill: 'rgba(13,148,136,0.10)' }}
                        contentStyle={{
                            backgroundColor: tipBg,
                            border: `1px solid ${tipBorder}`,
                            borderRadius: '10px',
                            padding: '8px 12px',
                            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                        }}
                        labelStyle={{ color: tipText, fontSize: 13, fontWeight: 600 }}
                        formatter={(value, name) => [`${value} unidades`, name]}
                    />
                    <Legend formatter={(value) => (
                        <span style={{ fontSize: 12, color: axis }}>{value}</span>
                    )} />
                    {SERIES.map((s) => (
                        <Bar key={s.key} dataKey={s.key} name={s.label} stackId="motivo"
                            fill={s.color} maxBarSize={54} />
                    ))}
                </RechartsBarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default TrendChart;
