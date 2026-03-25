"""
PADS2000 netlist (.asc) parser.

Produces three data structures:
  partmap: {ref_des: footprint}
  netmap:  {net_name: [{"ref": str, "pin": str}, ...]}
  pinmap:  {ref_des: {pin_str: net_name}}
"""
from __future__ import annotations


def parse_asc(content: str) -> tuple[dict, dict, dict]:
    partmap: dict[str, str] = {}
    netmap: dict[str, list[dict]] = {}
    pinmap: dict[str, dict[str, str]] = {}

    section = None
    current_net = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("*PADS2000*"):
            continue
        if line == "*PART*":
            section = "PART"
            continue
        if line == "*NET*":
            section = "NET"
            continue
        if line == "*END*":
            break

        if section == "PART":
            parts = line.split()
            if len(parts) >= 2:
                ref, footprint = parts[0], parts[1]
                partmap[ref] = footprint
            elif len(parts) == 1:
                partmap[parts[0]] = ""

        elif section == "NET":
            if line.startswith("*SIGNAL*"):
                current_net = line[len("*SIGNAL*"):].strip()
                if current_net not in netmap:
                    netmap[current_net] = []
            elif current_net is not None and not line.startswith("*"):
                tokens = line.split()
                for token in tokens:
                    if "." in token:
                        ref, pin = token.split(".", 1)
                        netmap[current_net].append({"ref": ref, "pin": pin})
                        if ref not in pinmap:
                            pinmap[ref] = {}
                        pinmap[ref][pin] = current_net

    return partmap, netmap, pinmap
