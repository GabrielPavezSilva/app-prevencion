import { useMemo } from 'react';
import DataTable from '../common/DataTable';

const CatalogoTable = ({ items, idKey, nombreKey, onEditar, onEliminar, loading }) => {
    const columns = useMemo(() => {
        const cols = [
            {
                accessorKey: idKey,
                header: '#',
                size: 80,
                meta: { align: 'center' },
                cell: ({ getValue }) => <span className="xls-mono">{getValue()}</span>,
            },
            {
                accessorKey: nombreKey,
                header: 'Nombre',
                size: 320,
                cell: ({ getValue }) => (
                    <span style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>{getValue()}</span>
                ),
            },
        ];
        if (onEditar || onEliminar) {
            cols.push({
                id: 'acciones',
                header: 'Acciones',
                size: 180,
                enableSorting: false,
                enableResizing: false,
                meta: { align: 'center' },
                cell: ({ row }) => (
                    <span style={{ display: 'inline-flex', gap: 8 }}>
                        {onEditar && (
                            <button className="catalogo-btn catalogo-btn--edit" onClick={() => onEditar(row.original)}>
                                Editar
                            </button>
                        )}
                        {onEliminar && (
                            <button className="catalogo-btn catalogo-btn--delete" onClick={() => onEliminar(row.original)}>
                                Eliminar
                            </button>
                        )}
                    </span>
                ),
            });
        }
        return cols;
    }, [idKey, nombreKey, onEditar, onEliminar]);

    const emptyState = (
        <div className="xls xls--state" style={{ fontStyle: 'italic' }}>
            No hay registros. Escanee una prenda nueva para registrarla.
        </div>
    );

    return (
        <DataTable
            columns={columns}
            data={items}
            loading={loading}
            emptyState={emptyState}
            initialSort={[{ id: idKey, desc: false }]}
        />
    );
};

export default CatalogoTable;
