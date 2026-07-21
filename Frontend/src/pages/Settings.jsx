import './Settings.css';

// Fase 0 del clon prevención: la página de configuración de lectores RFID
// se eliminó junto con el hardware. Queda como contenedor de preferencias
// del sistema (se poblará en fases siguientes).
const Settings = () => {
    return (
        <div className="settings-page">
            <header className="settings-header">
                <h1 className="settings-title">Configuración</h1>
                <p className="settings-subtitle">Preferencias y ajustes del sistema.</p>
            </header>

            <section className="settings-section">
                <div className="settings-section-header">
                    <h2 className="settings-section-title">Preferencias</h2>
                    <p className="settings-section-desc">
                        Aún no hay ajustes configurables. Las opciones de gestión de EPP
                        (stock mínimo global, plantillas de importación, sincronización con Buk)
                        se agregarán aquí en próximas fases.
                    </p>
                </div>
            </section>
        </div>
    );
};

export default Settings;
