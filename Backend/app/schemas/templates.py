from pydantic import BaseModel
from typing import List

class ImportColumn(BaseModel):
    name: str          # Nombre que verá el usuario en el Excel
    field: str         # Campo equivalente en el procesamiento (Ej: "cantidad")
    required: bool = True

class ImportTemplate(BaseModel):
    id: str
    name: str
    description: str
    columns: List[ImportColumn]

# Templates de importación del dominio EPP. En memoria (podría migrarse a BD).
DEFAULT_TEMPLATES = [
    ImportTemplate(
        id="productos_epp",
        name="Catálogo de Productos EPP",
        description="Alta masiva de productos EPP (crea categorías faltantes)",
        columns=[
            ImportColumn(name="Nombre", field="nombre", required=True),
            ImportColumn(name="Categoría", field="categoria", required=True),
            ImportColumn(name="Aplica Talla", field="talla_aplica", required=True),  # SI / NO
            ImportColumn(name="Certificación", field="certificacion", required=False),
        ],
    ),
    ImportTemplate(
        id="stock_inicial",
        name="Stock Inicial",
        description="Poblar el stock por primera vez (ingreso de existencias)",
        columns=[
            ImportColumn(name="Recinto", field="recinto", required=True),
            ImportColumn(name="Producto", field="producto", required=True),
            ImportColumn(name="Talla", field="talla", required=False),
            ImportColumn(name="Cantidad", field="cantidad", required=True),
            ImportColumn(name="Stock Mínimo", field="stock_minimo", required=False),
        ],
    ),
    ImportTemplate(
        id="ingreso_stock",
        name="Ingreso de Stock",
        description="Reposiciones periódicas / órdenes de compra",
        columns=[
            ImportColumn(name="Recinto", field="recinto", required=True),
            ImportColumn(name="Producto", field="producto", required=True),
            ImportColumn(name="Talla", field="talla", required=False),
            ImportColumn(name="Cantidad", field="cantidad", required=True),
            ImportColumn(name="Proveedor", field="proveedor", required=False),
            ImportColumn(name="Observación", field="observacion", required=False),
        ],
    ),
    ImportTemplate(
        id="entregas_historicas",
        name="Entregas Históricas",
        description="Migrar historial de entregas del software antiguo (no afecta stock actual)",
        columns=[
            ImportColumn(name="Recinto", field="recinto", required=True),
            ImportColumn(name="RUT", field="rut", required=True),
            ImportColumn(name="Producto", field="producto", required=True),
            ImportColumn(name="Talla", field="talla", required=False),
            ImportColumn(name="Cantidad", field="cantidad", required=False),
            ImportColumn(name="Fecha", field="fecha", required=True),
            ImportColumn(name="Motivo", field="motivo", required=True),   # NUEVA | PERDIDA | DANO
        ],
    ),
]
