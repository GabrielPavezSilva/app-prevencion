import './EmployeeReturnsList.css';
import StatusFilters from './StatusFilters';

const EmployeeReturnsList = ({ employees, selectedEmployee, onSelectEmployee, activeFilter, onFilterChange, loading }) => {
    const getInitials = (name) => {
        const parts = name.split(' ');
        if (parts.length >= 2) {
            return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    };

    if (loading) {
        return (
            <div className="returns-list-container">
                <div className="returns-list-loading">
                    <div className="loading"></div>
                    <p>Cargando empleados...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="returns-list-container">
            <div className="returns-list-search">
                <span className="search-icon">🔍</span>
                <input
                    type="text"
                    placeholder="Buscar empleado..."
                    className="search-input-returns"
                />
            </div>

            <StatusFilters activeFilter={activeFilter} onFilterChange={onFilterChange} />

            <div className="returns-list">
                {employees.length === 0 ? (
                    <div className="returns-list-empty">
                        <p>No hay empleados con devoluciones pendientes</p>
                    </div>
                ) : (
                    employees.map((employee) => (
                        <div
                            key={employee.id}
                            className={`employee-return-item ${selectedEmployee?.id === employee.id ? 'selected' : ''}`}
                            onClick={() => onSelectEmployee(employee)}
                        >
                            <div className="employee-return-avatar">
                                {getInitials(employee.name)}
                            </div>
                            <div className="employee-return-info">
                                <div className="employee-return-name">{employee.name}</div>
                                <div className="employee-return-meta">
                                    {employee.id} • {employee.department}
                                </div>
                            </div>
                            <div className="employee-return-badges">
                                {employee.returnStatus === 'Vencido' && (
                                    <span className="status-badge status-overdue">Vencido</span>
                                )}
                                {employee.returnStatus === 'PENDIENTE' && (
                                    <span className="status-badge status-pending">{employee.pendingItems} Artículos</span>
                                )}
                            </div>
                            <span className="employee-return-arrow">›</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default EmployeeReturnsList;
