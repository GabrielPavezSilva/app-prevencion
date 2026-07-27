import { useState, useEffect, useCallback } from "react";
import toast from "react-hot-toast";
import { getTemplates, descargarPlantilla, importar, getImportaciones } from "../services/importacionesService";
import DataTable from "../components/common/DataTable";
import "./Page.css";
import "./Inventory.css";

// ── Tab: Importar ─────────────────────────────────────────────────────────────
const TabImportar = ({ onImportado }) => {
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState("");
  const [file, setFile] = useState(null);
  const [importando, setImportando] = useState(false);
  const [resultado, setResultado] = useState(null);

  useEffect(() => {
    getTemplates().then((t) => { setTemplates(t); if (t[0]) setTemplateId(t[0].id); }).catch(() => {});
  }, []);

  const template = templates.find((t) => t.id === templateId);

  const handleDescargar = async () => {
    try { await descargarPlantilla(templateId); }
    catch (err) { toast.error(err.message || "Error al descargar"); }
  };

  const handleImportar = async () => {
    if (!file) return toast.error("Selecciona un archivo");
    setImportando(true); setResultado(null);
    try {
      const res = await importar(templateId, file);
      setResultado(res);
      if (res.filas_error === 0) toast.success(`Importadas ${res.filas_ok} filas`);
      else toast(`OK: ${res.filas_ok} · Con error: ${res.filas_error}`, { icon: "⚠️" });
      setFile(null);
      onImportado?.();
    } catch (err) {
      toast.error(err.message || "Error al importar");
    } finally { setImportando(false); }
  };

  return (
    <div style={{ maxWidth: 620 }}>
      <div className="modal-field">
        <label className="modal-label">Tipo de importación</label>
        <select className="modal-input" value={templateId} onChange={(e) => { setTemplateId(e.target.value); setResultado(null); }}>
          {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>

      {template && (
        <div style={{
          padding: "12px 14px", background: "var(--color-card)", border: "1px solid var(--color-card-border)",
          borderRadius: 8, marginBottom: 16,
        }}>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 8 }}>{template.description}</p>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 10 }}>
            Columnas: {template.columns.map((c) => c.name + (c.required ? "*" : "")).join(", ")}
            <span style={{ marginLeft: 6 }}>(* obligatoria)</span>
          </p>
          <button className="catalogo-btn catalogo-btn--edit" onClick={handleDescargar}>↓ Descargar plantilla vacía</button>
        </div>
      )}

      <div className="modal-field">
        <label className="modal-label">Archivo (.xlsx, .xls, .csv)</label>
        <input className="modal-input" type="file" accept=".xlsx,.xls,.csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </div>

      <button className="catalogo-btn catalogo-btn--primary" onClick={handleImportar} disabled={importando || !file}>
        {importando ? "Importando…" : "Importar"}
      </button>

      {resultado && (
        <div style={{
          marginTop: 20, padding: "14px 16px", borderRadius: 8,
          background: "var(--color-card)", border: "1px solid var(--color-card-border)",
        }}>
          <p style={{ fontWeight: 600, marginBottom: 8 }}>
            Resultado: <span style={{ color: "#16a34a" }}>{resultado.filas_ok} OK</span>
            {resultado.filas_error > 0 && <span style={{ color: "#dc2626" }}> · {resultado.filas_error} con error</span>}
          </p>
          {resultado.errores?.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#dc2626", maxHeight: 220, overflowY: "auto" }}>
              {resultado.errores.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

// ── Tab: Historial ────────────────────────────────────────────────────────────
const TabHistorial = ({ refresh }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  const cargar = useCallback(async () => {
    setLoading(true);
    try { setData(await getImportaciones()); } catch { setData([]); } finally { setLoading(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar, refresh]);

  const columns = [
    { accessorKey: "fecha", header: "Fecha",
      cell: ({ row }) => new Date(row.original.fecha).toLocaleString("es-CL") },
    { accessorKey: "template_id", header: "Tipo" },
    { accessorKey: "nombre_archivo", header: "Archivo" },
    { accessorKey: "filas_ok", header: "OK", meta: { align: "right" } },
    { accessorKey: "filas_error", header: "Errores", meta: { align: "right" } },
  ];

  return (
    <DataTable columns={columns} data={data} loading={loading}
      initialSort={[{ id: "fecha", desc: true }]}
      emptyState={<div className="xls xls--state">Sin importaciones registradas.</div>} />
  );
};

// ── Página ────────────────────────────────────────────────────────────────────
const Importaciones = () => {
  const [tab, setTab] = useState("importar");
  const [refresh, setRefresh] = useState(0);

  return (
    <div className="page-container">
      <div className="inventory-tabs">
        <button className={`inventory-tab ${tab === "importar" ? "active" : ""}`} onClick={() => setTab("importar")}>Importar</button>
        <button className={`inventory-tab ${tab === "historial" ? "active" : ""}`} onClick={() => setTab("historial")}>Historial</button>
      </div>
      {tab === "importar"
        ? <TabImportar onImportado={() => setRefresh((r) => r + 1)} />
        : <TabHistorial refresh={refresh} />}
    </div>
  );
};

export default Importaciones;
