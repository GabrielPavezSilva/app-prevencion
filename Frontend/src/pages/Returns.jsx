import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import EmployeeReturnsList from '../components/returns/EmployeeReturnsList';
import EmployeeReturnCard from '../components/returns/EmployeeReturnCard';
import ReturnItemsTable from '../components/returns/ReturnItemsTable';
import { getEmployeesWithReturns, getEmployeeReturnItems, processReturn } from '../services/returnsService';
import './Returns.css';

const Returns = () => {
    const { employeeId } = useParams();
    const [employees, setEmployees] = useState([]);
    const [selectedEmployee, setSelectedEmployee] = useState(null);
    const [items, setItems] = useState([]);
    const [notes, setNotes] = useState('');
    const [activeFilter, setActiveFilter] = useState('PENDIENTE');
    const [loading, setLoading] = useState(true);
    const [itemsLoading, setItemsLoading] = useState(false);

    // Load employees with returns
    useEffect(() => {
        const loadEmployees = async () => {
            try {
                setLoading(true);
                const data = await getEmployeesWithReturns({ status: activeFilter });
                setEmployees(data);
            } catch (error) {
                console.error('Error loading employees:', error);
            } finally {
                setLoading(false);
            }
        };

        loadEmployees();
    }, [activeFilter]);

    // Pre-select employee from URL if provided
    useEffect(() => {
        if (employeeId && employees.length > 0) {
            const employee = employees.find(emp => emp.id === employeeId);
            if (employee) {
                setSelectedEmployee(employee);
            }
        }
    }, [employeeId, employees]);

    // Load items when employee is selected
    useEffect(() => {
        const loadItems = async () => {
            if (!selectedEmployee) return;

            try {
                setItemsLoading(true);
                const data = await getEmployeeReturnItems(selectedEmployee.id);
                setItems(data.items);
            } catch (error) {
                console.error('Error loading items:', error);
            } finally {
                setItemsLoading(false);
            }
        };

        loadItems();
    }, [selectedEmployee]);

    const handleSelectEmployee = (employee) => {
        setSelectedEmployee(employee);
        setNotes('');
    };

    const handleFilterChange = (filter) => {
        setActiveFilter(filter);
        setSelectedEmployee(null);
    };

    const handleQuantityChange = (itemId, quantity) => {
        setItems(prevItems =>
            prevItems.map(item =>
                item.id === itemId ? { ...item, quantityReturned: quantity } : item
            )
        );
    };

    const handleStatusChange = (itemId, status) => {
        setItems(prevItems =>
            prevItems.map(item =>
                item.id === itemId ? { ...item, status } : item
            )
        );
    };

    const handleProcessReturn = async () => {
        if (!selectedEmployee) return;

        const itemsWithChanges = items.filter(item =>
            item.quantityReturned > 0 || item.status !== ''
        );

        if (itemsWithChanges.length === 0) {
            alert('Por favor, actualice al menos un artículo antes de procesar.');
            return;
        }

        try {
            const result = await processReturn(
                selectedEmployee.id,
                itemsWithChanges,
                notes
            );

            console.log('Return processed:', result);
            alert('Devolución procesada exitosamente');

            // Reset state
            setSelectedEmployee(null);
            setItems([]);
            setNotes('');

            // Reload employees
            const data = await getEmployeesWithReturns({ status: activeFilter });
            setEmployees(data);
        } catch (error) {
            console.error('Error processing return:', error);
            alert('Error al procesar la devolución');
        }
    };

    const handleUpdateStatus = () => {
        console.log('Update status:', items);
        alert('Estado actualizado (en desarrollo)');
    };

    const handleViewHistory = () => {
        console.log('View history for:', selectedEmployee);
        alert('Ver historial (en desarrollo)');
    };

    const handleContact = () => {
        console.log('Contact employee:', selectedEmployee);
        alert('Contactar empleado (en desarrollo)');
    };

    const countReturningItems = () => {
        return items.filter(item => item.quantityReturned > 0).length;
    };

    return (
        <div className="returns-page">
            <div className="returns-header">
                <div>
                    <h1 className="returns-title">Gestión de Devoluciones</h1>
                    <p className="returns-subtitle">
                        Seleccione un empleado para procesar artículos.
                    </p>
                </div>
            </div>

            <div className="returns-content">
                {/* Left Panel - Employee List */}
                <div className="returns-left-panel">
                    <EmployeeReturnsList
                        employees={employees}
                        selectedEmployee={selectedEmployee}
                        onSelectEmployee={handleSelectEmployee}
                        activeFilter={activeFilter}
                        onFilterChange={handleFilterChange}
                        loading={loading}
                    />
                </div>

                {/* Right Panel - Employee Details & Items */}
                <div className="returns-right-panel">
                    <EmployeeReturnCard
                        employee={selectedEmployee}
                        onViewHistory={handleViewHistory}
                        onContact={handleContact}
                    />

                    {selectedEmployee && (
                        <>
                            <ReturnItemsTable
                                items={items}
                                onQuantityChange={handleQuantityChange}
                                onStatusChange={handleStatusChange}
                                loading={itemsLoading}
                            />

                            <div className="notes-section">
                                <h3 className="notes-title">Notas Adicionales</h3>
                                <textarea
                                    className="notes-textarea"
                                    placeholder="Ingrese notas sobre el proceso de devolución o artículos dañados..."
                                    value={notes}
                                    onChange={(e) => setNotes(e.target.value)}
                                    rows={4}
                                />
                            </div>

                            <div className="returns-footer">
                                <div className="footer-summary">
                                    <span className="summary-label">RESUMEN</span>
                                    <span className="summary-text">
                                        Devolviendo {countReturningItems()} de {items.length} Artículos
                                    </span>
                                </div>
                                <div className="footer-actions">
                                    <button className="btn btn-secondary" onClick={handleUpdateStatus}>
                                        Actualizar Estado
                                    </button>
                                    <button className="btn btn-primary" onClick={handleProcessReturn}>
                                        Procesar Devolución
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Returns;
