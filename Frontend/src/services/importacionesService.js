import { apiClient } from './api';

// Lista de templates de importación disponibles
export const getTemplates = () => apiClient.get('/templates/');

// Descarga la plantilla Excel vacía de un template y dispara la descarga
export const descargarPlantilla = async (templateId) => {
    const blob = await apiClient.get(`/templates/descargar/${templateId}`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `plantilla_${templateId}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
};

// Sube un archivo Excel/CSV para un template -> resumen {filas_ok, filas_error, errores}
export const importar = (templateId, file) => {
    const fd = new FormData();
    fd.append('file', file);
    return apiClient.post(`/importaciones/${templateId}`, fd);
};

// Historial de importaciones ejecutadas
export const getImportaciones = () => apiClient.get('/importaciones/');
