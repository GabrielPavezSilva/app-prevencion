import { useState, useEffect } from 'react';
import FileUploadArea from '../components/reports/FileUploadArea';
import ReportGenerator from '../components/reports/ReportGenerator';
import RecentExportsTable from '../components/reports/RecentExportsTable';
import {
    uploadBulkData,
    downloadTemplate,
    generateReport,
    getRecentExports,
    downloadExport
} from '../services/reportsService';
import './Reports.css';

const Reports = () => {
    const [exports, setExports] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadExports();
    }, []);

    const loadExports = async () => {
        try {
            setLoading(true);
            const response = await getRecentExports(1, 10);
            setExports(response.data);
        } catch (error) {
            console.error('Error loading exports:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = async (file, templateId) => {
        const result = await uploadBulkData(file, templateId);
        return result;
    };

    const handleTemplateDownload = async () => {
        await downloadTemplate('stock');
    };

    const handleGenerate = async (config) => {
        const fullConfig = { ...config, format: 'pdf' };
        const result = await generateReport(fullConfig);
        alert(result.message);
        await loadExports();
    };

    const handleExportPDF = async (config) => {
        const fullConfig = { ...config, format: 'pdf' };
        await generateReport(fullConfig);
        alert('Reporte PDF generado exitosamente');
        await loadExports();
    };

    const handleExportExcel = async (config) => {
        const fullConfig = { ...config, format: 'excel' };
        await generateReport(fullConfig);
        alert('Reporte Excel generado exitosamente');
        await loadExports();
    };

    const handleDownload = async (exportId) => {
        try {
            await downloadExport(exportId);
        } catch (error) {
            console.error('Download error:', error);
            alert(error.message || 'Error al descargar el archivo');
        }
    };

    return (
        <div className="reports-page">
            <div className="reports-header">
                <div>
                    <h1 className="reports-title">Reportes y Gestión de Datos</h1>
                    <p className="reports-subtitle">
                        Importe datos de inventario masivos o genere reportes detallados de equipos para cumplimiento y auditoría.
                    </p>
                </div>
            </div>

            <div className="reports-grid">
                <FileUploadArea
                    onFileUpload={handleFileUpload}
                    onTemplateDownload={handleTemplateDownload}
                />

                <ReportGenerator
                    onGenerate={handleGenerate}
                    onExportPDF={handleExportPDF}
                    onExportExcel={handleExportExcel}
                />
            </div>

            <RecentExportsTable
                exports={exports}
                onDownload={handleDownload}
                loading={loading}
            />
        </div>
    );
};

export default Reports;
