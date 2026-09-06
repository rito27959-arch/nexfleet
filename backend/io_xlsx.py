# -*- coding: utf-8 -*-
"""Lecture et écriture de fichiers Excel .xlsx avec uniquement la bibliothèque standard.
L'import d'un .xlsx repose sur zipfile + xml (pas de dépendance openpyxl/pandas)."""

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

COL_RE = re.compile(r"^[A-Z]+")


def _col_index(ref):
    letters = COL_RE.match(ref)
    if not letters:
        return 0
    n = 0
    for ch in letters.group():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _cell_text(c, shared):
    t = c.get("t")
    v = c.find(f"{NS}v")
    if t == "s" and v is not None:
        try:
            i = int(v.text or 0)
            return shared[i] if 0 <= i < len(shared) else ""
        except (ValueError, IndexError):
            return ""
    if t == "inlineStr":
        is_ = c.find(f"{NS}is")
        if is_ is not None:
            return "".join(x.text or "" for x in is_.iter(f"{NS}t"))
    if v is not None:
        return (v.text or "").strip()
    return ""


def read_xlsx(data):
    """Retourne une liste de listes (feuille active / première feuille)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Fichier .xlsx invalide (archive corrompue).")

    shared = _read_shared(zf)
    sheets = sorted(n for n in zf.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    if not sheets:
        raise ValueError("Aucune feuille de calcul trouvée dans le fichier.")
    return _read_sheet(zf, sheets[0], shared)


def read_xlsx_sheets(data):
    """Retourne {nom_feuille: liste de lignes} en respectant l'ordre du classeur."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Fichier .xlsx invalide (archive corrompue).")

    shared = _read_shared(zf)

    order = []
    try:
        root = ET.fromstring(zf.read("xl/workbook.xml"))
        for sh in root.iter(f"{NS}sheet"):
            rid = sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            order.append((sh.get("name") or "Feuille", rid))
    except (KeyError, ET.ParseError):
        pass

    target = {}
    try:
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        for rel in rels.iter("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
            target[rel.get("Id")] = rel.get("Target")
    except (KeyError, ET.ParseError):
        pass

    out = {}
    if order:
        for name, rid in order:
            tgt = target.get(rid) or ""
            tgt = tgt.replace("\\", "/")
            if tgt and not tgt.startswith("xl/"):
                tgt = "xl/" + tgt.lstrip("/")
            if tgt in zf.namelist():
                out[name] = _read_sheet(zf, tgt, shared)
    if not out:
        sheets = sorted(n for n in zf.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        for i, s in enumerate(sheets):
            out[f"Feuille {i + 1}"] = _read_sheet(zf, s, shared)
    return out


def _read_shared(zf):
    shared = []
    if "xl/sharedStrings.xml" in zf.namelist():
        try:
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{NS}t"))
                      for si in root.findall(f"{NS}si")]
        except ET.ParseError:
            shared = []
    return shared


def _read_sheet(zf, sheet_path, shared):
    try:
        root = ET.fromstring(zf.read(sheet_path))
    except ET.ParseError:
        return []
    sheetdata = root.find(f".//{NS}sheetData")
    if sheetdata is None:
        return []
    rows = []
    for row in sheetdata.findall(f"{NS}row"):
        cells = {}
        for c in row.findall(f"{NS}c"):
            ref = c.get("r")
            idx = _col_index(ref) if ref else len(cells)
            cells[idx] = _cell_text(c, shared)
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
    return rows


# ------------------------------------------------------------------ écriture xlsx
_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheets}
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<workbookPr/>
<bookViews><workbookView activeTab="0"/></bookViews>
<sheets>{sheets}</sheets>
</workbook>"""

_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><name val="Calibri"/><sz val="11"/></font><font><name val="Calibri"/><b/><sz val="11"/><color rgb="FFFFFFFF"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF6366F1"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>
</styleSheet>"""


def _ref(col, row):
    s = ""
    c = col
    while c:
        c, rem = divmod(c - 1, 26)
        s = chr(65 + rem) + s
    return f"{s}{row}"


def _escape_xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def _cell_xml(value, col, row, header=False):
    ref = _ref(col, row)
    style = ' s="1"' if header else ""
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"{style}><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"{style}><v>{value}</v></c>'
    text = str(value) if value is not None else ""
    text = _escape_xml(text)
    return f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet_xml(rows):
    body = []
    for ri, row in enumerate(rows, 1):
        cells = "".join(_cell_xml(v, ci + 1, ri, header=(ri == 1)) for ci, v in enumerate(row))
        body.append(f'<row r="{ri}">{cells}</row>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="{NS[1:-1]}"><sheetData>{"".join(body)}</sheetData></worksheet>')


def write_xlsx(sheets):
    """sheets : dict nom_de_feuille -> liste de lignes (listes de valeurs)."""
    sheets = {k: v for k, v in sheets.items() if v}
    if not sheets:
        raise ValueError("Aucune donnée à exporter.")
    names = list(sheets)
    sheet_elems = "".join(
        f'<sheet name="{_escape_xml(names[i])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
        for i in range(len(names))
    )
    rels = "".join(
        f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
        for i in range(len(names))
    )
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(len(names))
    )
    content_types = _CONTENT_TYPES.format(sheets=sheet_overrides)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK.format(sheets=sheet_elems))
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS.format(rels=rels))
        zf.writestr("xl/styles.xml", _STYLES)
        for i, name in enumerate(names, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(sheets[name]))
    return buf.getvalue()


# ------------------------------------------------------------------ CSV
def write_csv(rows, filename=None):
    """CSV UTF-8 avec BOM pour une ouverture correcte dans Excel."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerows(rows)
    data = "\ufeff" + buf.getvalue()
    if filename:
        return io.BytesIO(data.encode("utf-8"))
    return data.encode("utf-8")
