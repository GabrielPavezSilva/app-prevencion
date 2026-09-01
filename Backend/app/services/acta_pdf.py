"""
Generación del PDF del acta de entrega de EPP.

Infraestructura sin dominio, igual que `excel_builder`: recibe datos ya
resueltos y devuelve bytes. No toca la base.
"""
import io
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

from fpdf import FPDF

TZ_CHILE = ZoneInfo("America/Santiago")

MOTIVO_LABEL = {"NUEVA": "Nueva", "PERDIDA": "Reposición por pérdida", "DANO": "Sustitución por daño"}


def firma_desde_data_url(data_url: str) -> bytes:
    """
    Decodifica el PNG de la firma que manda el canvas del navegador
    (`canvas.toDataURL()` -> "data:image/png;base64,...").

    Valida el prefijo antes de decodificar: es entrada de cliente y el bloque
    va derecho a un PDF y a la base.
    """
    if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
        raise ValueError("La firma debe ser un PNG en formato data URL")
    try:
        png = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except Exception:
        raise ValueError("La firma no es base64 válido")
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("La firma no es un PNG válido")
    if len(png) > 2_000_000:
        raise ValueError("La firma excede el tamaño máximo (2 MB)")
    return png


def construir_acta(trabajador: Dict[str, Any], lineas: List[Dict[str, Any]],
                   firma_png: bytes, fecha: Optional[datetime] = None) -> bytes:
    """
    Acta de una página: identificación, detalle de EPP y firma del trabajador.

    `lineas` son dicts con nombre_producto, nombre_talla, cantidad y motivo.
    """
    fecha = (fecha or datetime.now(TZ_CHILE)).astimezone(TZ_CHILE)

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "Acta de entrega de EPP", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    def dato(etiqueta: str, valor: Any) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(32, 6, f"{etiqueta}:")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, str(valor or "—"), new_x="LMARGIN", new_y="NEXT")

    dato("Empresa", trabajador.get("empresa"))
    dato("Trabajador", trabajador.get("nombre_completo"))
    dato("RUT", trabajador.get("rut"))
    if trabajador.get("cargo"):
        dato("Cargo", trabajador["cargo"])
    dato("Fecha", fecha.strftime("%d-%m-%Y"))
    dato("Hora", fecha.strftime("%H:%M"))
    pdf.ln(4)

    anchos = (100, 20, 50)
    pdf.set_font("Helvetica", "B", 10)
    for ancho, titulo in zip(anchos, ("Elemento de protección personal", "Cant.", "Tipo de entrega")):
        pdf.cell(ancho, 7, titulo, border="B")
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 10)
    for linea in lineas:
        nombre = " · ".join(filter(None, [linea.get("nombre_producto"), linea.get("nombre_talla")]))
        pdf.cell(anchos[0], 7, nombre, border="B")
        pdf.cell(anchos[1], 7, str(linea.get("cantidad", "")), border="B")
        pdf.cell(anchos[2], 7, MOTIVO_LABEL.get(linea.get("motivo"), linea.get("motivo", "")), border="B")
        pdf.ln(7)

    pdf.ln(10)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, "El trabajador declara haber recibido conforme los elementos de "
                         "protección personal detallados, y haber sido instruido sobre su uso "
                         "y conservación.")
    pdf.ln(6)

    # La firma se dibuja con ancho fijo; fpdf conserva la proporción.
    pdf.image(io.BytesIO(firma_png), w=70)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(70, 6, "Firma del trabajador", border="T", align="C")

    return bytes(pdf.output())


if __name__ == "__main__":
    # ponytail: autochequeo mínimo — el PDF sale y la validación de firma corta
    # lo que no es un PNG. Correr con: python -m app.services.acta_pdf
    png_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    assert firma_desde_data_url("data:image/png;base64," + base64.b64encode(png_1x1).decode()) == png_1x1
    for malo in ("", "hola", "data:image/jpeg;base64,AAAA", "data:image/png;base64,@@@@"):
        try:
            firma_desde_data_url(malo)
            raise AssertionError(f"debió rechazar: {malo!r}")
        except ValueError:
            pass
    pdf = construir_acta(
        {"empresa": "ACME", "nombre_completo": "Ana Pérez", "rut": "11.111.111-1", "cargo": "Operaria"},
        [{"nombre_producto": "Casco", "nombre_talla": None, "cantidad": 1, "motivo": "NUEVA"},
         {"nombre_producto": "Guantes", "nombre_talla": "M", "cantidad": 2, "motivo": "PERDIDA"}],
        png_1x1,
    )
    assert pdf.startswith(b"%PDF-") and len(pdf) > 800, len(pdf)
    print("OK acta_pdf")
