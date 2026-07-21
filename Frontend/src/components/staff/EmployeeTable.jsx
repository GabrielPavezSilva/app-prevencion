import { useMemo } from 'react';
import DataTable from '../common/DataTable';
import './EmployeeTable.css';

const EmptyState = () => (
    <div className="staff-empty-state">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
        </svg>
        <p className="staff-empty-message">No se encontraron empleados</p>
        <p className="staff-empty-hint">Intenta ajustar el criterio de búsqueda</p>
    </div>
);

const EmployeeTable = ({ employees, onVerPrendas, loading, filterable = false }) => {
    const columns = useMemo(() => [
        {
            accessorKey: 'rut',
            header: 'RUT',
            size: 132,
            cell: ({ getValue }) => <span className="staff-cell-mono">{getValue()}</span>,
        },
        {
            accessorKey: 'name',
            header: 'Nombre',
            size: 210,
            meta: { filter: 'text' },
            cell: ({ getValue }) => <span className="staff-cell-name">{getValue()}</span>,
        },
        { accessorKey: 'empresa', header: 'Empresa', size: 160, filterFn: 'equalsString', meta: { filter: 'select' } },
        { accessorKey: 'cargo', header: 'Cargo', size: 150, filterFn: 'equalsString', meta: { filter: 'select' } },
        { accessorKey: 'area', header: 'Área', size: 130, filterFn: 'equalsString', meta: { filter: 'select' } },
        {
            accessorKey: 'talla',
            header: 'Talla',
            size: 92,
            filterFn: 'equalsString',
            meta: { align: 'center', filter: 'select' },
            cell: ({ getValue }) => {
                const v = getValue();
                return v && v !== '—'
                    ? <span className="staff-badge-neutral">{v}</span>
                    : <span className="staff-cell-muted">—</span>;
            },
        },
        {
            accessorKey: 'prendasAsignadas',
            header: 'Prendas activas',
            size: 138,
            filterFn: 'equalsString',
            meta: { align: 'center', filter: 'select' },
            cell: ({ row, getValue }) => (
                getValue() > 0 ? (
                    <button
                        className="staff-badge-info staff-badge-clickable"
                        onClick={() => onVerPrendas(row.original)}
                        title="Ver prendas asignadas"
                    >
                        {getValue()}
                    </button>
                ) : <span className="staff-cell-muted">0</span>
            ),
        },
    ], [onVerPrendas]);

    return (
        <DataTable
            columns={columns}
            data={employees}
            loading={loading}
            emptyState={<EmptyState />}
            initialSort={[{ id: 'prendasAsignadas', desc: true }]}
            pinFirstColumn
            filterable={filterable}
        />
    );
};

export default EmployeeTable;
