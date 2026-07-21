import './EmployeeReturnCard.css';

const EmployeeReturnCard = ({ employee, onViewHistory, onContact }) => {
    if (!employee) {
        return (
            <div className="employee-return-card-empty">
                <p className="empty-icon">👤</p>
                <p>Seleccione un empleado para procesar devoluciones</p>
            </div>
        );
    }

    const getInitials = (name) => {
        const parts = name.split(' ');
        if (parts.length >= 2) {
            return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    };

    return (
        <div className="employee-return-card">
            <div className="employee-card-header">
                <div className="employee-card-avatar-large">
                    {getInitials(employee.name)}
                    <span className="status-indicator"></span>
                </div>
                <div className="employee-card-main-info">
                    <h2 className="employee-card-name">{employee.name}</h2>
                    <span className={`employee-status-badge ${employee.status === 'ACTIVO' ? 'active' : 'inactive'}`}>
                        {employee.status}
                    </span>
                </div>
                <div className="employee-card-actions">
                    <button className="action-btn" onClick={onViewHistory}>
                        📊 Historial
                    </button>
                    <button className="action-btn" onClick={onContact}>
                        💬 Contacto
                    </button>
                </div>
            </div>

            <div className="employee-card-metadata">
                <div className="metadata-item">
                    <span className="metadata-icon">🆔</span>
                    <span className="metadata-label">ID:</span>
                    <span className="metadata-value">{employee.id}</span>
                </div>
                <div className="metadata-item">
                    <span className="metadata-icon">🏢</span>
                    <span className="metadata-label">{employee.department}</span>
                </div>
                <div className="metadata-item">
                    <span className="metadata-icon">📅</span>
                    <span className="metadata-label">Vence:</span>
                    <span className="metadata-value">{employee.expirationDate}</span>
                </div>
            </div>

            <div className="employee-card-note">
                <p className="note-title">Modificación manual de stock asignado por trabajador:</p>
                <p className="note-subtitle">Disponible desde la opción del lápiz en el módulo de personal</p>
            </div>
        </div>
    );
};

export default EmployeeReturnCard;
