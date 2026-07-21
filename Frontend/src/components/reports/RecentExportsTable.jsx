import './RecentExportsTable.css';

const RecentExportsTable = ({ exports, onDownload, loading }) => {
    const getStatusColor = (status) => {
        switch (status.toLowerCase()) {
            case 'completado':
                return 'status-completed';
            case 'en proceso':
                return 'status-processing';
            case 'error':
                return 'status-error';
            default:
                return '';
        }
    };

    if (loading) {
        return (
            <div className="exports-table-loading">
                <div className="loading"></div>
                <p>Cargando exportaciones...</p>
            </div>
        );
    }

    if (!exports || exports.length === 0) {
        return (
            <div className="exports-table-empty">
                <p className="empty-icon">📭</p>
                <p>No hay exportaciones recientes</p>
            </div>
        );
    }

    return (
        <div className="recent-exports-section">
            <h3 className="exports-title">Exportaciones Recientes</h3>

            <div className="exports-table-container">
                <table className="exports-table">
                    <thead>
                        <tr>
                            <th>NOMBRE DEL REPORTE</th>
                            <th>FECHA GENERADA</th>
                            <th>SOLICITADO POR</th>
                            <th>ESTADO</th>
                            <th>ACCIÓN</th>
                        </tr>
                    </thead>
                    <tbody>
                        {exports.map((exportItem) => (
                            <tr key={exportItem.id}>
                                <td className="report-name-cell">
                                    <span className="report-icon">
                                        {exportItem.format === 'pdf' ? '📄' : '📊'}
                                    </span>
                                    {exportItem.name}
                                </td>
                                <td>{exportItem.generatedDate}</td>
                                <td>{exportItem.requestedBy}</td>
                                <td>
                                    <span className={`status-badge ${getStatusColor(exportItem.status)}`}>
                                        {exportItem.status}
                                    </span>
                                </td>
                                <td className="action-cell">
                                    {exportItem.status === 'Completado' ? (
                                        <button
                                            className="download-btn"
                                            onClick={() => onDownload(exportItem.id)}
                                            title="Descargar"
                                        >
                                            ⬇️
                                        </button>
                                    ) : (
                                        <span className="no-action">-</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default RecentExportsTable;
