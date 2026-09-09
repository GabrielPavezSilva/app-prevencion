"""
Generación del PDF del acta de entrega de EPP.

Infraestructura sin dominio, igual que `excel_builder`: recibe datos ya
resueltos y devuelve bytes. No toca la base.

Dos documentos, un mismo formato de tabla:
  - `construir_acta`: el acta del carrito que se firma en el momento.
  - `construir_acta_maestra`: el documento maestro del trabajador, con todas
    sus entregas firmadas históricas. No se guarda: se regenera desde la base
    cada vez que se pide, así nunca hay un archivo que se quede atrás.
"""
import io
import base64
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

from fpdf import FPDF

TZ_CHILE = ZoneInfo("America/Santiago")

MOTIVO_LABEL = {"NUEVA": "Nueva", "PERDIDA": "Reposición por pérdida", "DANO": "Sustitución por daño"}

# Descripción, Tipo, Talla, Entrega, Recambio, Cant., Firma (mm; 190 útiles en A4)
# El `padding=1.5` de la tabla come 3 mm por celda: el ancho útil de cada
# columna es el valor de acá menos 3, y ahí tiene que caber la palabra más
# larga del título o fpdf2 la corta. "Cantidad" mide 11,3 mm en Helvetica 8 y
# con 14 se cortaba en "Cantida"; los 2 mm salen de "Descripción EPP", que
# sobra de ancho. El autochequeo de abajo verifica que sigan entrando todos.
COL_ANCHOS = (44, 32, 14, 23, 27, 16, 34)
COL_TITULOS = ("Descripción EPP", "Tipo de EPP", "Talla", "Fecha de entrega",
               "Fecha probable de recambio", "Cantidad", "Firma")


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


def _fecha_recambio(entrega: Any, meses: Optional[int]) -> str:
    """
    Fecha probable de recambio = fecha de entrega + la vida útil del producto.

    Sin vida útil definida en el catálogo no se inventa nada: la celda queda en
    blanco antes que mostrar una fecha que nadie fijó.
    """
    if not meses or not isinstance(entrega, (datetime, date)):
        return "-"
    base = entrega.date() if isinstance(entrega, datetime) else entrega
    # timedelta no sabe de meses; 30 días es la aproximación de siempre en el
    # rubro y basta para una fecha "probable".
    return (base + timedelta(days=30 * int(meses))).strftime("%d-%m-%Y")


def _fmt_fecha(valor: Any) -> str:
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d-%m-%Y")
    return "-"


def _ajustar(pdf: FPDF, ancho: float, texto: str) -> str:
    """
    Recorta `texto` para que quepa en `ancho` mm con la fuente activa.

    `pdf.cell` no recorta lo que no cabe: lo dibuja igual, encima de la celda
    siguiente, y el encabezado queda ilegible. Un nombre completo o un cargo
    largo alcanzan para eso.

    Los "..." van con puntos sueltos a propósito: las fuentes core de fpdf2
    codifican en latin-1 y el carácter de elipsis no existe ahí.
    """
    limite = ancho - 1  # deja aire para que el texto no bese el borde
    if pdf.get_string_width(texto) <= limite:
        return texto
    while texto and pdf.get_string_width(texto + "...") > limite:
        texto = texto[:-1]
    return texto.rstrip() + "..."


def _encabezado(pdf: FPDF, trabajador: Dict[str, Any], titulo: str, fecha: datetime) -> None:
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Antecedentes Generales", new_x="LMARGIN", new_y="NEXT")

    # Anchos de las cuatro celdas de cada par; suman los 190 mm útiles del A4.
    # El label izquierdo es el más ancho porque "Persona Trabajadora:" es la
    # etiqueta más larga del bloque.
    def par(et_izq: str, val_izq: Any, et_der: str, val_der: Any) -> None:
        for ancho_et, ancho_val, etiqueta, valor in (
            (42, 53, et_izq, val_izq), (22, 73, et_der, val_der),
        ):
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(ancho_et, 6, _ajustar(pdf, ancho_et, f"{etiqueta}:"))
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(ancho_val, 6, _ajustar(pdf, ancho_val, str(valor or "-")))
        pdf.ln(6)

    par("Persona Trabajadora", trabajador.get("nombre_completo"), "Rut", trabajador.get("rut"))
    par("Cargo", trabajador.get("cargo"), "Área", trabajador.get("nombre_area"))
    par("Empresa", trabajador.get("empresa"), "Emitido", fecha.strftime("%d-%m-%Y %H:%M"))
    pdf.ln(4)


def _tabla(pdf: FPDF, filas: List[Dict[str, Any]]) -> None:
    """
    Tabla por filas y celdas: la última columna lleva el PNG de la firma
    ajustado al ancho de su celda (`img_fill_width`), que es lo que permite
    que cada registro conserve la firma con la que se recibió.

    Cada fila es un dict con: nombre_producto, nombre_categoria, nombre_talla,
    fecha_entrega, vida_util_meses, cantidad, firma (bytes o None).
    """
    pdf.set_font("Helvetica", "", 8)
    with pdf.table(col_widths=COL_ANCHOS, line_height=5, first_row_as_headings=True,
                   text_align=("LEFT", "LEFT", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER"),
                   padding=1.5) as tabla:
        encabezado = tabla.row()
        for titulo in COL_TITULOS:
            encabezado.cell(titulo)
        for f in filas:
            fila = tabla.row()
            fila.cell(f.get("nombre_producto") or "-")
            fila.cell(f.get("nombre_categoria") or "-")
            fila.cell(f.get("nombre_talla") or "-")
            fila.cell(_fmt_fecha(f.get("fecha_entrega")))
            fila.cell(_fecha_recambio(f.get("fecha_entrega"), f.get("vida_util_meses")))
            fila.cell(str(f.get("cantidad", "")))
            firma = f.get("firma")
            if firma:
                fila.cell(img=io.BytesIO(firma), img_fill_width=True)
            else:
                fila.cell("-")


def _pie(pdf: FPDF) -> None:
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, "La persona trabajadora declara haber recibido conforme los elementos "
                         "de protección personal detallados, y haber sido instruida sobre su uso "
                         "y conservación. La firma de cada fila corresponde a la recepción de ese "
                         "elemento.")


