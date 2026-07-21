import { useState, useEffect, useCallback } from "react";
import {
  getTipos,
  createTipo,
  updateTipo,
  deleteTipo,
  getTallas,
  createTalla,
  updateTalla,
  deleteTalla,
} from "../services/catalogosService";
import CatalogoTable from "../components/inventory/CatalogoTable";
import CatalogoModal from "../components/inventory/CatalogoModal";
import ConfirmDeleteModal from "../components/inventory/ConfirmDeleteModal";
import "./Page.css";
import "./Inventory.css";

// ── Tab: Catálogo genérico (CRUD nombre único) ───────────────────────────────
// Fase 0 del clon prevención: la página queda reducida a catálogos.
// Los tabs de stock EPP e importadores se agregan en Fases 1-3
// (ver docs/plans/2026-07-21-clon-prevencion-epp-design.md).

const TabCatalogo = ({
  titulo,
  idKey,
  nombreKey,
  fetchFn,
  createFn,
  updateFn,
  deleteFn,
  onCatalogoChange,
}) => {
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
    try {
      const data = await fetchFn();
      setItems(data);
      onCatalogoChange?.();
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, onCatalogoChange]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const abrirCrear = () => {
    setItemEditando(null);
    setErrorModal("");
    setModalAbierto(true);
  };

  const abrirEditar = (item) => {
    setItemEditando(item);
    setErrorModal("");
    setModalAbierto(true);
  };

  const cerrarModal = () => {
    if (guardando) return;
    setModalAbierto(false);
    setItemEditando(null);
    setErrorModal("");
  };

  const handleGuardar = async (nombre) => {
    setGuardando(true);
    setErrorModal("");
    try {
      if (itemEditando) {
        await updateFn(itemEditando[idKey], nombre);
      } else {
        await createFn(nombre);
      }
      setModalAbierto(false);
      setItemEditando(null);
      await cargar();
    } catch (err) {
      setErrorModal(err.message || "Error al guardar");
    } finally {
      setGuardando(false);
    }
  };

  const abrirConfirmEliminar = (item) => {
    setItemEliminando(item);
    setErrorEliminar("");
  };

  const cerrarConfirmEliminar = () => {
    if (eliminando) return;
    setItemEliminando(null);
    setErrorEliminar("");
  };

  const handleEliminar = async () => {
    setEliminando(true);
    setErrorEliminar("");
    try {
      await deleteFn(itemEliminando[idKey]);
      setItemEliminando(null);
      await cargar();
    } catch (err) {
      setErrorEliminar(err.message || "Error al eliminar");
    } finally {
      setEliminando(false);
    }
  };

  return (
    <>
      <div className="catalogo-tab-header">
        <h3 className="catalogo-tab-title">{titulo}</h3>
        <button
          className="catalogo-btn catalogo-btn--primary"
          onClick={abrirCrear}
        >
          + Agregar
        </button>
      </div>

      <CatalogoTable
        items={items}
        idKey={idKey}
        nombreKey={nombreKey}
        onEditar={abrirEditar}
        onEliminar={abrirConfirmEliminar}
        loading={loading}
      />

      {modalAbierto && (
        <CatalogoModal
          titulo={itemEditando ? `Editar ${titulo}` : `Nuevo ${titulo}`}
          valorInicial={itemEditando ? itemEditando[nombreKey] : ""}
          onGuardar={handleGuardar}
          onCerrar={cerrarModal}
          guardando={guardando}
          errorServidor={errorModal}
        />
      )}

      {itemEliminando && (
        <ConfirmDeleteModal
          mensaje={`¿Eliminar "${itemEliminando[nombreKey]}"? Esta acción no se puede deshacer.`}
          errorServidor={errorEliminar}
          onConfirmar={handleEliminar}
          onCerrar={cerrarConfirmEliminar}
          eliminando={eliminando}
        />
      )}
    </>
  );
};

// ── Página principal ──────────────────────────────────────────────────────────

const Inventory = () => {
  const [activeTab, setActiveTab] = useState("tipos");

  const tabs = [
    { id: "tipos", label: "Tipos de EPP" },
    { id: "tallas", label: "Tallas" },
  ];

  return (
    <div className="page-container">
      <div className="inventory-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`inventory-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "tipos" && (
        <TabCatalogo
          titulo="Tipo de EPP"
          idKey="TipoID"
          nombreKey="nombreTipo"
          fetchFn={getTipos}
          createFn={createTipo}
          updateFn={updateTipo}
          deleteFn={deleteTipo}
        />
      )}

      {activeTab === "tallas" && (
        <TabCatalogo
          titulo="Talla"
          idKey="TallaID"
          nombreKey="nombreTalla"
          fetchFn={getTallas}
          createFn={createTalla}
          updateFn={updateTalla}
          deleteFn={deleteTalla}
        />
      )}
    </div>
  );
};

export default Inventory;
