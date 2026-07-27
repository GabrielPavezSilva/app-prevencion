import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import EmployeeTable from '../components/staff/EmployeeTable';
import EppsModal from '../components/staff/EppsModal';
import { getEmployees, getEstadoSync, sincronizarPersonal } from '../services/staffService';
import { useAuth } from '../context/AuthContextModel';
import './Staff.css';

const formatearFechaHora = (valor) => {
    if (!valor) return null;
    const d = new Date(valor);
    return Number.isNaN(d.getTime())
        ? null
        : d.toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' });
};

/**
 * Personal — solo lectura. La nómina se sincroniza desde la base de RRHH
 * (diaria + botón manual); no hay alta ni edición desde la aplicación.
 */
const Staff = () => {
    const { user } = useAuth();
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [incluirInactivos, setIncluirInactivos] = useState(false);

    const [ultimaSync, setUltimaSync] = useState(null);
    const [sincronizando, setSincronizando] = useState(false);

    const [selectedEmployee, setSelectedEmployee] = useState(null);

    const puedeSincronizar =
        user?.role === 'admin' ||
        user?.role === 'administrador' ||
        (user?.modulos ?? []).includes('personal');

    const loadEmployees = useCallback(async () => {
        try {
            setLoading(true);
            const data = await getEmployees({ search: searchTerm, incluirInactivos });
            const mapped = (Array.isArray(data) ? data : []).map((emp) => ({
                id: emp.rut,
                rut: emp.rut,
                name: emp.nombre_completo,
                empresa: emp.empresa ?? '—',
                cargo: emp.cargo ?? '—',
                area: emp.nombre_area ?? '—',
                subarea: emp.nombre_subarea ?? '—',
                eppVigentes: emp.epp_vigentes ?? 0,
                activo: emp.activo !== false,
                url_picture: emp.url_picture ?? null,
            }));
            setEmployees(mapped);
        } catch (error) {
            console.error('Error loading employees:', error);
            toast.error('No se pudo cargar el personal.');
        } finally {
            setLoading(false);
        }
    }, [searchTerm, incluirInactivos]);

    const loadEstadoSync = useCallback(async () => {
        try {
            const estado = await getEstadoSync();
            setUltimaSync(estado?.ultima_sincronizacion ?? null);
        } catch {
            setUltimaSync(null);
        }
    }, []);

    useEffect(() => { loadEmployees(); }, [loadEmployees]);
    useEffect(() => { loadEstadoSync(); }, [loadEstadoSync]);

    const handleSincronizar = async () => {
        setSincronizando(true);
        const toastId = toast.loading('Sincronizando con RRHH…');
        try {
            const r = await sincronizarPersonal();
            toast.success(
                `Sincronización lista — ${r.creados} nuevos, ${r.actualizados} actualizados, ` +
                `${r.desactivados} desvinculados`,
                { id: toastId, duration: 6000 }
            );
            if (r.errores?.length) {
                toast.error(`${r.errores.length} registros con problemas — revisá el log`, { duration: 8000 });
            }
            await Promise.all([loadEmployees(), loadEstadoSync()]);
        } catch (error) {
            const detalle = error?.response?.data?.detail || error?.message || 'Error desconocido';
            toast.error(`No se pudo sincronizar: ${detalle}`, { id: toastId, duration: 8000 });
        } finally {
            setSincronizando(false);
        }
    };

    const fechaSync = formatearFechaHora(ultimaSync);

    return (
        <div className="staff-page">
            <div className="staff-filter-row">
                <p className="staff-page-title">Personal</p>

                <span className="staff-sync-info">
                    {fechaSync
                        ? `Última sincronización: ${fechaSync}`
                        : 'Sin sincronizaciones registradas'}
                </span>

                <label className="staff-toggle-inactivos">
                    <input
                        type="checkbox"
                        checked={incluirInactivos}
                        onChange={(e) => setIncluirInactivos(e.target.checked)}
                    />
                    Mostrar desvinculados
                </label>

                <div className="staff-search-wrapper">
                    <svg className="staff-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
                    </svg>
                    <input
                        type="text"
                        className="staff-search-input"
                        placeholder="Buscar por nombre o RUT..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                {puedeSincronizar && (
                    <button
                        type="button"
                        className="staff-btn-primary"
                        onClick={handleSincronizar}
                        disabled={sincronizando}
                        title="La nómina se sincroniza sola a diario; usá esto para un alta del día"
                    >
                        {sincronizando ? 'Sincronizando…' : 'Sincronizar ahora'}
                    </button>
                )}
            </div>

            <EmployeeTable
                employees={employees}
                onVerEpps={setSelectedEmployee}
                loading={loading}
                filterable
            />

            {selectedEmployee && (
                <EppsModal
                    employee={selectedEmployee}
                    onClose={() => setSelectedEmployee(null)}
                />
            )}
        </div>
    );
};

export default Staff;
