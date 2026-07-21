from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class ReportesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_inventario(self, empresa_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene los datos crudos para el reporte de inventario desde lecturas_rfid.
        Si empresa_id viene informado, filtra por esa empresa.
        """
        sql = """
            SELECT
                lr.sku                  AS "SKU",
                lr.estado_disponible    AS "Disponible",
                tp.nombre_tipo          AS "Tipo Prenda",
                t.nombre_talla          AS "Talla",
                s.nombre_seccion        AS "Sección",
                tmp.nombre_temporada    AS "Temporada",
                e.nombre_empresa        AS "Empresa"
            FROM lecturas_rfid lr
            JOIN tiposprendas tp  ON lr.tipo_id      = tp.tipo_id
            JOIN tallas       t   ON lr.talla_id     = t.talla_id
            JOIN secciones    s   ON lr.seccion_id   = s.seccion_id
            JOIN temporadas   tmp ON lr.temporada_id = tmp.temporada_id
            JOIN empresa      e   ON lr.empresa_id   = e.empresa_id
        """
        params = {}
        if empresa_id is not None:
            sql += " WHERE lr.empresa_id = :empresa_id"
            params["empresa_id"] = empresa_id
        query = text(sql)
        result = self.db.execute(query, params).mappings().fetchall()
        return [dict(row) for row in result]

    def get_asignaciones_filtradas(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Obtiene los datos de asignaciones filtrados por fecha.
        Los datos están directamente en la tabla asignaciones (sin JOINs extra).
        """
        sql = """
            SELECT 
                asignacion_id AS AsignacionID, 
                nombre_completo AS NombreCompleto,
                rut AS Rut,
                sku AS SKU, 
                tag_epc AS TagEPC,
                fecha_entrega AS FechaEntrega, 
                fecha_devolucion AS FechaDevolucion
            FROM asignaciones
            WHERE 1=1
        """
        params = {}
        if start_date:
            sql += " AND fecha_entrega >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND fecha_entrega <= :end_date"
            params["end_date"] = f"{end_date} 23:59:59"
            
        sql += " ORDER BY fecha_entrega DESC"
        
        query = text(sql)
        result = self.db.execute(query, params).mappings().fetchall()
        return [dict(row) for row in result]

    def bulk_insert_inventario_inicial(self, records: List[Dict[str, Any]]) -> dict:
        """
        Inserta registros masivos para inventario inicial.
        Resuelve referencias por nombre a IDs (tipo_prenda, talla, empresa).
        """
        if not records:
            return {"success": False, "message": "No hay registros para procesar", "recordsImported": 0}

        # 1. Cargar diccionarios de lookup para IDs
        tipos_map = {row.nombre_tipo.lower(): row.tipo_id for row in self.db.execute(text("SELECT tipo_id, nombre_tipo FROM tiposprendas")).fetchall()}
        tallas_map = {row.nombre_talla.lower(): row.talla_id for row in self.db.execute(text("SELECT talla_id, nombre_talla FROM tallas")).fetchall()}
        secciones_map = {row.nombre_seccion.lower(): row.seccion_id for row in self.db.execute(text("SELECT seccion_id, nombre_seccion FROM secciones")).fetchall()}
        temporadas_map = {row.nombre_temporada.lower(): row.temporada_id for row in self.db.execute(text("SELECT temporada_id, nombre_temporada FROM temporadas")).fetchall()}
        empresas_map = {row.nombre_empresa.lower(): row.empresa_id for row in self.db.execute(text("SELECT empresa_id, nombre_empresa FROM empresa")).fetchall()}

        from app.models.inventario import LecturaRFID

        inserted_count = 0
        errors = []

        for i, record in enumerate(records):
            sku = str(record.get('sku', '')).strip()
            tipo_nombre = str(record.get('tipo_prenda', '')).strip().lower()
            talla_nombre = str(record.get('talla', '')).strip().lower()
            seccion_nombre = str(record.get('seccion', '')).strip().lower()
            temporada_nombre = str(record.get('temporada', '')).strip().lower()
            empresa_nombre = str(record.get('empresa', '')).strip().lower()

            if not sku:
                errors.append(f"Fila {i+2}: SKU vacío.")
                continue

            # Buscar IDs
            tipo_id = tipos_map.get(tipo_nombre)
            talla_id = tallas_map.get(talla_nombre)
            seccion_id = secciones_map.get(seccion_nombre)
            temporada_id = temporadas_map.get(temporada_nombre)
            empresa_id = empresas_map.get(empresa_nombre)

            if not tipo_id:
                errors.append(f"Fila {i+2} (SKU {sku}): Tipo de Prenda '{tipo_nombre}' no reconocido.")
                continue
            if not talla_id:
                errors.append(f"Fila {i+2} (SKU {sku}): Talla '{talla_nombre}' no reconocida.")
                continue
            if not seccion_id:
                errors.append(f"Fila {i+2} (SKU {sku}): Sección '{seccion_nombre}' no reconocida.")
                continue
            if not temporada_id:
                errors.append(f"Fila {i+2} (SKU {sku}): Temporada '{temporada_nombre}' no reconocida.")
                continue
            if not empresa_id:
                errors.append(f"Fila {i+2} (SKU {sku}): Empresa '{empresa_nombre}' no reconocida.")
                continue

            # Verificar si el SKU ya existe
            exists = self.db.execute(
                text("SELECT 1 FROM lecturas_rfid WHERE sku = :sku LIMIT 1"),
                {"sku": sku}
            ).fetchone()
            
            if exists:
                errors.append(f"Fila {i+2}: El SKU {sku} ya existe en el inventario.")
                continue

            nueva_lectura = LecturaRFID(
                tag_epc=str(uuid.uuid4())[:20], # Generado automaticamente al importar si no viene
                sku=sku,
                tipo_id=tipo_id,
                talla_id=talla_id,
                seccion_id=seccion_id,
                temporada_id=temporada_id,
                accion="Entrada",
                resultado="Exito",
                estado_disponible=True,
                empresa_id=empresa_id
            )
            self.db.add(nueva_lectura)
            inserted_count += 1
            
            # Commit en batches para evitar saturar memoria, o todo al final
            if inserted_count % 100 == 0:
                self.db.commit()

        # Commit final
        self.db.commit()

        if errors and inserted_count == 0:
             return {"success": False, "message": "Errores en la validación", "recordsImported": 0, "errors": errors}
        elif errors:
             return {"success": True, "message": "Importación parcial completada con algunos errores", "recordsImported": inserted_count, "errors": errors}
        else:
             return {"success": True, "message": "Importación masiva completada exitosamente", "recordsImported": inserted_count}