def construir_acta(trabajador: Dict[str, Any], lineas: List[Dict[str, Any]],
                   firma_png: bytes, fecha: Optional[datetime] = None) -> bytes:
    """
    Acta del carrito que se acaba de firmar. Todas sus filas llevan la misma
    firma, que es la que el trabajador acaba de trazar.
    """
    fecha = (fecha or datetime.now(TZ_CHILE)).astimezone(TZ_CHILE)
    filas = [{**linea, "firma": firma_png, "fecha_entrega": linea.get("fecha_entrega") or fecha}
             for linea in lineas]

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _encabezado(pdf, trabajador, "Acta de entrega de EPP", fecha)
    _tabla(pdf, filas)
    _pie(pdf)
    return bytes(pdf.output())


def construir_acta_maestra(trabajador: Dict[str, Any], filas: List[Dict[str, Any]],
                           fecha: Optional[datetime] = None) -> bytes:
    """
    Documento maestro del trabajador: una fila por entrega firmada, en orden
    cronológico, cada una con su propia firma.
    """
    fecha = (fecha or datetime.now(TZ_CHILE)).astimezone(TZ_CHILE)

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _encabezado(pdf, trabajador, "Registro de entrega de EPP", fecha)
    if filas:
        _tabla(pdf, filas)
        _pie(pdf)
    else:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, "Sin entregas firmadas registradas.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


if __name__ == "__main__":
    # ponytail: autochequeo mínimo — los dos PDF salen, la tabla acepta firma
    # por fila y la validación corta lo que no es un PNG.
    # Correr con: python -m app.services.acta_pdf
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

    assert _fecha_recambio(datetime(2026, 1, 1), None) == "-"
    assert _fecha_recambio(datetime(2026, 1, 1), 6) == "30-06-2026"

    # El encabezado no se sobrepone: lo que no cabe en su celda se recorta.
    medidor = FPDF(format="A4", unit="mm")
    medidor.add_page()
    medidor.set_font("Helvetica", "B", 10)
    largo = "Bernardino Esteban de la Santisima Concepcion Valenzuela Iturriaga"
    assert medidor.get_string_width(largo) > 53, "el caso de prueba ya cabia"
    recortado = _ajustar(medidor, 53, largo)
    assert recortado.endswith("...") and medidor.get_string_width(recortado) <= 52
    # Lo que ya cabe se deja intacto, sin puntos de más.
    assert _ajustar(medidor, 53, "Ana Perez") == "Ana Perez"
    # Y la etiqueta más larga del bloque entra en su ancho sin recorte.
    medidor.set_font("Helvetica", "", 10)
    assert _ajustar(medidor, 42, "Persona Trabajadora:") == "Persona Trabajadora:"

    # Los títulos de la tabla entran en su columna: fpdf2 parte por palabras,
    # así que lo que no puede caber es la palabra más larga de cada título.
    assert sum(COL_ANCHOS) == 190, "la tabla se sale del A4"
    medidor.set_font("Helvetica", "", 8)
    for titulo, ancho in zip(COL_TITULOS, COL_ANCHOS):
        peor = max(medidor.get_string_width(p) for p in titulo.split())
        assert peor <= ancho - 3, f"'{titulo}' no cabe en {ancho}mm (necesita {peor:.1f})"

    trab = {"empresa": "ACME", "nombre_completo": "Ana Pérez", "rut": "11.111.111-1",
            "cargo": "Operaria", "nombre_area": "Producción"}
    pdf = construir_acta(
        trab,
        [{"nombre_producto": "Casco", "nombre_categoria": "Protección cabeza", "nombre_talla": None,
          "cantidad": 1, "motivo": "NUEVA", "vida_util_meses": 24},
         {"nombre_producto": "Guantes", "nombre_categoria": "Protección manos", "nombre_talla": "M",
          "cantidad": 2, "motivo": "PERDIDA", "vida_util_meses": None}],
        png_1x1,
    )
    assert pdf.startswith(b"%PDF-") and len(pdf) > 800, len(pdf)

    maestro = construir_acta_maestra(trab, [
        {"nombre_producto": "Casco", "nombre_categoria": "Protección cabeza", "nombre_talla": None,
         "cantidad": 1, "fecha_entrega": datetime(2026, 1, 5), "vida_util_meses": 24, "firma": png_1x1},
        {"nombre_producto": "Guantes", "nombre_categoria": "Protección manos", "nombre_talla": "M",
         "cantidad": 2, "fecha_entrega": datetime(2026, 3, 2), "vida_util_meses": 6, "firma": None},
    ])
    assert maestro.startswith(b"%PDF-") and len(maestro) > 800, len(maestro)
    assert construir_acta_maestra(trab, []).startswith(b"%PDF-")
    print("OK acta_pdf")
