import { useState } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    getFacetedRowModel,
    getFacetedUniqueValues,
    flexRender,
} from '@tanstack/react-table';
import './DataTable.css';

/** Control de filtro por columna (texto o select con valores únicos). */
function ColumnFilter({ column }) {
    const type = column.columnDef.meta?.filter;
    const value = column.getFilterValue() ?? '';

    if (type === 'select') {
        const options = Array.from(column.getFacetedUniqueValues().keys())
            .filter((v) => v != null && v !== '' && v !== '—')
            .sort((a, b) => String(a).localeCompare(String(b), 'es', { numeric: true }));
        return (
            <select
                className="xls__filter"
                value={value}
                onChange={(e) => column.setFilterValue(e.target.value || undefined)}
            >
                <option value="">Todos</option>
                {options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                ))}
            </select>
        );
    }
    if (type === 'text') {
        return (
            <input
                className="xls__filter"
                type="text"
                placeholder="Filtrar…"
                value={value}
                onChange={(e) => column.setFilterValue(e.target.value || undefined)}
            />
        );
    }
    return null;
}

/**
 * Tabla estilo hoja de cálculo (Excel) sobre TanStack Table.
 * - Ancho 100% del contenedor; con scroll horizontal si las columnas no caben.
 * - Cuadrícula completa, encabezado fijo, orden y columnas redimensionables.
 * - `filterable`: muestra una fila de filtros por columna (según `meta.filter`).
 * - `meta.filter`: 'text' | 'select'. `meta.align`: 'center' | 'right'.
 * - `pinFirstColumn`: congela la primera columna (freeze panes).
 */
export default function DataTable({
    columns,
    data,
    loading = false,
    emptyState = null,
    initialSort = [],
    pinFirstColumn = false,
    filterable = false,
    maxHeight = 'min(64vh, 640px)',
}) {
    const [sorting, setSorting] = useState(initialSort);
    const [columnFilters, setColumnFilters] = useState([]);

    const table = useReactTable({
        data: data ?? [],
        columns,
        state: { sorting, columnFilters },
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getFacetedRowModel: getFacetedRowModel(),
        getFacetedUniqueValues: getFacetedUniqueValues(),
        columnResizeMode: 'onChange',
        enableColumnResizing: true,
    });

    if (loading) {
        return (
            <div className="xls xls--state">
                {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="xls__skeleton-row skeleton" />
                ))}
            </div>
        );
    }

    if (!data || data.length === 0) {
        return emptyState ?? <div className="xls xls--state">Sin datos.</div>;
    }

    const rows = table.getRowModel().rows;

    return (
        <div className="xls" style={{ maxHeight }}>
            <table className="xls__table" style={{ width: '100%', minWidth: table.getCenterTotalSize() }}>
                <thead>
                    {table.getHeaderGroups().map((hg) => (
                        <tr key={hg.id}>
                            {hg.headers.map((header, i) => {
                                const col = header.column;
                                const sortable = col.getCanSort();
                                const sorted = col.getIsSorted();
                                const pin = pinFirstColumn && i === 0;
                                return (
                                    <th
                                        key={header.id}
                                        className={`xls__th${pin ? ' xls__pin' : ''}`}
                                        style={{ width: header.getSize() }}
                                        aria-sort={sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : 'none'}
                                    >
                                        <button
                                            type="button"
                                            className="xls__th-btn"
                                            onClick={col.getToggleSortingHandler()}
                                            disabled={!sortable}
                                        >
                                            <span className="xls__th-label">
                                                {flexRender(col.columnDef.header, header.getContext())}
                                            </span>
                                            {sortable && (
                                                <span className="xls__sort" data-dir={sorted || 'none'} aria-hidden="true">
                                                    {sorted === 'asc' ? (
                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 15 12 9 18 15" /></svg>
                                                    ) : sorted === 'desc' ? (
                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
                                                    ) : (
                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="7 10 12 5 17 10" /><polyline points="7 14 12 19 17 14" /></svg>
                                                    )}
                                                </span>
                                            )}
                                        </button>
                                        {col.getCanResize() && (
                                            <span
                                                className="xls__resizer"
                                                data-resizing={col.getIsResizing() || undefined}
                                                onMouseDown={header.getResizeHandler()}
                                                onTouchStart={header.getResizeHandler()}
                                            />
                                        )}
                                    </th>
                                );
                            })}
                        </tr>
                    ))}
                    {filterable && table.getHeaderGroups().map((hg) => (
                        <tr key={`f-${hg.id}`} className="xls__filter-row">
                            {hg.headers.map((header, i) => {
                                const pin = pinFirstColumn && i === 0;
                                return (
                                    <th key={header.id} className={`xls__filter-th${pin ? ' xls__pin' : ''}`} style={{ width: header.getSize() }}>
                                        {header.column.getCanFilter() && header.column.columnDef.meta?.filter
                                            ? <ColumnFilter column={header.column} />
                                            : null}
                                    </th>
                                );
                            })}
                        </tr>
                    ))}
                </thead>
                <tbody>
                    {rows.length === 0 ? (
                        <tr>
                            <td className="xls__noresults" colSpan={table.getAllLeafColumns().length}>
                                Sin resultados para los filtros aplicados.
                            </td>
                        </tr>
                    ) : rows.map((row) => (
                        <tr key={row.id} className="xls__row">
                            {row.getVisibleCells().map((cell, i) => {
                                const align = cell.column.columnDef.meta?.align;
                                const pin = pinFirstColumn && i === 0;
                                return (
                                    <td
                                        key={cell.id}
                                        className={`xls__td${pin ? ' xls__pin' : ''}${align ? ` xls__td--${align}` : ''}`}
                                        style={{ width: cell.column.getSize() }}
                                    >
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
