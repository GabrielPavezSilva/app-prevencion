import { useState, useEffect } from 'react';
import './FileUploadArea.css';
import { getTemplates } from '../../services/reportsService';

const FileUploadArea = ({ onFileUpload }) => {
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [dragActive, setDragActive] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadSuccess, setUploadSuccess] = useState(null);

    useEffect(() => {
        const fetchTemplates = async () => {
            try {
                const data = await getTemplates();
                setTemplates(data);
                if (data.length > 0) {
                    setSelectedTemplate(data[0].id);
                }
            } catch (error) {
                console.error("Error al obtener templates: ", error);
            }
        };
        fetchTemplates();
    }, []);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            await handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = async (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            await handleFile(e.target.files[0]);
        }
    };

    const handleFile = async (file) => {
        if (!selectedTemplate) {
            alert("Debe seleccionar un Template de Importación primero.");
            return;
        }

        setUploading(true);
        setUploadSuccess(null);

        try {
            const result = await onFileUpload(file, selectedTemplate);
            setUploadSuccess(result);
            setTimeout(() => setUploadSuccess(null), 5000);
        } catch (error) {
            console.error('Upload failed:', error);
            alert(error.message || 'Error al subir el archivo');
        } finally {
            setUploading(false);
        }
    };

    const handleClick = () => {
        document.getElementById('file-upload-input').click();
    };

    return (
        <div className="file-upload-card">
            <div className="file-upload-header">
                <span className="upload-icon">🔺</span>
                <h3 className="upload-title">Carga Masiva de Datos</h3>
            </div>

            <div className="template-selector" style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', color: '#666' }}>Tipo de Importación:</label>
                <select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    style={{
                        width: '100%',
                        padding: '10px',
                        borderRadius: '6px',
                        border: '1px solid #ddd',
                        backgroundColor: '#f9f9f9'
                    }}
                >
                    {templates.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                </select>
                <p style={{ marginTop: '5px', fontSize: '0.8rem', color: '#888' }}>
                    {templates.find(t => t.id === selectedTemplate)?.description}
                </p>
            </div>

            <div
                className={`file-upload-zone ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                <input
                    id="file-upload-input"
                    type="file"
                    accept=".csv,.xls,.xlsx"
                    onChange={handleChange}
                    style={{ display: 'none' }}
                />

                {uploading ? (
                    <div className="upload-loading">
                        <div className="loading"></div>
                        <p>Subiendo archivo...</p>
                    </div>
                ) : uploadSuccess ? (
                    <div className="upload-success">
                        <span className="success-icon">✓</span>
                        <p>{uploadSuccess.message}</p>
                        <p className="success-details">{uploadSuccess.recordsImported} registros importados</p>
                    </div>
                ) : (
                    <>
                        <span className="file-icon">📄</span>
                        <p className="upload-text">Clic para subir o arrastre y suelte</p>
                        <p className="upload-hint">CSV, XLS, XLSX (Máx 50MB)</p>
                    </>
                )}
            </div>

            <button className="template-link" onClick={() => {
                if (selectedTemplate) {
                    window.location.href = `http://localhost:8000/api/templates/descargar/${selectedTemplate}`;
                }
            }}>
                Descargar Plantilla
            </button>

            <button className="upload-btn" onClick={handleClick} disabled={uploading}>
                Subir Archivo
            </button>
        </div>
    );
};

export default FileUploadArea;
