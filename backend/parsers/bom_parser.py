"""
Allegro OrCAD BOM text file parser.

Produces:
  valuemap: {ref_des: component_value_string}
  e.g. {"C821": "2.2uF", "U93": "TDM24544"}
"""
from __future__ import annotations


def parse_bom(content: str) -> dict[str, str]:
    valuemap: dict[str, str] = {}
    lines = content.splitlines()

    # Find the header line containing column labels
    header_idx = None
    for i, line in enumerate(lines):
        if "Item" in line and "Reference" in line and "Part" in line:
            header_idx = i
            break

    if header_idx is None:
        return valuemap

    # Skip separator line (underscores) and blank lines
    data_lines = lines[header_idx + 1:]

    current_refs: list[str] = []
    current_value: str | None = None

    def commit():
        if current_refs and current_value is not None:
            for ref in current_refs:
                ref = ref.strip()
                if ref:
                    valuemap[ref] = current_value

    for line in data_lines:
        if not line.strip():
            continue
        if set(line.strip()) == {"_"}:
            continue

        # New item: line starts with a digit
        if line and line[0].isdigit():
            commit()
            current_refs = []
            current_value = None

            parts = line.split("\t")
            if len(parts) >= 4:
                refs_str = parts[2].strip()
                current_value = parts[3].strip()
                current_refs = [r.strip() for r in refs_str.split(",") if r.strip()]
            elif len(parts) == 3:
                # Some BOM exports have 3 columns: item, qty, refs+part combined
                refs_str = parts[2].strip()
                current_refs = [r.strip() for r in refs_str.split(",") if r.strip()]

        # Continuation line: starts with whitespace
        elif line and line[0] in ("\t", " "):
            stripped = line.strip()
            if stripped:
                more = [r.strip() for r in stripped.split(",") if r.strip()]
                current_refs.extend(more)

    commit()
    return valuemap
