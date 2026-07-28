import { useState, useEffect, useCallback, useMemo } from "react";
import { useLocation } from "react-router-dom";
import toast from "react-hot-toast";
import { searchEmployees } from "../services/staffService";
import { getProductos } from "../services/eppService";
import { getTallas } from "../services/catalogosService";
import { getEntregas, crearEntregas, crearSustitucion, getVigentes } from "../services/entregasService";
import SustitucionModal from "../components/entregas/SustitucionModal";
import DataTable from "../components/common/DataTable";
import "./Page.css";
import "./Inventory.css";

const MOTIVOS = [
  { v: "NUEVA", label: "Nueva" },
  { v: "PERDIDA", label: "Reposición por pérdida" },
];

const itemLabel = (nombre, talla) => [nombre, talla].filter(Boolean).join(" · ");

// ── Tab: Registrar entrega ────────────────────────────────────────────────────
const TabRegistrar = () => {
  const [search, setSearch] = useState("");
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [trabajador, setTrabajador] = useState(null);

  const [productos, setProductos] = useState([]);
  const [tallas, setTallas] = useState([]);

  const [carrito, setCarrito] = useState([]);
  const [addProd, setAddProd] = useState("");
  const [addTalla, setAddTalla] = useState("");
  const [addCant, setAddCant] = useState("1");
  const [addMotivo, setAddMotivo] = useState("NUEVA");
  // Solo para PERDIDA: qué entrega vigente se dio por perdida. Sin vincularla,
  // el EPP perdido sigue contando como vigente junto a su reposición y el
  // reporte general muestra dos donde hay uno.
  const [addReemplaza, setAddReemplaza] = useState("");

  const [vigentes, setVigentes] = useState([]);
  const [loadingVig, setLoadingVig] = useState(false);
  const [confirmando, setConfirmando] = useState(false);

  const [sustituyendo, setSustituyendo] = useState(null);
  const [guardandoSus, setGuardandoSus] = useState(false);
  const [errorSus, setErrorSus] = useState("");

  useEffect(() => {
    Promise.all([getProductos({ activo: true }), getTallas()])
      .then(([p, t]) => { setProductos(p); setTallas(t); })
      .catch(() => {});
  }, []);

  // RUT precargado desde el modal de EPP de la página Personal
  const location = useLocation();
  useEffect(() => {
    if (location.state?.rut) setSearch(location.state.rut);
  }, [location.state]);

  // Búsqueda de trabajador (debounce)
  useEffect(() => {
    if (!search.trim() || trabajador) { setResultados([]); return; }
    setBuscando(true);
    const id = setTimeout(async () => {
      try { setResultados(await searchEmployees(search.trim())); }
      catch { setResultados([]); }
      finally { setBuscando(false); }
    }, 300);
    return () => clearTimeout(id);
  }, [search, trabajador]);

  const cargarVigentes = useCallback(async (rut) => {
    setLoadingVig(true);
    try { setVigentes(await getVigentes(rut)); }
    catch { setVigentes([]); }
    finally { setLoadingVig(false); }
  }, []);

  const seleccionar = (t) => {
    setTrabajador(t);
    setSearch("");
    setResultados([]);
    setCarrito([]);
    cargarVigentes(t.rut);
  };

  const limpiarTrabajador = () => {
    setTrabajador(null); setCarrito([]); setVigentes([]);
  };

  const prodSel = useMemo(
    () => productos.find((p) => p.producto_id === Number(addProd)),
    [productos, addProd]
  );

  // Vigentes que todavía se pueden dar por perdidos: se descuentan los que ya
  // están vinculados por otra línea del carrito (el backend rechazaría el
  // segundo intento, mejor no ofrecerlo).
  const yaVinculadas = new Set(
    carrito.map((l) => l.entrega_reemplazada_id).filter(Boolean)
  );
  const vigentesDisponibles = vigentes.filter((v) => !yaVinculadas.has(v.entrega_id));

  const agregarLinea = () => {
    if (!addProd) return toast.error("Selecciona un producto");
    if (prodSel?.talla_aplica && !addTalla) return toast.error("Este producto requiere talla");
    if (Number(addCant) <= 0) return toast.error("Cantidad inválida");
    const talla = tallas.find((t) => t.TallaID === Number(addTalla));
    const reemplazada = addMotivo === "PERDIDA" && addReemplaza
      ? vigentes.find((v) => v.entrega_id === Number(addReemplaza))
      : null;
    setCarrito((c) => [...c, {
      producto_id: Number(addProd),
      nombre: prodSel.nombre,
      talla_id: prodSel.talla_aplica ? Number(addTalla) : null,
      nombre_talla: prodSel.talla_aplica ? talla?.nombreTalla : null,
      cantidad: Number(addCant),
      motivo: addMotivo,
      entrega_reemplazada_id: reemplazada?.entrega_id ?? null,
      reemplaza_label: reemplazada
        ? itemLabel(reemplazada.nombre_producto, reemplazada.nombre_talla)
        : null,
    }]);
    setAddProd(""); setAddTalla(""); setAddCant("1");
    setAddMotivo("NUEVA"); setAddReemplaza("");
  };

  const quitarLinea = (i) => setCarrito((c) => c.filter((_, idx) => idx !== i));

  const confirmar = async () => {
    if (carrito.length === 0) return;
    setConfirmando(true);
    try {
      await crearEntregas({
        rut: trabajador.rut,
        lineas: carrito.map((l) => ({
          producto_id: l.producto_id, talla_id: l.talla_id,
          cantidad: l.cantidad, motivo: l.motivo,
          entrega_reemplazada_id: l.entrega_reemplazada_id,
        })),
      });
      toast.success(`Entrega registrada (${carrito.length} ítem${carrito.length > 1 ? "s" : ""})`);
      setCarrito([]);
      cargarVigentes(trabajador.rut);
    } catch (err) {
      toast.error(err.message || "Error al registrar la entrega");
    } finally { setConfirmando(false); }
  };

  const guardarSustitucion = async (data) => {
    setGuardandoSus(true); setErrorSus("");
    try {
      await crearSustitucion({
        rut: trabajador.rut,
        entrega_reemplazada_id: sustituyendo.entrega_id,
        ...data,
      });
      toast.success("Sustitución registrada");
      setSustituyendo(null);
      cargarVigentes(trabajador.rut);
    } catch (err) {
      setErrorSus(err.message || "Error en la sustitución");
    } finally { setGuardandoSus(false); }
  };

  return (
    <div>
      {/* Búsqueda de trabajador */}
      {!trabajador ? (
        <div style={{ maxWidth: 480, position: "relative" }}>
          <label className="modal-label">Buscar trabajador (nombre o RUT)</label>
          <input className="modal-input" value={search} autoFocus
            onChange={(e) => setSearch(e.target.value)} placeholder="Ej: Juan Pérez o 11.111.111-1" />
          {buscando && <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 6 }}>Buscando…</p>}
          {resultados.length > 0 && (
            <div style={{
              position: "absolute", zIndex: 10, left: 0, right: 0, marginTop: 4,
              background: "var(--color-card)", border: "1px solid var(--color-card-border)",
              borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.12)", maxHeight: 280, overflowY: "auto",
            }}>
              {resultados.map((t) => (
                <button key={t.rut} onClick={() => seleccionar(t)} style={{
                  display: "block", width: "100%", textAlign: "left", padding: "10px 12px",
                  background: "transparent", border: "none", borderBottom: "1px solid var(--color-card-border)",
                  cursor: "pointer", color: "var(--color-text-primary)", fontSize: 14,
                }}>
                  <strong>{t.nombre_completo}</strong>
                  <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}> — {t.rut} · {t.empresa}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div>
          {/* Ficha trabajador */}
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "14px 16px", background: "var(--color-card)", border: "1px solid var(--color-card-border)",
            borderRadius: 10, marginBottom: 20,
          }}>
            <div>
              <p style={{ fontWeight: 700, fontSize: 16, color: "var(--color-text-primary)" }}>{trabajador.nombre_completo}</p>
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                {trabajador.rut} · {trabajador.empresa}{trabajador.cargo ? ` · ${trabajador.cargo}` : ""}
                {trabajador.nombre_subarea ? ` · ${trabajador.nombre_subarea}` : ""}
              </p>
            </div>
            <button className="catalogo-btn catalogo-btn--cancel" onClick={limpiarTrabajador}>Cambiar</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
            {/* Nueva entrega */}
            <div>
              <h3 className="catalogo-tab-title" style={{ marginBottom: 12 }}>Nueva entrega</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                <select className="modal-input" value={addProd}
                  onChange={(e) => { setAddProd(e.target.value); setAddTalla(""); }}>
                  <option value="">— Producto —</option>
                  {productos.map((p) => <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>)}
                </select>
                {prodSel?.talla_aplica && (
                  <select className="modal-input" value={addTalla} onChange={(e) => setAddTalla(e.target.value)}>
                    <option value="">— Talla —</option>
                    {tallas.map((t) => <option key={t.TallaID} value={t.TallaID}>{t.nombreTalla}</option>)}
                  </select>
                )}
                <div style={{ display: "flex", gap: 8 }}>
                  <input className="modal-input" type="number" min="1" value={addCant}
                    onChange={(e) => setAddCant(e.target.value)} style={{ width: 90 }} title="Cantidad" />
                  <select className="modal-input" value={addMotivo}
                    onChange={(e) => { setAddMotivo(e.target.value); setAddReemplaza(""); }}>
                    {MOTIVOS.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
                  </select>
                </div>

                {addMotivo === "PERDIDA" && (
                  <div>
                    <select className="modal-input" value={addReemplaza}
                      onChange={(e) => setAddReemplaza(e.target.value)}
                      disabled={vigentesDisponibles.length === 0}>
                      <option value="">— ¿Qué EPP se perdió? (opcional) —</option>
                      {vigentesDisponibles.map((v) => (
                        <option key={v.entrega_id} value={v.entrega_id}>
                          {itemLabel(v.nombre_producto, v.nombre_talla)} · {new Date(v.fecha_entrega).toLocaleDateString("es-CL")}
                        </option>
                      ))}
                    </select>
                    <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 6, lineHeight: 1.45 }}>
                      {vigentesDisponibles.length === 0
                        ? "Este trabajador no tiene EPP vigentes para dar de baja."
                        : "Si no lo indicas, el EPP perdido seguirá figurando como vigente junto a esta reposición."}
                    </p>
                  </div>
                )}

                <button className="catalogo-btn catalogo-btn--edit" onClick={agregarLinea}>+ Agregar al carrito</button>
              </div>

              {carrito.length > 0 && (
                <div style={{ border: "1px solid var(--color-card-border)", borderRadius: 8, overflow: "hidden" }}>
                  {carrito.map((l, i) => (
                    <div key={i} style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "8px 12px", borderBottom: "1px solid var(--color-card-border)", fontSize: 14,
                    }}>
                      <span>{itemLabel(l.nombre, l.nombre_talla)} × {l.cantidad}
                        <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}> · {MOTIVOS.find(m => m.v === l.motivo)?.label}</span>
                        {l.reemplaza_label && (
                          <span style={{ display: "block", color: "var(--color-text-muted)", fontSize: 12 }}>
                            da de baja: {l.reemplaza_label}
                          </span>
                        )}
                      </span>
                      <button className="catalogo-btn catalogo-btn--delete" onClick={() => quitarLinea(i)}>Quitar</button>
                    </div>
                  ))}
                  <div style={{ padding: 12 }}>
                    <button className="catalogo-btn catalogo-btn--primary" style={{ width: "100%" }}
                      onClick={confirmar} disabled={confirmando}>
                      {confirmando ? "Registrando…" : `Confirmar entrega (${carrito.length})`}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* EPP vigentes */}
            <div>
              <h3 className="catalogo-tab-title" style={{ marginBottom: 12 }}>EPP vigentes</h3>
              {loadingVig ? (
                <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>Cargando…</p>
              ) : vigentes.length === 0 ? (
                <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>Sin EPP vigentes.</p>
              ) : (
                <div style={{ border: "1px solid var(--color-card-border)", borderRadius: 8, overflow: "hidden" }}>
                  {vigentes.map((v) => (
                    <div key={v.entrega_id} style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "8px 12px", borderBottom: "1px solid var(--color-card-border)", fontSize: 14,
                    }}>
                      <span>{itemLabel(v.nombre_producto, v.nombre_talla)} × {v.cantidad}
                        <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}> · {new Date(v.fecha_entrega).toLocaleDateString("es-CL")}</span>
                      </span>
                      <button className="catalogo-btn catalogo-btn--edit"
                        onClick={() => { setErrorSus(""); setSustituyendo(v); }}>Sustituir</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {sustituyendo && (
        <SustitucionModal entregaReemplazada={sustituyendo} productos={productos} tallas={tallas}
          onGuardar={guardarSustitucion}
          onCerrar={() => { if (!guardandoSus) setSustituyendo(null); }}
          guardando={guardandoSus} errorServidor={errorSus} />
      )}
    </div>
  );
};

