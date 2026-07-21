import TopNav from './TopNav';
import './Layout.css';

const Layout = ({ children, title, subtitle }) => {
    return (
        <div className="layout">
            <TopNav />
            <main className="layout-content">
                {(title || subtitle) && (
                    <header className="page-head">
                        {title && <h1 className="page-head__title">{title}</h1>}
                        {subtitle && <p className="page-head__subtitle">{subtitle}</p>}
                    </header>
                )}
                {children}
            </main>
        </div>
    );
};

export default Layout;
