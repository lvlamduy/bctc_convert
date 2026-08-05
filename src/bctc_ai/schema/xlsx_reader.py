from __future__ import annotations

import posixpath
import re
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS, "p": PKG_REL_NS}


class WorkbookReadError(ValueError):
    pass


def _column(reference: str) -> str:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        raise WorkbookReadError(f"invalid cell reference: {reference}")
    return match.group(1)


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall("m:si", NS)
    ]


def _sheet_targets(archive: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
    result: list[tuple[str, str]] = []
    sheets = workbook.find("m:sheets", NS)
    if sheets is None:
        return result
    for sheet in sheets:
        relation_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = targets[relation_id].lstrip("/")
        if not target.startswith("xl/"):
            target = posixpath.normpath(posixpath.join("xl", target))
        result.append((sheet.attrib["name"], target))
    return result


def read_rows(path: Path, sheet_index: int = 0) -> Iterator[dict[str, str]]:
    try:
        with ZipFile(path) as archive:
            shared = _shared_strings(archive)
            sheets = _sheet_targets(archive)
            if sheet_index >= len(sheets):
                raise WorkbookReadError(f"sheet index {sheet_index} missing in {path}")
            _, target = sheets[sheet_index]
            root = ET.fromstring(archive.read(target))
            for row in root.findall(".//m:sheetData/m:row", NS):
                values: dict[str, str] = {}
                for cell in row.findall("m:c", NS):
                    reference = cell.attrib.get("r", "")
                    cell_type = cell.attrib.get("t")
                    value_node = cell.find("m:v", NS)
                    if cell_type == "inlineStr":
                        inline = cell.find("m:is", NS)
                        value = (
                            ""
                            if inline is None
                            else "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))
                        )
                    elif value_node is None:
                        value = ""
                    elif cell_type == "s":
                        try:
                            value = shared[int(value_node.text or "")]
                        except (IndexError, ValueError) as exc:
                            raise WorkbookReadError(
                                f"bad shared string in {path}: {reference}"
                            ) from exc
                    else:
                        value = value_node.text or ""
                    values[_column(reference)] = value
                if values:
                    yield values
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise WorkbookReadError(f"cannot read workbook {path}: {exc}") from exc
