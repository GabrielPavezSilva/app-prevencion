import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './BarChart.css';

const BarChart = ({
    data,
    color = '#0d9488',
    dataKey = 'value',
    nameKey = 'name',
    theme = {},
}) => {
    const grid = theme.grid || '#e2e8f0';
    const axis = theme.axis || '#5a6b80';
    const tipBg = theme.tooltipBg || '#ffffff';
    const tipBorder = theme.tooltipBorder || '#e2e8f0';
    const tipText = theme.tooltipText || '#475569';

    if (!data || data.length === 0) {
        return <div className="bar-chart-empty">Sin datos disponibles</div>;
    }

    return (
        <div className="bar-chart-container">
            <ResponsiveContainer width="100%" height={260}>
                <RechartsBarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={grid} vertical={false} />
                    <XAxis
                        dataKey={nameKey}
                        tick={{ fill: axis, fontSize: 13 }}
                        axisLine={{ stroke: grid }}
                        tickLine={false}
                    />
                    <YAxis
                        tick={{ fill: axis, fontSize: 13 }}
                        axisLine={false}
                        tickLine={false}
                        width={36}
                        allowDecimals={false}
                    />
                    <Tooltip
                        cursor={{ fill: `${color}1f` }}
                        contentStyle={{
                            backgroundColor: tipBg,
                            border: `1px solid ${tipBorder}`,
                            borderRadius: '10px',
                            padding: '8px 12px',
                            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                        }}
                        labelStyle={{ color: tipText, fontSize: 13, fontWeight: 600 }}
                        itemStyle={{ color: color }}
                    />
                    <Bar dataKey={dataKey} fill={color} radius={[6, 6, 0, 0]} maxBarSize={64} />
                </RechartsBarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default BarChart;
