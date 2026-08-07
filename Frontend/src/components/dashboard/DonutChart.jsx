import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Paleta por posición. En el dashboard EPP el backend ordena los motivos por
// cantidad, así que el color no es semántico por motivo.
const COLORES = ['#0d9488', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6'];

/**
 * Donut genérico sobre una lista `[{ nombre, cantidad }]`.
 *
 * Antes recibía `disponibles`/`en_uso` del dominio lavandería; se generalizó en
 * Fase 5 para servir a cualquier distribución (motivos, categorías, etc.).
 */
const DonutChart = ({ data, unidad = 'unidades', theme = {} }) => {
    const tipBg = theme.tooltipBg || '#ffffff';
    const tipBorder = theme.tooltipBorder || '#e2e8f0';
    const tipText = theme.tooltipText || '#475569';
    const legendText = theme.axis || '#475569';

    const filas = (data || []).map((d) => ({ name: d.nombre, value: d.cantidad }));
    const total = filas.reduce((acc, d) => acc + (d.value || 0), 0);

    if (total === 0) {
        return (
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: 240, color: 'var(--color-text-muted)', fontSize: 13,
            }}>
                Sin datos disponibles
            </div>
        );
    }

    return (
        <div style={{ width: '100%', height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie data={filas} cx="50%" cy="50%" innerRadius={62} outerRadius={92}
                        paddingAngle={3} dataKey="value">
                        {filas.map((_, index) => (
                            <Cell key={index} fill={COLORES[index % COLORES.length]} stroke="none" />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value, name) => [`${value} ${unidad}`, name]}
                        contentStyle={{
                            backgroundColor: tipBg,
                            border: `1px solid ${tipBorder}`,
                            borderRadius: '10px',
                            padding: '8px 12px',
                            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                        }}
                        labelStyle={{ color: tipText }}
                        itemStyle={{ color: tipText }}
                    />
                    <Legend formatter={(value) => (
                        <span style={{ fontSize: 13, color: legendText }}>{value}</span>
                    )} />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
};

export default DonutChart;
