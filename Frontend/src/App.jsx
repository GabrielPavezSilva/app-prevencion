import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContextModel';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import Entregas from './pages/Entregas';
import Importaciones from './pages/Importaciones';
import Staff from './pages/Staff';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Login from './pages/Login';
import SuperAdmin from './pages/SuperAdmin';
import { getHomeForUser } from './utils/routes';
import './styles/index.css';

/**
 * Ruta protegida por módulo.
 *
 * - Si no está autenticado → redirige a /login.
 * - admin siempre pasa (acceso total).
 * - Si requiredModule está definido → el usuario debe tener ese módulo en su lista.
 * - Si no tiene el módulo → redirige a su home según rol.
 */
const ProtectedRoute = ({ children, requiredModule }) => {
  const { loading, isAuthenticated, user } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--color-bg)'
      }}>
        <div className="loading"></div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  // Admin siempre tiene acceso completo
  if (user?.role === 'admin') return children;

  // Verificar que el usuario tenga el módulo requerido
  if (requiredModule && !user?.modulos?.includes(requiredModule)) {
    return <Navigate to={getHomeForUser(user)} replace />;
  }

  return children;
};

// App routes component
const AppRoutes = () => {
  const { isAuthenticated, user } = useAuth();

  return (
    <Routes>
      {/* Ruta pública — Login */}
      <Route
        path="/login"
        element={
          isAuthenticated() ? (
            <Navigate to={getHomeForUser(user)} replace />
          ) : (
            <Login />
          )
        }
      />

      {/* ── Rutas Admin ── */}
      <Route
        path="/"
        element={
          <ProtectedRoute requiredModule="dashboard">
            <Layout title="Panel de Control General" subtitle="Entregas de EPP, cobertura de personal y alertas de stock.">
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventario"
        element={
          <ProtectedRoute requiredModule="inventario">
            <Layout>
              <Inventory />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/entregas"
        element={
          <ProtectedRoute requiredModule="entregas">
            <Layout title="Entregas de EPP" subtitle="Registro de entregas, reposiciones y sustituciones.">
              <Entregas />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/importaciones"
        element={
          <ProtectedRoute requiredModule="inventario">
            <Layout title="Importaciones" subtitle="Carga masiva de productos, stock y entregas históricas.">
              <Importaciones />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/personal"
        element={
          <ProtectedRoute requiredModule="personal">
            <Layout>
              <Staff />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reportes"
        element={
          <ProtectedRoute requiredModule="reportes">
            <Layout title="Reportes" subtitle="Trazabilidad de entregas, EPP vigentes por trabajador y estado del stock.">
              <Reports />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/configuracion"
        element={
          <ProtectedRoute requiredModule="configuracion">
            <Layout title="Configuración" subtitle="Preferencias y ajustes del sistema.">
              <Settings />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* ── Superadmin ── */}
      <Route
        path="/superadmin"
        element={
          <ProtectedRoute requiredModule="superadmin">
            <Layout title="Administración del sistema" subtitle="Gestión de usuarios, roles y permisos.">
              <SuperAdmin />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Sin acceso — usuarios autenticados sin módulos asignados */}
      <Route
        path="/sin-acceso"
        element={
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100vh', background: 'var(--color-bg)',
            gap: 16, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-family)',
          }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>Sin acceso</h2>
            <p style={{ fontSize: 14, margin: 0 }}>Tu cuenta no tiene módulos asignados. Contacta al administrador.</p>
          </div>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
