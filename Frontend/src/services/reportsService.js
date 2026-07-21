import { apiClient } from './api';

export const getTemplates = async () => {
    try {
        return await apiClient.get('/templates');
    } catch (error) {
        console.error("Error fetching templates:", error);
        return [];
    }
};

// Mock data for recent exports
const mockRecentExports = [
    {
        id: 1,
        name: 'Auditoria_Stock_03.pdf',
        generatedDate: '24 Oct, 2023',
        requestedBy: 'Admin User',
        status: 'Completado',
        format: 'pdf',
        downloadUrl: '/exports/audit_stock_03.pdf'
    },
    {
        id: 2,
        name: 'Reporte_Personal_Octubre.xlsx',
        generatedDate: '23 Oct, 2023',
        requestedBy: 'Manager',
        status: 'Completado',
        format: 'excel',
        downloadUrl: '/exports/staff_october.xlsx'
    },
    {
        id: 3,
        name: 'Devoluciones_Q3_2023.pdf',
        generatedDate: '20 Oct, 2023',
        requestedBy: 'Admin User',
        status: 'En Proceso',
        format: 'pdf',
        downloadUrl: null
    },
    {
        id: 4,
        name: 'Stock_Semanal_15-22_Oct.xlsx',
        generatedDate: '15 Oct, 2023',
        requestedBy: 'Supervisor',
        status: 'Completado',
        format: 'excel',
        downloadUrl: '/exports/weekly_stock.xlsx'
    },
    {
        id: 5,
        name: 'Auditoria_Completa_Sep.pdf',
        generatedDate: '01 Oct, 2023',
        requestedBy: 'Admin User',
        status: 'Error',
        format: 'pdf',
        downloadUrl: null
    }
];

/**
 * Upload bulk data file
 * @param {File} file - File object to upload
 * @param {string} templateId - Template ID
 * @returns {Promise<Object>} Upload result
 */
export const uploadBulkData = async (file, templateId) => {
    try {
        const formData = new FormData();
        formData.append('file', file);

        // Simular validación basica de frontend
        const validTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        if (!validTypes.includes(file.type)) {
            throw new Error('Tipo de archivo no válido. Use CSV, XLS o XLSX');
        }

        if (file.size > 50 * 1024 * 1024) {
            throw new Error('El archivo excede el tamaño máximo de 50MB');
        }

        const response = await apiClient.post(`/reportes/importar/${templateId}`, formData);

        // La respuesta del backend tendrá { success, message, recordsImported, errors }
        return response;
    } catch (error) {
        console.error("Error importando datos:", error);
        throw new Error(error.response?.data?.detail || error.message || "Ocurrió un error al importar el archivo.");
    }
};

/**
 * Download template file
 * @param {string} type - Template type ('stock', 'employee', 'returns')
 * @returns {Promise<void>} Triggers download
 */
export const downloadTemplate = async (type) => {
    // TODO: Replace with real API call
    // return apiClient.get(`/reports/template/${type}`, { responseType: 'blob' });

    await new Promise(resolve => setTimeout(resolve, 500));

    console.log(`Downloading ${type} template...`);
    alert(`Template de ${type} descargada (funcionalidad en desarrollo)`);

    return { success: true, type };
};

/**
 * Generate report
 * @param {Object} config - Report configuration
 * @param {Object} config.dateRange - { start, end }
 * @param {Array} config.selectedColumns - Array of selected column IDs
 * @param {string} config.format - 'pdf' or 'excel'
 * @returns {Promise<Object>} Generation result
 */
export const generateReport = async (config) => {
    try {
        const response = await apiClient.post('/reportes/generar', config, {
            responseType: 'blob' // Es vital para recibir el archivo binario
        });

        // Crear enlace temporal para descargar
        const url = window.URL.createObjectURL(new Blob([response]));
        const link = document.createElement('a');
        link.href = url;

        const timestamp = new Date().toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
        const fileName = `Reporte_Personalizado_${timestamp.replace(/ /g, '_')}.xlsx`;

        link.setAttribute('download', fileName);
        document.body.appendChild(link);
        link.click();

        // Limpieza
        window.URL.revokeObjectURL(url);
        link.parentNode.removeChild(link);

        return {
            success: true,
            message: 'Reporte Excel generado y descargado exitosamente'
        };
    } catch (error) {
        console.error("Error generando reporte:", error);
        throw new Error("Ocurrió un error al generar el Excel.");
    }
};

/**
 * Get recent exports
 * @param {number} page - Page number
 * @param {number} pageSize - Items per page
 * @returns {Promise<Object>} Paginated exports
 */
export const getRecentExports = async (page = 1, pageSize = 10) => {
    // TODO: Replace with real API call
    // return apiClient.get(`/reports/recent?page=${page}&pageSize=${pageSize}`);

    await new Promise(resolve => setTimeout(resolve, 400));

    const total = mockRecentExports.length;
    const totalPages = Math.ceil(total / pageSize);
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const data = mockRecentExports.slice(start, end);

    return {
        data,
        pagination: {
            page,
            pageSize,
            total,
            totalPages,
            hasNext: page < totalPages,
            hasPrev: page > 1
        }
    };
};

/**
 * Download export file
 * @param {number} exportId - Export ID
 * @returns {Promise<void>} Triggers download
 */
export const downloadExport = async (exportId) => {
    // TODO: Replace with real API call
    // return apiClient.get(`/reports/download/${exportId}`, { responseType: 'blob' });

    await new Promise(resolve => setTimeout(resolve, 800));

    const exportItem = mockRecentExports.find(exp => exp.id === exportId);
    if (!exportItem || !exportItem.downloadUrl) {
        throw new Error('Archivo no disponible para descarga');
    }

    console.log(`Downloading export: ${exportItem.name}`);
    alert(`Descargando ${exportItem.name} (funcionalidad en desarrollo)`);

    return { success: true, fileName: exportItem.name };
};

/**
 * Get report generation status
 * @param {number} reportId - Report ID
 * @returns {Promise<Object>} Status information
 */
export const getGenerationStatus = async (reportId) => {
    // TODO: Replace with real API call
    // return apiClient.get(`/reports/status/${reportId}`);

    await new Promise(resolve => setTimeout(resolve, 300));

    return {
        reportId,
        status: 'completed',
        progress: 100,
        downloadUrl: `/exports/report_${reportId}.pdf`
    };
};

/**
 * Get report configuration defaults
 * @returns {Object} Default configuration
 */
export const getDefaultConfig = () => {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    return {
        dateRange: {
            start: firstDayOfMonth.toISOString().split('T')[0],
            end: lastDayOfMonth.toISOString().split('T')[0]
        },
        includeData: {
            stockLevels: true,
            staffHistory: false,
            damages: false,
            auditLogs: false
        },
        format: 'pdf'
    };
};

