import { useState, useEffect, useCallback } from "react";
import {
  getCategorias, createCategoria, updateCategoria, deleteCategoria,
  getProductos, createProducto, updateProducto, deleteProducto,
  getStock, ajustarStock, getRecintos,
} from "../services/eppService";
import { getTallas, createTalla, updateTalla, deleteTalla } from "../services/catalogosService";
import CatalogoTable from "../components/inventory/CatalogoTable";
import CatalogoModal from "../components/inventory/CatalogoModal";
import ConfirmDeleteModal from "../components/inventory/ConfirmDeleteModal";
import ProductoModal from "../components/inventory/ProductoModal";
import AjusteStockModal from "../components/inventory/AjusteStockModal";
import DataTable from "../components/common/DataTable";
import { useAuth } from "../context/AuthContextModel";
import "./Page.css";
import "./Inventory.css";

// ── Badge reutilizable ────────────────────────────────────────────────────────
const Badge = ({ texto, color }) => (
  <span style={{
    display: "inline-block", padding: "2px 10px", borderRadius: 999,
    fontSize: 12, fontWeight: 600, background: `${color}1a`, color,
    border: `1px solid ${color}40`,
  }}>{texto}</span>
);

// ── Tab: Catálogo genérico (CRUD nombre único) ───────────────────────────────
const TabCatalogo = ({ titulo, idKey, nombreKey, fetchFn, createFn, updateFn, deleteFn }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [itemEditando, setItemEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState("");
  const [itemEliminando, setItemEliminando] = useState(null);
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState("");

  const cargar = useCallback(async () => {
    setLoading(true);
    try { setItems(await fetchFn()); } catch { setItems([]); } finally { setLoading(false); }
  }, [fetchFn]);

  useEffect(() => { cargar(); }, [cargar]);

  const handleGuardar = async (nombre) => {
    setGuardando(true); setErrorModal("");
    try {
      if (itemEditando) await updateFn(itemEditando[idKey], nombre);
      else await createFn(nombre);
      setModalAbierto(false); setItemEditando(null); await cargar();
    } catch (err) { setErrorModal(err.message || "Error al guardar"); }
    finally { setGuardando(false); }
  };

  const handleEliminar = async () => {
    setEliminando(true); setErrorEliminar("");
    try { await deleteFn(itemEliminando[idKey]); setItemEliminando(null); await cargar(); }
    catch (err) { setErrorEliminar(err.message || "Error al eliminar"); }
    finally { setEliminando(false); }
  };

  return (
    <>
      <div className="catalogo-tab-header">
        <h3 className="catalogo-tab-title">{titulo}</h3>
        <button className="catalogo-btn catalogo-btn--primary"
          onClick={() => { setItemEditando(null); setErrorModal(""); setModalAbierto(true); }}>
          + Agregar
        </button>
      </div>
      <CatalogoTable items={items} idKey={idKey} nombreKey={nombreKey}
        onEditar={(it) => { setItemEditando(it); setErrorModal(""); setModalAbierto(true); }}
        onEliminar={(it) => { setItemEliminando(it); setErrorEliminar(""); }}
        loading={loading} />
      {modalAbierto && (
        <CatalogoModal
          titulo={itemEditando ? `Editar ${titulo}` : `Nuevo ${titulo}`}
          valorInicial={itemEditando ? itemEditando[nombreKey] : ""}
          onGuardar={handleGuardar}
          onCerrar={() => { if (!guardando) { setModalAbierto(false); setItemEditando(null); setErrorModal(""); } }}
          guardando={guardando} errorServidor={errorModal} />
      )}
      {itemEliminando && (
        <ConfirmDeleteModal
          mensaje={`¿Eliminar "${itemEliminando[nombreKey]}"? Esta acción no se puede deshacer.`}
          errorServidor={errorEliminar} onConfirmar={handleEliminar}
          onCerrar={() => { if (!eliminando) { setItemEliminando(null); setErrorEliminar(""); } }}
          eliminando={eliminando} />
      )}
    </>
  );
};

// ── Tab: Productos ────────────────────────────────────────────────────────────
const TabProductos = () => {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState("");
  const [eliminando, setEliminando] = useState(null);
  const [borrando, setBorrando] = useState(false);
  const [errorBorrar, setErrorBorrar] = useState("");

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const [prod, cats] = await Promise.all([getProductos(), getCategorias()]);
      setProductos(prod); setCategorias(cats);
    } catch { setProductos([]); } finally { setLoading(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const handleGuardar = async (data) => {
    setGuardando(true); setErrorModal("");
    try {
      if (editando) await updateProducto(editando.producto_id, data);
      else await createProducto(data);
      setModal(false); setEditando(null); await cargar();
    } catch (err) { setErrorModal(err.message || "Error al guardar"); }
    finally { setGuardando(false); }
  };

  const handleEliminar = async () => {
    setBorrando(true); setErrorBorrar("");
    try { await deleteProducto(eliminando.producto_id); setEliminando(null); await cargar(); }
    catch (err) { setErrorBorrar(err.message || "Error al eliminar"); }
    finally { setBorrando(false); }
  };

  const columns = [
    { accessorKey: "nombre", header: "Producto" },
    { accessorKey: "nombre_categoria", header: "Categoría",
      cell: ({ row }) => row.original.nombre_categoria || "—" },
    { accessorKey: "talla_aplica", header: "Tallas", meta: { align: "center" },
      cell: ({ row }) => (row.original.talla_aplica ? "Sí" : "No") },
    { accessorKey: "certificacion", header: "Certificación",
      cell: ({ row }) => row.original.certificacion || "—" },
    { accessorKey: "vida_util_meses", header: "Vida útil", meta: { align: "center" },
      cell: ({ row }) => row.original.vida_util_meses
        ? `${row.original.vida_util_meses} meses` : "—" },
    { accessorKey: "activo", header: "Estado", meta: { align: "center" },
      cell: ({ row }) => row.original.activo
        ? <Badge texto="Activo" color="#16a34a" /> : <Badge texto="Inactivo" color="#94a3b8" /> },
    { id: "acciones", header: "", meta: { align: "center" },
      cell: ({ row }) => (
        <div style={{ display: "flex", gap: 6, justifyContent: "center" }}>
          <button className="catalogo-btn catalogo-btn--edit"
            onClick={() => { setEditando(row.original); setErrorModal(""); setModal(true); }}>Editar</button>
          <button className="catalogo-btn catalogo-btn--delete"
            onClick={() => { setEliminando(row.original); setErrorBorrar(""); }}>Eliminar</button>
        </div>
      ) },
  ];

  return (
    <>
      <div className="catalogo-tab-header">
        <h3 className="catalogo-tab-title">Productos EPP</h3>
        <button className="catalogo-btn catalogo-btn--primary"
          onClick={() => { setEditando(null); setErrorModal(""); setModal(true); }}>
          + Nuevo producto
        </button>
      </div>
      <DataTable columns={columns} data={productos} loading={loading}
        initialSort={[{ id: "nombre", desc: false }]}
        emptyState={<div className="xls xls--state">Aún no hay productos. Crea uno o impórtalos.</div>} />
      {modal && (
        <ProductoModal producto={editando} categorias={categorias}
          onGuardar={handleGuardar}
          onCerrar={() => { if (!guardando) { setModal(false); setEditando(null); } }}
          guardando={guardando} errorServidor={errorModal} />
      )}
      {eliminando && (
        <ConfirmDeleteModal
          mensaje={`¿Eliminar el producto "${eliminando.nombre}"? Si tiene stock o entregas, desactívalo en su lugar.`}
          errorServidor={errorBorrar} onConfirmar={handleEliminar}
          onCerrar={() => { if (!borrando) { setEliminando(null); setErrorBorrar(""); } }}
          eliminando={borrando} />
      )}
    </>
  );
};

// ── Tab: Stock ────────────────────────────────────────────────────────────────
const TabStock = () => {
  const { user } = useAuth();
  // Sin recinto propio (admin) hay que elegirlo en cada movimiento; con recinto
  // propio el backend lo impone. Es la misma señal que usa `resolver_recinto`,
  // así no hay dos listas de roles que se desincronicen.
  const puedeElegirRecinto = user?.recinto_id == null;

  const [stock, setStock] = useState([]);
  const [productos, setProductos] = useState([]);
  const [tallas, setTallas] = useState([]);
  const [recintos, setRecintos] = useState([]);
  const [filtroRecinto, setFiltroRecinto] = useState("");
  const [loading, setLoading] = useState(true);
  const [soloBajoMinimo, setSoloBajoMinimo] = useState(false);
  const [modal, setModal] = useState(false);
  const [ajustando, setAjustando] = useState(null); // stockRow o null (nuevo)
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState("");

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const [st, prod, tll, rec] = await Promise.all([
        getStock({
          ...(soloBajoMinimo ? { bajo_minimo: true } : {}),
          ...(filtroRecinto ? { recinto_id: filtroRecinto } : {}),
        }),
        getProductos(), getTallas(), getRecintos(),
      ]);
      setStock(st); setProductos(prod); setTallas(tll); setRecintos(rec);
    } catch { setStock([]); } finally { setLoading(false); }
  }, [soloBajoMinimo, filtroRecinto]);
  useEffect(() => { cargar(); }, [cargar]);

  const handleGuardar = async (data) => {
    setGuardando(true); setErrorModal("");
    try { await ajustarStock(data); setModal(false); setAjustando(null); await cargar(); }
    catch (err) { setErrorModal(err.message || "Error al ajustar"); }
    finally { setGuardando(false); }
  };

  const columns = [
    { accessorKey: "nombre_recinto", header: "Recinto" },
    { accessorKey: "nombre_producto", header: "Producto" },
    { accessorKey: "nombre_categoria", header: "Categoría",
      cell: ({ row }) => row.original.nombre_categoria || "—" },
    { accessorKey: "nombre_talla", header: "Talla", meta: { align: "center" },
      cell: ({ row }) => row.original.nombre_talla || "—" },
    { accessorKey: "cantidad_actual", header: "Cantidad", meta: { align: "right" } },
    { accessorKey: "stock_minimo", header: "Mínimo", meta: { align: "right" } },
    { accessorKey: "bajo_minimo", header: "Estado", meta: { align: "center" },
      cell: ({ row }) => row.original.bajo_minimo
        ? <Badge texto="Bajo mínimo" color="#dc2626" /> : <Badge texto="OK" color="#16a34a" /> },
    { id: "acciones", header: "", meta: { align: "center" },
      cell: ({ row }) => (
        <button className="catalogo-btn catalogo-btn--edit"
          onClick={() => { setAjustando(row.original); setErrorModal(""); setModal(true); }}>Ajustar</button>
      ) },
  ];

  return (
    <>
      <div className="catalogo-tab-header">
        <h3 className="catalogo-tab-title">Stock</h3>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <select className="modal-input" style={{ width: "auto", fontSize: 13 }}
            value={filtroRecinto} onChange={(e) => setFiltroRecinto(e.target.value)}>
            <option value="">Todos los recintos</option>
            {recintos.map((r) => (
              <option key={r.recinto_id} value={r.recinto_id}>{r.nombre_recinto}</option>
            ))}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer", color: "var(--color-text-secondary)" }}>
            <input type="checkbox" checked={soloBajoMinimo} onChange={(e) => setSoloBajoMinimo(e.target.checked)} />
            Solo bajo mínimo
          </label>
          <button className="catalogo-btn catalogo-btn--primary"
            onClick={() => { setAjustando(null); setErrorModal(""); setModal(true); }}>
            + Cargar / ajustar
          </button>
        </div>
      </div>
      <DataTable columns={columns} data={stock} loading={loading}
        initialSort={[{ id: "nombre_recinto", desc: false }]}
        emptyState={<div className="xls xls--state">Sin stock registrado. Usa "Cargar / ajustar" o el importador.</div>} />
      {modal && (
        <AjusteStockModal stockRow={ajustando} productos={productos} tallas={tallas}
          recintos={recintos} recintoPropio={user?.recinto_id ?? null}
          puedeElegirRecinto={puedeElegirRecinto}
          onGuardar={handleGuardar}
          onCerrar={() => { if (!guardando) { setModal(false); setAjustando(null); } }}
          guardando={guardando} errorServidor={errorModal} />
      )}
    </>
  );
};

// ── Página principal ──────────────────────────────────────────────────────────
const Inventory = () => {
  const [activeTab, setActiveTab] = useState("productos");
  const tabs = [
    { id: "productos", label: "Productos" },
    { id: "stock", label: "Stock" },
    { id: "categorias", label: "Categorías" },
    { id: "tallas", label: "Tallas" },
  ];

  return (
    <div className="page-container">
      <div className="inventory-tabs">
        {tabs.map((tab) => (
          <button key={tab.id}
            className={`inventory-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "productos" && <TabProductos />}
      {activeTab === "stock" && <TabStock />}
      {activeTab === "categorias" && (
        <TabCatalogo titulo="Categoría" idKey="categoria_id" nombreKey="nombre_categoria"
          fetchFn={getCategorias} createFn={createCategoria} updateFn={updateCategoria} deleteFn={deleteCategoria} />
      )}
      {activeTab === "tallas" && (
        <TabCatalogo titulo="Talla" idKey="TallaID" nombreKey="nombreTalla"
          fetchFn={getTallas} createFn={createTalla} updateFn={updateTalla} deleteFn={deleteTalla} />
      )}
    </div>
  );
};

export default Inventory;
