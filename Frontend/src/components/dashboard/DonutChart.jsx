import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORES = ['#0d9488', '#ef8a3d']; // disponible (teal) · en uso (ámbar cálido)

const DonutChart = ({ disponibles, en_uso, theme = {} }) => {
    const tipBg = theme.tooltipBg || '#ffffff';
    const tipBorder = theme.tooltipBorder || '#e2e8f0';
    const tipText = theme.tooltipText || '#475569';
    const legendText = theme.axis || '#475569';

    const data = [
        { name: 'Disponibles', value: disponibles },
        { name: 'En Uso', value: en_uso },
    ];
    const total = disponibles + en_uso;

    if (total === 0) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 240, color: 'var(--color-text-muted)', fontSize: 13 }}>
                Sin datos disponibles
            </div>
        );
    }

    return (
        <div style={{ width: '100%', height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie data={data} cx="50%" cy="50%" innerRadius={62} outerRadius={92} paddingAngle={3} dataKey="value">
                        {data.map((_, index) => (
                            <Cell key={index} fill={COLORES[index]} stroke="none" />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value, name) => [`${value} prendas`, name]}
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
                    <Legend
                        formatter={(value) => (
                            <span style={{ fontSize: 13, color: legendText }}>{value}</span>
                        )}
                    />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
};

export default DonutChart;
