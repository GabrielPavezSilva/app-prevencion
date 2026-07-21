import './Header.css';

const CalendarIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
);

const Header = ({ title, subtitle }) => {
    const today = new Date().toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });

    return (
        <header className="header">
            <div className="header-content">
                <div className="header-title-section">
                    <h1 className="header-title">{title}</h1>
                    {subtitle && <p className="header-subtitle">{subtitle}</p>}
                </div>

                <div className="header-actions">
                    <div className="date-selector">
                        <CalendarIcon />
                        <span className="date-text">{today}</span>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
