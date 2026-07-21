import { useState, useEffect } from 'react';
import EmployeeTable from '../components/staff/EmployeeTable';
import PrendasModal from '../components/staff/PrendasModal';
import { getEmployees, getAsignaciones } from '../services/staffService';
import { getTallas } from '../services/catalogosService';
import './Staff.css';

const Staff = () => {
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    // Prendas Modal State
    const [showPrendasModal, setShowPrendasModal] = useState(false);
    const [selectedEmployeeForPrendas, setSelectedEmployeeForPrendas] = useState(null);

    const handleVerPrendas = (employee) => {
        setSelectedEmployeeForPrendas(employee);
        setShowPrendasModal(true);
    };

    const handlePrendasModalSuccess = () => {
        setShowPrendasModal(false);
        setSelectedEmployeeForPrendas(null);
        loadEmployees();
    };

    // Load employees + asignaciones para cruce (N° EPPs asignados por RUT)
    const loadEmployees = async () => {
        try {
            setLoading(true);
            const [data, asignacionesData, tallasData] = await Promise.all([
                getEmployees(1, 100, { search: searchTerm }),
                getAsignaciones(),
                getTallas(),
            ]);
            // Mapa talla_id → nombreTalla
            const tallaMap = {};
            (Array.isArray(tallasData) ? tallasData : []).forEach((t) => {
                tallaMap[t.TallaID] = t.nombreTalla;
            });
            const asignaciones = Array.isArray(asignacionesData) ? asignacionesData : [];
            const normalizeRut = (r) => (r || '').toString().replace(/[.\s-]/g, '').toUpperCase();
            const countByRut = {};
            asignaciones.forEach((a) => {
                if (a.fecha_devolucion == null) {
                    const key = normalizeRut(a.rut);
                    countByRut[key] = (countByRut[key] || 0) + 1;
                }
            });
            const mapped = (Array.isArray(data) ? data : []).map((emp) => {
                const rutNorm = normalizeRut(emp.rut);
                return {
                    id: emp.rut,
                    rut: emp.rut,
                    name: emp.nombre_completo,
                    empresa: emp.empresa ?? '—',
                    cargo: emp.cargo ?? '—',
                    area: emp.nombre_subarea ?? '—',
                    talla: tallaMap[emp.talla_id] ?? '—',
                    prendasAsignadas: countByRut[rutNorm] ?? 0,
                    url_picture: emp.url_picture ?? null,
                };
            });
            mapped.sort((a, b) => b.prendasAsignadas - a.prendasAsignadas);
            setEmployees(mapped);
        } catch (error) {
            console.error('Error loading employees:', error);
        } finally {
            setLoading(false);
        }
    };

    // Load employees when search changes
    useEffect(() => {
        loadEmployees();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchTerm]);

    const handleSearch = (e) => {
        setSearchTerm(e.target.value);
    };

    const handleEdit = (employee) => {
        console.log('Edit employee:', employee);
        // TODO: Open edit modal
    };

    return (
        <div className="staff-page">
            {/* Título + búsqueda en una sola fila para subir la tabla */}
            <div className="staff-filter-row">
                <p className="staff-page-title">Personal</p>
                <div className="staff-search-wrapper">
                    <svg className="staff-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
                    </svg>
                    <input
                        type="text"
                        className="staff-search-input"
                        placeholder="Ingrese RUT para buscar..."
                        value={searchTerm}
                        onChange={handleSearch}
                    />
                </div>
            </div>

            {/* Employee Table — empresa/cargo se filtran por columna (TanStack) */}
            <EmployeeTable
                employees={employees}
                onEdit={handleEdit}
                onVerPrendas={handleVerPrendas}
                loading={loading}
                filterable
            />

            {/* Prendas Modal */}
            {showPrendasModal && selectedEmployeeForPrendas && (
                <PrendasModal
                    employee={selectedEmployeeForPrendas}
                    onClose={() => {
                        setShowPrendasModal(false);
                        setSelectedEmployeeForPrendas(null);
                    }}
                    onSuccess={handlePrendasModalSuccess}
                />
            )}
        </div>
    );
};

export default Staff;