// ── Tab: Historial ────────────────────────────────────────────────────────────
const TabHistorial = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [motivo, setMotivo] = useState("");

  const cargar = useCallback(async () => {
    setLoading(true);
    try { setData(await getEntregas(motivo ? { motivo } : {})); }
    catch { setData([]); }
    finally { setLoading(false); }
  }, [motivo]);
  useEffect(() => { cargar(); }, [cargar]);

  const columns = [
    { accessorKey: "fecha_entrega", header: "Fecha",
      cell: ({ row }) => new Date(row.original.fecha_entrega).toLocaleDateString("es-CL") },
    { accessorKey: "nombre_completo", header: "Trabajador" },
    { accessorKey: "nombre_producto", header: "Producto",
      cell: ({ row }) => itemLabel(row.original.nombre_producto, row.original.nombre_talla) },
    { accessorKey: "cantidad", header: "Cant.", meta: { align: "right" } },
    { accessorKey: "motivo", header: "Motivo", meta: { align: "center", filter: "select" } },
    { accessorKey: "estado_firma", header: "Firma", meta: { align: "center" } },
  ];

  return (
    <div>
      <div className="catalogo-tab-header">
        <h3 className="catalogo-tab-title">Historial de entregas</h3>
        <select className="modal-input" style={{ maxWidth: 220 }} value={motivo} onChange={(e) => setMotivo(e.target.value)}>
          <option value="">Todos los motivos</option>
          <option value="NUEVA">Nueva</option>
          <option value="PERDIDA">Pérdida</option>
          <option value="DANO">Daño</option>
        </select>
      </div>
      <DataTable columns={columns} data={data} loading={loading} filterable
        initialSort={[{ id: "fecha_entrega", desc: true }]}
        emptyState={<div className="xls xls--state">Sin entregas registradas.</div>} />
    </div>
  );
};

// ── Página ────────────────────────────────────────────────────────────────────
const Entregas = () => {
  const [tab, setTab] = useState("registrar");
  return (
    <div className="page-container">
      <div className="inventory-tabs">
        <button className={`inventory-tab ${tab === "registrar" ? "active" : ""}`} onClick={() => setTab("registrar")}>Registrar</button>
        <button className={`inventory-tab ${tab === "historial" ? "active" : ""}`} onClick={() => setTab("historial")}>Historial</button>
      </div>
      {tab === "registrar" ? <TabRegistrar /> : <TabHistorial />}
    </div>
  );
};

export default Entregas;
