import './MetricCard.css';

// Color semántico por rol -> variable de tema (sigue claro/oscuro).
const toneVar = {
    indigo: '--color-accent-bright',
    teal:   '--color-accent-bright',
    green:  '--color-success',
    red:    '--color-error',
    amber:  '--color-warning',
    blue:   '--color-info',
};

const MetricCard = ({ title, value, subtitle, color = 'teal', icon, index = 0 }) => {
    const tone = `var(${toneVar[color] || toneVar.teal})`;

    return (
        <div
            className="kpi"
            style={{ '--kpi-tone': tone, animationDelay: `${index * 70}ms` }}
        >
            <div className="kpi__row">
                <p className="kpi__label">{title}</p>
                {icon && <span className="kpi__icon">{icon}</span>}
            </div>
            <p className="kpi__value">
                {typeof value === 'number' ? value.toLocaleString('es-CL') : value}
            </p>
            {subtitle && <p className="kpi__sub">{subtitle}</p>}
        </div>
    );
};

export default MetricCard;
