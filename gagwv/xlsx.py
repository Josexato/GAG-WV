"""Exportar el .sdjf/.gag a Excel: una hoja por sección.

Generador XLSX mínimo en stdlib pura (un .xlsx es un ZIP de XMLs con
strings inline) — sin openpyxl ni dependencias nuevas. Hojas: Elements,
Connections, Areas y Journeys; las columnas conocidas van primero y
cualquier campo extra queda como JSON en la columna `otros`.
"""

import io
import json
import zipfile
from xml.sax.saxutils import escape

# (hoja, clave raíz, columnas conocidas) — siempre presentes
SECCIONES = [
    ('Elements', 'elements',
     ['id', 'label', 'type', 'color', 'contains']),
    ('Connections', 'connections',
     ['from', 'to', 'label', 'direction', 'semantic_type', 'style']),
    ('Areas', 'areas',
     ['id', 'label', 'color', 'members']),
    ('Journeys', 'journeys',
     ['id', 'label', 'color', 'path']),
]

# Secciones opcionales del formato (v3.20): la hoja sólo se crea si la
# clave existe en el archivo. `roles` es un dict {id: {label, color}}.
SECCIONES_OPCIONALES = [
    ('Lanes', 'lanes', ['id', 'label', 'members']),
    ('Unions', 'unions', ['id', 'between']),
]


def _celda_texto(valor, clave):
    """Valor de una celda: listas legibles, dicts/extras como JSON."""
    if valor is None:
        return ''
    if isinstance(valor, list):
        if clave == 'path':
            return ' → '.join(str(v) for v in valor)
        partes = []
        for v in valor:
            if isinstance(v, dict):
                base = str(v.get('id', json.dumps(v, ensure_ascii=False)))
                if 'scope' in v:
                    base += f" ({v['scope']})"
                partes.append(base)
            else:
                partes.append(str(v))
        return ', '.join(partes)
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def _filas_de_seccion(items, columnas):
    """Encabezado + una fila por item; campos no contemplados → `otros`."""
    filas = [columnas + ['otros']]
    for item in items or []:
        if not isinstance(item, dict):
            filas.append([_celda_texto(item, '')] + [''] * len(columnas))
            continue
        fila = [_celda_texto(item.get(c), c) for c in columnas]
        extras = {k: v for k, v in item.items() if k not in columnas}
        fila.append(json.dumps(extras, ensure_ascii=False) if extras else '')
        filas.append(fila)
    return filas


def _xml_hoja(filas):
    cuerpo = []
    for i, fila in enumerate(filas, 1):
        celdas = []
        for j, valor in enumerate(fila):
            col = ''
            n = j
            while True:
                col = chr(65 + n % 26) + col
                n = n // 26 - 1
                if n < 0:
                    break
            estilo = ' s="1"' if i == 1 else ''
            celdas.append(
                f'<c r="{col}{i}" t="inlineStr"{estilo}>'
                f'<is><t xml:space="preserve">{escape(str(valor))}</t></is></c>')
        cuerpo.append(f'<row r="{i}">{"".join(celdas)}</row>')
    n_cols = max((len(f) for f in filas), default=1)
    cols = (f'<cols><col min="1" max="{n_cols}" width="24" '
            f'customWidth="1"/></cols>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main">'
            f'{cols}<sheetData>{"".join(cuerpo)}</sheetData></worksheet>')


_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
    '<cellXfs count="2"><xf/><xf fontId="1" applyFont="1"/></cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/>'
    '</cellStyles></styleSheet>')


def _filas_roles(mapa):
    """`roles` es un dict {id: {label, color}} (§I30), no una lista."""
    filas = [['id', 'label', 'color', 'otros']]
    for clave, v in (mapa or {}).items():
        if isinstance(v, dict):
            extras = {k: x for k, x in v.items()
                      if k not in ('label', 'color')}
            filas.append([clave,
                          _celda_texto(v.get('label'), 'label'),
                          _celda_texto(v.get('color'), 'color'),
                          json.dumps(extras, ensure_ascii=False)
                          if extras else ''])
        else:
            filas.append([clave, _celda_texto(v, ''), '', ''])
    return filas


def libro_desde_sdjf(data):
    """bytes de un .xlsx: hojas Elements/Connections/Areas/Journeys fijas,
    más Lanes/Unions/Roles cuando el archivo declara esas secciones."""
    hojas = [(nombre, _filas_de_seccion(data.get(clave), columnas))
             for nombre, clave, columnas in SECCIONES]
    for nombre, clave, columnas in SECCIONES_OPCIONALES:
        if clave in data:
            hojas.append((nombre, _filas_de_seccion(data.get(clave), columnas)))
    if isinstance(data.get('roles'), dict):
        hojas.append(('Roles', _filas_roles(data['roles'])))

    sheets_xml = ''.join(
        f'<sheet name="{escape(nombre)}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (nombre, _) in enumerate(hojas, 1))
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{sheets_xml}</sheets></workbook>')

    n = len(hojas)
    rels_wb = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + ''.join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, n + 1))
        + f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/'
          f'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>')

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
        'package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + ''.join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.'
            f'spreadsheetml.worksheet+xml"/>'
            for i in range(1, n + 1))
        + '</Types>')

    rels_raiz = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels_raiz)
        z.writestr('xl/workbook.xml', workbook)
        z.writestr('xl/_rels/workbook.xml.rels', rels_wb)
        z.writestr('xl/styles.xml', _STYLES)
        for i, (_, filas) in enumerate(hojas, 1):
            z.writestr(f'xl/worksheets/sheet{i}.xml', _xml_hoja(filas))
    return buf.getvalue()
