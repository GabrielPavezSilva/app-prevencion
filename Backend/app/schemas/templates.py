from pydantic import BaseModel
from typing import List, Optional

class ImportColumn(BaseModel):
    name: str # Nombre que verá el usuario en el Excel
    field: str # Campo equivalente en la base de datos (Ej: "sku")
    required: bool = True

class ImportTemplate(BaseModel):
    id: str
    name: str
    description: str
    columns: List[ImportColumn]

# Como mock inicial para la persistencia, usaremos diccionarios en memoria.
# Posteriormente puede migrarse a Base de Datos.
DEFAULT_TEMPLATES = [
    ImportTemplate(
        id="inventario_inicial",
        name="Inventario Inicial",
        description="Carga masiva para popular el inventario inicial",
        columns=[
            ImportColumn(name="SKU", field="sku", required=True),
            ImportColumn(name="Tipo de Prenda", field="tipo_prenda", required=True),
            ImportColumn(name="Talla", field="talla", required=True),
            ImportColumn(name="Empresa", field="empresa", required=True)
        ]
    ),
    ImportTemplate(
        id="orden_compra",
        name="Orden de Compra",
        description="Ingreso de nuevo stock mediante Ordenes de Compra",
        columns=[
            ImportColumn(name="SKU", field="sku", required=True),
            ImportColumn(name="Cantidad", field="cantidad", required=True),
            ImportColumn(name="Proveedor", field="proveedor", required=False),
            ImportColumn(name="Fecha Esperada", field="fecha_esperada", required=False)
        ]
    )
]
