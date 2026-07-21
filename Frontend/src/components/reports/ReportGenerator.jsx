import { useState } from 'react';
import './ReportGenerator.css';

const AVAILABLE_COLUMNS = [
    { id: 'sku', label: 'SKU', desc: 'Identificador único de la prenda' },
    { id: 'tipo_prenda', label: 'Tipo de Prenda', desc: 'Categoría de la prenda' },
    { id: 'talla', label: 'Talla', desc: 'Tamaño de la prenda' },
    { id: 'empresa', label: 'Empresa', desc: 'Organización a la que pertenece' },
    { id: 'estado', label: 'Estado', desc: 'Disponible vs En uso' },
    { id: 'fecha_entrega', label: 'Fecha Entrega', desc: 'Si está asignada, cuándo se entregó' },
    { id: 'rut_asignado', label: 'RUT Asignado', desc: 'Si está asignada, RUT del trabajador' },
];

const ReportGenerator = ({ onGenerate, onExportPDF, onExportExcel }) => {
    const [config, setConfig] = useState({
        dateRange: {
            start: '2023-10-01',
            end: '2023-10-31'
        },
        selectedColumns: ['sku', 'tipo_prenda', 'estado']
    });

    const [generating, setGenerating] = useState(false);

    const handleDateChange = (field, value) => {
        setConfig(prev => ({
            ...prev,
            dateRange: {
                ...prev.dateRange,
                [field]: value
            }
        }));
    };

    const handleColumnToggle = (colId) => {
        setConfig(prev => {
            const isSelected = prev.selectedColumns.includes(colId);
            const newColumns = isSelected
                ? prev.selectedColumns.filter(id => id !== colId)
                : [...prev.selectedColumns, colId];

            return {
                ...prev,
                selectedColumns: newColumns
            };
        });
    };

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            await onGenerate(config);
        } finally {
            setGenerating(false);
        }
    };

    const handleExportPDF = async () => {
        await onExportPDF(config);
    };

    const handleExportExcel = async () => {
        await onExportExcel(config);
    };

    return (
        <div className="report-generator-card">
            <div className="generator-header">
                <span className="generator-icon">📊</span>
                <h3 className="generator-title">Exportar Reportes</h3>
                <span className="active-badge">Sistema Activo</span>
            </div>

            <div className="date-range-section">
                <h4 className="section-label">RANGO DE FECHAS</h4>
                <div className="date-inputs">
                    <div className="date-input-group">
                        <label>Fecha de inicio</label>
                        <input
                            type="date"
                            className="date-input"
                            value={config.dateRange.start}
                            onChange={(e) => handleDateChange('start', e.target.value)}
                        />
                    </div>
                    <div className="date-input-group">
                        <label>Fecha de fin</label>
                        <input
                            type="date"
                            className="date-input"
                            value={config.dateRange.end}
                            onChange={(e) => handleDateChange('end', e.target.value)}
                        />
                    </div>
                </div>
            </div>

            <div className="data-inclusion-section">
                <h4 className="section-label">COLUMNAS A EXPORTAR</h4>
                <div className="checkbox-group" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '10px' }}>
                    {AVAILABLE_COLUMNS.map(col => (
                        <label className="checkbox-card" key={col.id} style={{ marginBottom: 0 }}>
                            <input
                                type="checkbox"
                                checked={config.selectedColumns.includes(col.id)}
                                onChange={() => handleColumnToggle(col.id)}
                            />
                            <div className="checkbox-content">
                                <span className="checkbox-title">{col.label}</span>
                                <span className="checkbox-desc" style={{ fontSize: '0.75rem' }}>{col.desc}</span>
                            </div>
                        </label>
                    ))}
                </div>
            </div>

            <div className="export-actions">
                <button className="export-btn export-pdf" onClick={handleExportPDF}>
                    📄 Descargar PDF
                </button>
                <button className="export-btn export-excel" onClick={handleExportExcel}>
                    📊 Exportar a Excel
                </button>
                <button
                    className="export-btn export-generate"
                    onClick={handleGenerate}
                    disabled={generating}
                >
                    {generating ? 'Generando...' : 'Generar Reporte →'}
                </button>
            </div>
        </div>
    );
};

export default ReportGenerator;
