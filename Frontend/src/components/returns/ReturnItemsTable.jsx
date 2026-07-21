import ReturnItemRow from './ReturnItemRow';
import './ReturnItemsTable.css';

const ReturnItemsTable = ({ items, onQuantityChange, onStatusChange, loading }) => {
    if (loading) {
        return (
            <div className="items-table-loading">
                <div className="loading"></div>
                <p>Cargando artículos...</p>
            </div>
        );
    }

    if (!items || items.length === 0) {
        return (
            <div className="items-table-empty">
                <p className="empty-icon">📦</p>
                <p>No hay artículos pendientes de devolución</p>
            </div>
        );
    }

    return (
        <div className="return-items-section">
            <div className="section-header">
                <h3 className="section-title">Artículos Pendientes</h3>
                <p className="section-subtitle">Validar cantidad y estado de cada artículo.</p>
                <button className="mark-all-btn">
                    ✓ Marcar Todo como Bueno
                </button>
            </div>

            <div className="items-table-header-label">DETALLES DEL ARTÍCULO</div>

            <div className="items-table-container">
                <table className="items-table">
                    <thead>
                        <tr>
                            <th className="th-image"></th>
                            <th className="th-details">Artículo</th>
                            <th className="th-quantity">CANTIDAD<br />SOLICITADA</th>
                            <th className="th-returned">CANTIDAD<br />DEVUELTA</th>
                            <th className="th-status">ESTADO</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item) => (
                            <ReturnItemRow
                                key={item.id}
                                item={item}
                                onQuantityChange={onQuantityChange}
                                onStatusChange={onStatusChange}
                            />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ReturnItemsTable;
