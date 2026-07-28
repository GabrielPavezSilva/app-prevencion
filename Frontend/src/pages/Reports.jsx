import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import DataTable from '../components/common/DataTable';
import { getProductos, getCategorias } from '../services/eppService';
import {
    getTrazabilidad, getEppVigentes, getStock,
    getAreas, getSubareas, getEmpresas,
    descargarTrazabilidad, descargarEppVigentes, descargarStock,
} from '../services/reportsService';
import './Page.css';
import './Inventory.css';
import './Reports.css';

const MOTIVOS = [
    { v: 'NUEVA', label: 'Nueva' },
    { v: 'PERDIDA', label: 'Reposición por pérdida' },
    { v: 'DANO', label: 'Sustitución por daño' },
];

const etiquetaMotivo = (v) => MOTIVOS.find((m) => m.v === v)?.label || v || '—';
const fecha = (v) => (v ? new Date(v).toLocaleDateString('es-CL') : '—');
const fechaHora = (v) => (v ? new Date(v).toLocaleString('es-CL', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
}) : '—');

/** Quita las claves vacías para no mandar filtros nulos al backend. */
const limpiar = (f) => Object.fromEntries(
    Object.entries(f).filter(([, v]) => v !== '' && v !== null && v !== undefined)
);

// ── Barra de descarga ─────────────────────────────────────────────────────────
function BotonExcel({ onDescargar, filtros, disabled }) {
    const [bajando, setBajando] = useState(false);
    const click = async () => {
        setBajando(true);
        try {
            await onDescargar(limpiar(filtros));
            toast.success('Excel generado');
        } catch (err) {
            toast.error(err.message || 'No se pudo generar el Excel');
        } finally {
            setBajando(false);
        }
    };
    return (
        <button className="catalogo-btn catalogo-btn--primary" onClick={click}
            disabled={bajando || disabled}>
            {bajando ? 'Generando…' : 'Exportar Excel'}
        </button>
    );
}

// ── Hook de catálogos compartidos por los tabs ────────────────────────────────
function useCatalogos() {
    const [cat, setCat] = useState({ empresas: [], areas: [], productos: [], categorias: [] });
    useEffect(() => {
        Promise.all([
            getEmpresas().catch(() => []),
            getAreas().catch(() => []),
            getProductos({ activo: true }).catch(() => []),
            getCategorias().catch(() => []),
        ]).then(([empresas, areas, productos, categorias]) => {
            setCat({
                empresas: empresas || [], areas: areas || [],
                productos: productos || [], categorias: categorias || [],
            });
        });
    }, []);
    return cat;
}

/** Selectores de empresa → área → subárea, encadenados. */
function FiltrosOrganizacion({ cat, filtros, setFiltro }) {
    // Caché por área: evita refetch al volver a un área ya consultada y deja la
    // lista visible como valor derivado, sin setState síncrono en el efecto.
    const [cache, setCache] = useState({});

    useEffect(() => {
        const id = filtros.area_id;
        if (!id || cache[id]) return;
        getSubareas(id)
            .then((s) => setCache((m) => ({ ...m, [id]: s || [] })))
            .catch(() => setCache((m) => ({ ...m, [id]: [] })));
    }, [filtros.area_id, cache]);

    const subareas = filtros.area_id ? (cache[filtros.area_id] || []) : [];

    const areasVisibles = filtros.empresa_id
        ? cat.areas.filter((a) => a.empresa_id === Number(filtros.empresa_id))
        : cat.areas;

    return (
        <>
            <select className="modal-input" value={filtros.empresa_id ?? ''}
                onChange={(e) => setFiltro({ empresa_id: e.target.value, area_id: '', subarea_id: '' })}>
                <option value="">Todas las empresas</option>
                {cat.empresas.map((e) => (
                    <option key={e.empresa_id} value={e.empresa_id}>{e.nombre_empresa}</option>
                ))}
            </select>
            <select className="modal-input" value={filtros.area_id ?? ''}
                onChange={(e) => setFiltro({ area_id: e.target.value, subarea_id: '' })}>
                <option value="">Todas las áreas</option>
                {areasVisibles.map((a) => (
                    <option key={a.area_id} value={a.area_id}>
                        {!filtros.empresa_id && a.nombre_empresa
                            ? `${a.nombre_area} · ${a.nombre_empresa}`
                            : a.nombre_area}
                    </option>
                ))}
            </select>
            <select className="modal-input" value={filtros.subarea_id ?? ''}
                onChange={(e) => setFiltro({ subarea_id: e.target.value })}
                disabled={subareas.length === 0}>
                <option value="">Todas las subáreas</option>
                {subareas.map((s) => (
                    <option key={s.subarea_id} value={s.subarea_id}>{s.nombre_subarea}</option>
                ))}
            </select>
        </>
    );
}

