import './ReturnItemRow.css';

const ReturnItemRow = ({ item, onQuantityChange, onStatusChange }) => {
    const statusOptions = [
        { value: '', label: 'Seleccionar Estado...' },
        { value: 'Buen Estado', label: 'Buen Estado' },
        { value: 'Dañado', label: 'Dañado' },
        { value: 'Muy Dañado', label: 'Muy Dañado' },
        { value: 'Perdido', label: 'Perdido' }
    ];

    const handleQuantityChange = (e) => {
        const value = parseInt(e.target.value) || 0;
        if (value >= 0 && value <= item.quantityRequested) {
            onQuantityChange(item.id, value);
        }
    };

    const handleStatusChange = (e) => {
        onStatusChange(item.id, e.target.value);
    };

    return (
        <tr className="return-item-row">
            <td className="item-image-cell">
                <div className="item-image-placeholder">
                    📦
                </div>
            </td>

            <td className="item-details-cell">
                <div className="item-name">{item.name}</div>
                <div className="item-meta">
                    SKU: {item.sku} {item.size && `• ${item.size}`}
                </div>
            </td>

            <td className="item-quantity-cell">
                {item.quantityRequested}
            </td>

            <td className="item-returned-cell">
                <input
                    type="number"
                    className="quantity-input"
                    value={item.quantityReturned}
                    onChange={handleQuantityChange}
                    min="0"
                    max={item.quantityRequested}
                />
            </td>

            <td className="item-status-cell">
                <select
                    className="status-select"
                    value={item.status}
                    onChange={handleStatusChange}
                >
                    {statusOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>
                            {opt.label}
                        </option>
                    ))}
                </select>
            </td>
        </tr>
    );
};

export default ReturnItemRow;
