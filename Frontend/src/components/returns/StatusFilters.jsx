import './StatusFilters.css';

const StatusFilters = ({ activeFilter, onFilterChange }) => {
    const filters = [
        { id: 'PENDIENTE', label: 'PENDIENTE' },
        { id: 'Vencido', label: 'Vencido' },
        { id: 'Seguridad', label: 'Seguridad' }
    ];

    return (
        <div className="status-filters">
            {filters.map((filter) => (
                <button
                    key={filter.id}
                    className={`filter-tab ${activeFilter === filter.id ? 'active' : ''}`}
                    onClick={() => onFilterChange(filter.id)}
                >
                    {filter.label}
                </button>
            ))}
        </div>
    );
};

export default StatusFilters;