// ── Tab 1: Trazabilidad de entregas ───────────────────────────────────────────
const TabTrazabilidad = ({ cat }) => {
    const [filtros, setFiltros] = useState({
        desde: '', hasta: '', motivo: '', empresa_id: '', area_id: '',
        subarea_id: '', producto_id: '', categoria_id: '', rut: '',
    });
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    const setFiltro = (parcial) => setFiltros((f) => ({ ...f, ...parcial }));

    const cargar = useCallback(async () => {
        setLoading(true);
        try { setData(await getTrazabilidad(limpiar(filtros))); }
        catch (err) { toast.error(err.message || 'Error al cargar el reporte'); setData([]); }
        finally { setLoading(false); }
    }, [filtros]);
    useEffect(() => { cargar(); }, [cargar]);

    const columns = [
        { accessorKey: 'fecha_entrega', header: 'Fecha',
          cell: ({ row }) => fechaHora(row.original.fecha_entrega) },
        { accessorKey: 'rut', header: 'RUT' },
        { accessorKey: 'nombre_completo', header: 'Trabajador' },
        { accessorKey: 'area', header: 'Área', cell: ({ row }) => row.original.area || '—' },
        { accessorKey: 'producto', header: 'Producto',
          cell: ({ row }) => [row.original.producto, row.original.talla].filter(Boolean).join(' · ') },
        { accessorKey: 'cantidad', header: 'Cant.', meta: { align: 'right' } },
        { accessorKey: 'motivo', header: 'Motivo', meta: { align: 'center', filter: 'select' },
          cell: ({ row }) => etiquetaMotivo(row.original.motivo) },
        { accessorKey: 'registrado_por', header: 'Registró',
          cell: ({ row }) => row.original.registrado_por || '—' },
    ];

    return (
        <div>
            <div className="rep-filtros">
                <input className="modal-input" type="date" value={filtros.desde}
                    onChange={(e) => setFiltro({ desde: e.target.value })} title="Desde" />
                <input className="modal-input" type="date" value={filtros.hasta}
                    onChange={(e) => setFiltro({ hasta: e.target.value })} title="Hasta" />
                <select className="modal-input" value={filtros.motivo}
                    onChange={(e) => setFiltro({ motivo: e.target.value })}>
                    <option value="">Todos los motivos</option>
                    {MOTIVOS.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
                </select>
                <FiltrosOrganizacion cat={cat} filtros={filtros} setFiltro={setFiltro} />
                <select className="modal-input" value={filtros.producto_id}
                    onChange={(e) => setFiltro({ producto_id: e.target.value })}>
                    <option value="">Todos los productos</option>
                    {cat.productos.map((p) => (
                        <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>
                    ))}
                </select>
                <input className="modal-input" placeholder="RUT del trabajador" value={filtros.rut}
                    onChange={(e) => setFiltro({ rut: e.target.value })} />
            </div>

            <div className="rep-acciones">
                <span className="rep-conteo">
                    {loading ? 'Cargando…' : `${data.length} ${data.length === 1 ? 'entrega' : 'entregas'}`}
                </span>
                <BotonExcel onDescargar={descargarTrazabilidad} filtros={filtros} />
            </div>

            <DataTable columns={columns} data={data} loading={loading} filterable
                initialSort={[{ id: 'fecha_entrega', desc: true }]}
                emptyState={<div className="xls xls--state">Sin entregas para estos filtros.</div>} />
        </div>
    );
};

// ── Tab 2: EPP vigentes ───────────────────────────────────────────────────────
const TabVigentes = ({ cat }) => {
    const [filtros, setFiltros] = useState({
        empresa_id: '', area_id: '', subarea_id: '',
        producto_id: '', categoria_id: '', rut: '', incluir_inactivos: false,
    });
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    const setFiltro = (parcial) => setFiltros((f) => ({ ...f, ...parcial }));

    const cargar = useCallback(async () => {
        setLoading(true);
        try { setData(await getEppVigentes(limpiar(filtros))); }
        catch (err) { toast.error(err.message || 'Error al cargar el reporte'); setData([]); }
        finally { setLoading(false); }
    }, [filtros]);
    useEffect(() => { cargar(); }, [cargar]);

    const columns = [
        { accessorKey: 'rut', header: 'RUT' },
        { accessorKey: 'nombre_completo', header: 'Trabajador' },
        { accessorKey: 'area', header: 'Área', cell: ({ row }) => row.original.area || '—' },
        { accessorKey: 'cargo', header: 'Cargo', cell: ({ row }) => row.original.cargo || '—' },
        { accessorKey: 'producto', header: 'EPP vigente',
          cell: ({ row }) => (row.original.sin_epp
              ? <span className="rep-sin-epp">Sin EPP asignado</span>
              : [row.original.producto, row.original.talla].filter(Boolean).join(' · ')) },
        { accessorKey: 'cantidad', header: 'Cant.', meta: { align: 'right' },
          cell: ({ row }) => row.original.cantidad ?? '—' },
        { accessorKey: 'fecha_entrega', header: 'Entregado',
          cell: ({ row }) => fecha(row.original.fecha_entrega) },
        { accessorKey: 'dias_desde_entrega', header: 'Días', meta: { align: 'right' },
          cell: ({ row }) => row.original.dias_desde_entrega ?? '—' },
    ];

    const sinEpp = data.filter((r) => r.sin_epp).length;

    return (
        <div>
            <div className="rep-filtros">
                <FiltrosOrganizacion cat={cat} filtros={filtros} setFiltro={setFiltro} />
                <select className="modal-input" value={filtros.categoria_id}
                    onChange={(e) => setFiltro({ categoria_id: e.target.value })}>
                    <option value="">Todas las categorías</option>
                    {cat.categorias.map((c) => (
                        <option key={c.categoria_id} value={c.categoria_id}>{c.nombre_categoria}</option>
                    ))}
                </select>
                <select className="modal-input" value={filtros.producto_id}
                    onChange={(e) => setFiltro({ producto_id: e.target.value })}>
                    <option value="">Todos los productos</option>
                    {cat.productos.map((p) => (
                        <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>
                    ))}
                </select>
                <label className="rep-check">
                    <input type="checkbox" checked={filtros.incluir_inactivos}
                        onChange={(e) => setFiltro({ incluir_inactivos: e.target.checked })} />
                    Incluir desvinculados
                </label>
            </div>

            <p className="rep-nota">
                Al filtrar por producto o categoría, quien no lo tenga aparece igual marcado como
                «Sin EPP asignado» — el reporte sirve tanto para ver quién tiene como quién falta.
            </p>

            <div className="rep-acciones">
                <span className="rep-conteo">
                    {loading ? 'Cargando…' : `${data.length} filas · ${sinEpp} sin EPP`}
                </span>
                <BotonExcel onDescargar={descargarEppVigentes} filtros={filtros} />
            </div>

            <DataTable columns={columns} data={data} loading={loading} filterable
                initialSort={[{ id: 'nombre_completo', desc: false }]}
                emptyState={<div className="xls xls--state">Sin trabajadores para estos filtros.</div>} />
        </div>
    );
};

// ── Tab 3: Stock ──────────────────────────────────────────────────────────────
const TabStock = ({ cat }) => {
    const [filtros, setFiltros] = useState({ categoria_id: '', solo_alertas: false, dias_consumo: 90 });
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    const setFiltro = (parcial) => setFiltros((f) => ({ ...f, ...parcial }));

    const cargar = useCallback(async () => {
        setLoading(true);
        try { setData(await getStock(limpiar(filtros))); }
        catch (err) { toast.error(err.message || 'Error al cargar el reporte'); setData([]); }
        finally { setLoading(false); }
    }, [filtros]);
    useEffect(() => { cargar(); }, [cargar]);

    const columns = [
        { accessorKey: 'categoria', header: 'Categoría',
          cell: ({ row }) => row.original.categoria || '—' },
        { accessorKey: 'producto', header: 'Producto' },
        { accessorKey: 'talla', header: 'Talla', meta: { align: 'center' },
          cell: ({ row }) => row.original.talla || '—' },
        { accessorKey: 'cantidad_actual', header: 'Actual', meta: { align: 'right' } },
        { accessorKey: 'stock_minimo', header: 'Mínimo', meta: { align: 'right' } },
        { accessorKey: 'estado', header: 'Estado', meta: { align: 'center', filter: 'select' },
          cell: ({ row }) => (
              <span className={`dash-badge dash-badge--${row.original.estado.toLowerCase()}`}>
                  {row.original.estado}
              </span>
          ) },
        { accessorKey: 'consumo', header: `Consumo ${filtros.dias_consumo}d`, meta: { align: 'right' } },
        { accessorKey: 'cobertura_dias', header: 'Cobertura', meta: { align: 'right' },
          cell: ({ row }) => (row.original.cobertura_dias != null
              ? `${row.original.cobertura_dias} días` : '—') },
    ];

    const criticos = data.filter((r) => r.estado !== 'OK').length;

    return (
        <div>
            <div className="rep-filtros">
                <select className="modal-input" value={filtros.categoria_id}
                    onChange={(e) => setFiltro({ categoria_id: e.target.value })}>
                    <option value="">Todas las categorías</option>
                    {cat.categorias.map((c) => (
                        <option key={c.categoria_id} value={c.categoria_id}>{c.nombre_categoria}</option>
                    ))}
                </select>
                <select className="modal-input" value={filtros.dias_consumo}
                    onChange={(e) => setFiltro({ dias_consumo: Number(e.target.value) })}>
                    <option value={30}>Consumo últimos 30 días</option>
                    <option value={90}>Consumo últimos 90 días</option>
                    <option value={180}>Consumo últimos 180 días</option>
                    <option value={365}>Consumo último año</option>
                </select>
                <label className="rep-check">
                    <input type="checkbox" checked={filtros.solo_alertas}
                        onChange={(e) => setFiltro({ solo_alertas: e.target.checked })} />
                    Solo bajo mínimo
                </label>
            </div>

            <p className="rep-nota">
                La cobertura estima cuántos días alcanza el stock actual al ritmo de consumo de la
                ventana elegida. Sin consumo en el periodo no se puede estimar.
            </p>

            <div className="rep-acciones">
                <span className="rep-conteo">
                    {loading ? 'Cargando…' : `${data.length} ítems · ${criticos} en alerta`}
                </span>
                <BotonExcel onDescargar={descargarStock} filtros={filtros} />
            </div>

            <DataTable columns={columns} data={data} loading={loading} filterable
                emptyState={<div className="xls xls--state">Sin stock registrado.</div>} />
        </div>
    );
};

// ── Página ────────────────────────────────────────────────────────────────────
const Reports = () => {
    const [tab, setTab] = useState('trazabilidad');
    const cat = useCatalogos();

    return (
        <div className="page-container">
            <div className="inventory-tabs">
                <button className={`inventory-tab ${tab === 'trazabilidad' ? 'active' : ''}`}
                    onClick={() => setTab('trazabilidad')}>Trazabilidad</button>
                <button className={`inventory-tab ${tab === 'vigentes' ? 'active' : ''}`}
                    onClick={() => setTab('vigentes')}>EPP vigentes</button>
                <button className={`inventory-tab ${tab === 'stock' ? 'active' : ''}`}
                    onClick={() => setTab('stock')}>Stock</button>
            </div>

            {tab === 'trazabilidad' && <TabTrazabilidad cat={cat} />}
            {tab === 'vigentes' && <TabVigentes cat={cat} />}
            {tab === 'stock' && <TabStock cat={cat} />}
        </div>
    );
};

export default Reports;
