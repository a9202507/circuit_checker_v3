"""
Rule checker logic for circuit compliance checking.
"""
from __future__ import annotations
import re
from .rule_loader import (
    ComponentRuleSet,
    PinCountRule,
    PinToGndCapRule,
    PinToPinCapRule,
    PinToPinConnectionRule,
    PinFloatingRule,
    PinToNetResistorRule,
    PinToNetCapacitorRule,
    PinToNetInductorRule,
    FbVoutDividerRule,
    PmbusVoutCheckRule,
    PmbusLinear11CheckRule,
    RegisterValueRule,
)


# ── Value normalization ────────────────────────────────────────────────────────

def normalize_capacitance(value_str: str) -> float | None:
    """Convert capacitance string (e.g. '2.2uF', '220pF') to farads."""
    units = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "f": 1.0}
    s = value_str.strip().lower().replace(" ", "")
    m = re.match(r"^([0-9.]+)\s*([pnumf]?)f$", s)
    if not m:
        return None
    number = float(m.group(1))
    unit = m.group(2) if m.group(2) else "f"
    return number * units[unit]


def normalize_resistance(value_str: str) -> float | None:
    """Convert resistance string (e.g. '10k', '4.7M', '100R', '100') to ohms."""
    s = value_str.strip().lower().replace(" ", "").replace("ω", "").replace("ohm", "")
    m = re.match(r"^([0-9.]+)\s*([kmr]?)$", s)
    if not m:
        return None
    number = float(m.group(1))
    unit = m.group(2)
    multipliers = {"k": 1e3, "m": 1e6, "r": 1.0, "": 1.0}
    return number * multipliers.get(unit, 1.0)


def normalize_voltage(value_str: str) -> float | None:
    """Convert voltage string (e.g. '1.8V', '0.6V', '3.3V') to float volts."""
    s = value_str.strip().lower().replace(" ", "")
    m = re.match(r"^([0-9.]+)\s*v?$", s)
    if not m:
        return None
    return float(m.group(1))


def normalize_inductance(value_str: str) -> float | None:
    """Convert inductance string (e.g. '100nH', '10uH', '1mH') to henries."""
    s = value_str.strip().lower().replace(" ", "")
    m = re.match(r"^([0-9.]+)\s*([pnum]?)h$", s)
    if not m:
        return None
    number = float(m.group(1))
    unit = m.group(2)
    multipliers = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "": 1.0}
    return number * multipliers.get(unit, 1.0)


def capacitance_match(val_str: str, expected_str: str) -> bool:
    a = normalize_capacitance(val_str)
    b = normalize_capacitance(expected_str)
    if a is None or b is None:
        return False
    if b == 0:
        return a == 0
    return abs(a - b) / b < 0.01


def _value_in_range(val_str: str, min_str: str | None, max_str: str | None, normalizer) -> tuple[bool, str]:
    """Check if a value falls within [min_str, max_str]. Returns (ok, reason)."""
    val = normalizer(val_str)
    if val is None:
        return False, f"Cannot parse value '{val_str}'"
    if min_str is not None:
        min_val = normalizer(min_str)
        if min_val is not None and val < min_val * 0.999:
            return False, f"{val_str} is below minimum {min_str}"
    if max_str is not None:
        max_val = normalizer(max_str)
        if max_val is not None and val > max_val * 1.001:
            return False, f"{val_str} exceeds maximum {max_str}"
    return True, ""


# ── Net equivalence (0Ω bridges) ────────────────────────────────────────────

def _build_net_equiv(partmap: dict, netmap: dict, pinmap: dict, valuemap: dict) -> dict[str, str]:
    """
    Build net equivalence map for 0Ω resistor bridges.
    Returns {net_name: canonical_net_name} using union-find.
    Supports multi-layer chains (A→B→C resolve to same canonical net).
    """
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Scan netmap for 0Ω resistors
    for net_name, entries in netmap.items():
        for entry in entries:
            ref = entry["ref"]
            pin = entry["pin"]
            if not is_resistor(ref):
                continue
            value = valuemap.get(ref, "")
            ohms = normalize_resistance(value)
            if ohms != 0.0:
                continue

            # Found a 0Ω resistor — find its other end
            pins = pinmap.get(ref, {})
            for other_pin, other_net in pins.items():
                if other_pin != pin:
                    union(net_name, other_net)

    # Build final equivalence map
    equiv = {}
    for net in netmap.keys():
        equiv[net] = find(net)
    return equiv


def _resolve(net: str, equiv: dict[str, str]) -> str:
    """Resolve net to its canonical name via equivalence map."""
    return equiv.get(net, net)


# ── Net matching ───────────────────────────────────────────────────────────────

def _nets_match(other_net: str, rule_net: str, gnd_nets: list[str], equiv: dict[str, str] | None = None) -> bool:
    """
    Compare other_net against rule_net, respecting GND aliases and 0Ω bridges.
    If rule_net is one of the gnd_nets, any net in gnd_nets is accepted.
    Comparison is case-insensitive. Nets are resolved via equivalence map first.
    """
    if equiv is None:
        equiv = {}

    other_resolved = _resolve(other_net, equiv)
    rule_resolved = _resolve(rule_net, equiv)

    gnd_lower = {n.lower() for n in gnd_nets}
    if rule_resolved.lower() in gnd_lower:
        return other_resolved.lower() in gnd_lower
    return other_resolved.lower() == rule_resolved.lower()


# ── Component type detection ───────────────────────────────────────────────────

def is_capacitor(ref: str, partmap: dict) -> bool:
    footprint = partmap.get(ref, "").lower()
    return footprint.startswith("cc")


def is_capacitor_general(ref: str, partmap: dict) -> bool:
    """Footprint-first, ref-prefix fallback."""
    if is_capacitor(ref, partmap):
        return True
    return bool(re.match(r"^C\d", ref, re.IGNORECASE))


def is_resistor(ref: str) -> bool:
    return bool(re.match(r"^R\d", ref, re.IGNORECASE))


def is_inductor(ref: str) -> bool:
    return bool(re.match(r"^(L\d|FB)", ref, re.IGNORECASE))


# ── Rule dispatch ──────────────────────────────────────────────────────────────

def check_rule(
    ref_des: str,
    rule,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    equiv: dict[str, str] | None = None,
    regpair=None,
) -> dict:
    """Check a single rule for a given IC instance. Returns a result dict."""
    if equiv is None:
        equiv = {}

    if isinstance(rule, PinCountRule):
        return _check_pin_count(ref_des, rule, pinmap)

    if isinstance(rule, PinToPinConnectionRule):
        return _check_pin_to_pin_connection(ref_des, rule, pinmap, equiv)

    if isinstance(rule, PinToGndCapRule):
        return _check_pin_to_gnd_cap(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap, equiv)

    if isinstance(rule, PinToPinCapRule):
        return _check_pin_to_pin_cap(ref_des, rule, partmap, netmap, pinmap, valuemap, equiv)

    if isinstance(rule, PinFloatingRule):
        return _check_pin_floating(ref_des, rule, netmap, pinmap)

    if isinstance(rule, PinToNetResistorRule):
        return _check_pin_to_net_passive(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap,
                                         "pin_to_net_resistor", is_resistor, normalize_resistance, equiv)

    if isinstance(rule, PinToNetCapacitorRule):
        return _check_pin_to_net_capacitor(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap, equiv)

    if isinstance(rule, PinToNetInductorRule):
        return _check_pin_to_net_passive(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap,
                                         "pin_to_net_inductor", is_inductor, normalize_inductance, equiv)

    if isinstance(rule, FbVoutDividerRule):
        return _check_fb_vout_divider(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap, equiv)

    if isinstance(rule, PmbusVoutCheckRule):
        return _check_pmbus_vout(rule, regpair)

    if isinstance(rule, PmbusLinear11CheckRule):
        return _check_pmbus_linear11(rule, regpair)

    if isinstance(rule, RegisterValueRule):
        return _check_register_value(rule, regpair)

    return {"rule_type": "unknown", "description": "", "status": "ERROR", "detail": "Unknown rule type"}


# ── Individual checkers ────────────────────────────────────────────────────────

def _check_pin_count(ref_des: str, rule: PinCountRule, pinmap: dict) -> dict:
    desc = rule.description or f"Total pin count must be one of {rule.count}"
    ic_pins = pinmap.get(ref_des, {})
    count = len(ic_pins)
    if count in rule.count:
        return {"rule_type": "pin_count", "description": desc, "status": "PASS",
                "detail": f"Found {count} pins"}
    return {"rule_type": "pin_count", "description": desc,
            "status": rule.severity.upper(),
            "detail": f"Found {count} pins, expected one of {rule.count}"}


def _check_pin_to_pin_connection(ref_des: str, rule: PinToPinConnectionRule, pinmap: dict, equiv: dict[str, str] | None = None) -> dict:
    if equiv is None:
        equiv = {}
    desc = rule.description or f"pin{rule.pin1} must connect to pin{rule.pin2}"
    ic_pins = pinmap.get(ref_des, {})
    net1 = ic_pins.get(rule.pin1)
    net2 = ic_pins.get(rule.pin2)

    if net1 is None:
        return {"rule_type": "pin_to_pin_connection", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin1} not found in netlist"}
    if net2 is None:
        return {"rule_type": "pin_to_pin_connection", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin2} not found in netlist"}

    net1_resolved = _resolve(net1, equiv)
    net2_resolved = _resolve(net2, equiv)

    if net1_resolved == net2_resolved:
        return {"rule_type": "pin_to_pin_connection", "description": desc,
                "status": "PASS", "detail": f"Both pins on equivalent net {net1_resolved}"}
    return {"rule_type": "pin_to_pin_connection", "description": desc,
            "status": rule.severity.upper(),
            "detail": f"pin{rule.pin1} on {net1}, pin{rule.pin2} on {net2}"}


def _check_pin_to_gnd_cap(
    ref_des: str,
    rule: PinToGndCapRule,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    equiv: dict[str, str] | None = None,
) -> dict:
    if equiv is None:
        equiv = {}
    desc = rule.description or f"pin{rule.pin} needs {rule.capacitance} cap to GND"
    ic_pins = pinmap.get(ref_des, {})
    target_net = ic_pins.get(rule.pin)

    if target_net is None:
        return {"rule_type": "pin_to_gnd_cap", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin} not found in netlist"}

    gnd_nets = {n.lower() for n in ruleset.gnd_nets}
    found_caps = []

    for entry in netmap.get(target_net, []):
        cap_ref = entry["ref"]
        cap_pin = entry["pin"]
        if cap_ref == ref_des:
            continue
        if not is_capacitor(cap_ref, partmap):
            continue

        cap_ic_pins = pinmap.get(cap_ref, {})
        other_pins = [p for p in cap_ic_pins if p != cap_pin]
        for other_pin in other_pins:
            other_net = cap_ic_pins[other_pin]
            if _nets_match(other_net, "GND", ruleset.gnd_nets, equiv):
                cap_value = valuemap.get(cap_ref, "")
                if capacitance_match(cap_value, rule.capacitance):
                    return {"rule_type": "pin_to_gnd_cap", "description": desc,
                            "status": "PASS",
                            "detail": f"{cap_ref} ({cap_value}) on {target_net}, other pin on {other_net}"}
                found_caps.append(f"{cap_ref}={cap_value}")

    if found_caps:
        return {"rule_type": "pin_to_gnd_cap", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Caps to GND found but wrong value: {', '.join(found_caps)}; expected {rule.capacitance}"}
    return {"rule_type": "pin_to_gnd_cap", "description": desc,
            "status": rule.severity.upper(),
            "detail": f"No {rule.capacitance} cap to GND found on pin{rule.pin} (net: {target_net})"}


def _check_pin_to_pin_cap(
    ref_des: str,
    rule: PinToPinCapRule,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    equiv: dict[str, str] | None = None,
) -> dict:
    if equiv is None:
        equiv = {}
    desc = rule.description or f"A {rule.capacitance} cap must exist between pin{rule.pin1} and pin{rule.pin2}"
    ic_pins = pinmap.get(ref_des, {})
    net1 = ic_pins.get(rule.pin1)
    net2 = ic_pins.get(rule.pin2)

    if net1 is None:
        return {"rule_type": "pin_to_pin_cap", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin1} not found in netlist"}
    if net2 is None:
        return {"rule_type": "pin_to_pin_cap", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin2} not found in netlist"}

    net2_resolved = _resolve(net2, equiv)

    for entry in netmap.get(net1, []):
        cap_ref = entry["ref"]
        cap_pin = entry["pin"]
        if cap_ref == ref_des:
            continue
        if not is_capacitor(cap_ref, partmap):
            continue

        cap_ic_pins = pinmap.get(cap_ref, {})
        other_pins = [p for p in cap_ic_pins if p != cap_pin]
        for other_pin in other_pins:
            other_net_resolved = _resolve(cap_ic_pins[other_pin], equiv)
            if other_net_resolved == net2_resolved:
                cap_value = valuemap.get(cap_ref, "")
                if capacitance_match(cap_value, rule.capacitance):
                    return {"rule_type": "pin_to_pin_cap", "description": desc,
                            "status": "PASS",
                            "detail": f"{cap_ref} ({cap_value}) bridges {net1} and {net2}"}

    return {"rule_type": "pin_to_pin_cap", "description": desc,
            "status": rule.severity.upper(),
            "detail": f"No {rule.capacitance} cap found between pin{rule.pin1} ({net1}) and pin{rule.pin2} ({net2})"}


def _check_pin_floating(
    ref_des: str,
    rule: PinFloatingRule,
    netmap: dict,
    pinmap: dict,
) -> dict:
    desc = rule.description or f"pin{rule.pin} must be floating (no external connection)"
    ic_pins = pinmap.get(ref_des, {})
    pin_net = ic_pins.get(rule.pin)

    if pin_net is None:
        # Pin is not in any signal net — truly floating
        return {"rule_type": "pin_floating", "description": desc,
                "status": "PASS", "detail": f"pin{rule.pin} is not connected to any net"}

    # Pin is on a net — check if any other component is also on that net
    net_entries = netmap.get(pin_net, [])
    other_refs = [e["ref"] for e in net_entries if e["ref"] != ref_des]

    if not other_refs:
        return {"rule_type": "pin_floating", "description": desc,
                "status": "PASS",
                "detail": f"pin{rule.pin} is on net {pin_net} with no other connections (stub)"}

    return {"rule_type": "pin_floating", "description": desc,
            "status": rule.severity.upper(),
            "detail": f"pin{rule.pin} is connected to net {pin_net} with: {', '.join(sorted(set(other_refs))[:5])}"}


def _check_pin_to_net_passive(
    ref_des: str,
    rule,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    rule_type: str,
    is_comp_fn,
    normalizer,
    equiv: dict[str, str] | None = None,
) -> dict:
    """
    Generic checker for pin_to_net_resistor / pin_to_net_inductor.
    Finds a passive component on the pin's net whose other terminal connects to rule.net
    (respecting gnd_nets aliases and 0Ω bridges), and whose value falls within [rule.min_value, rule.max_value].
    """
    if equiv is None:
        equiv = {}

    _range_str = ""
    if rule.min_value and rule.max_value:
        _range_str = f"{rule.min_value}–{rule.max_value}"
    elif rule.min_value:
        _range_str = f"≥{rule.min_value}"
    elif rule.max_value:
        _range_str = f"≤{rule.max_value}"
    else:
        _range_str = "any value"

    comp_kind = {"pin_to_net_resistor": "resistor",
                 "pin_to_net_capacitor": "capacitor",
                 "pin_to_net_inductor": "inductor"}.get(rule_type, "passive")

    desc = rule.description or f"pin{rule.pin} needs {_range_str} {comp_kind} to {rule.net}"

    ic_pins = pinmap.get(ref_des, {})
    target_net = ic_pins.get(rule.pin)

    if target_net is None:
        return {"rule_type": rule_type, "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin} not found in netlist"}

    wrong_value_found = []
    wrong_net_found = []

    for entry in netmap.get(target_net, []):
        comp_ref = entry["ref"]
        comp_pin = entry["pin"]
        if comp_ref == ref_des:
            continue
        if not is_comp_fn(comp_ref):
            continue

        comp_pins = pinmap.get(comp_ref, {})
        other_pins = [p for p in comp_pins if p != comp_pin]

        for other_pin in other_pins:
            other_net = comp_pins[other_pin]
            comp_value = valuemap.get(comp_ref, "")

            if _nets_match(other_net, rule.net, ruleset.gnd_nets, equiv):
                # Net matches — check value range
                if rule.min_value is None and rule.max_value is None:
                    return {"rule_type": rule_type, "description": desc,
                            "status": "PASS",
                            "detail": f"{comp_ref} ({comp_value or 'N/A'}) on {target_net}, other pin on {other_net}"}
                ok, reason = _value_in_range(comp_value, rule.min_value, rule.max_value, normalizer)
                if ok:
                    return {"rule_type": rule_type, "description": desc,
                            "status": "PASS",
                            "detail": f"{comp_ref} ({comp_value}) on {target_net}, other pin on {other_net}"}
                wrong_value_found.append(f"{comp_ref}={comp_value} ({reason})")
            else:
                wrong_net_found.append(f"{comp_ref} (other end on {other_net})")

    if wrong_value_found:
        return {"rule_type": rule_type, "description": desc,
                "status": rule.severity.upper(),
                "detail": f"{comp_kind.capitalize()} to {rule.net} found but value out of range: {', '.join(wrong_value_found)}"}
    if wrong_net_found:
        return {"rule_type": rule_type, "description": desc,
                "status": rule.severity.upper(),
                "detail": f"{comp_kind.capitalize()} found but other end not on '{rule.net}': {', '.join(wrong_net_found[:3])}"}
    return {"rule_type": rule_type, "description": desc,
            "status": rule.severity.upper(),
            "detail": f"No {comp_kind} ({_range_str}) to net '{rule.net}' found on pin{rule.pin} (net: {target_net})"}


def _check_pin_to_net_capacitor(
    ref_des: str,
    rule,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    equiv: dict[str, str] | None = None,
) -> dict:
    """
    pin_to_net_capacitor with optional count requirement.
    Collects ALL matching capacitors (value in range, other end on rule.net)
    respecting gnd_nets aliases and 0Ω bridges, and compares against rule.count if specified.
    """
    if equiv is None:
        equiv = {}

    _range_str = ""
    if rule.min_value and rule.max_value:
        _range_str = f"{rule.min_value}–{rule.max_value}"
    elif rule.min_value:
        _range_str = f"≥{rule.min_value}"
    elif rule.max_value:
        _range_str = f"≤{rule.max_value}"
    else:
        _range_str = "any value"

    count_str = f" ×{rule.count}" if rule.count is not None else ""
    desc = rule.description or f"pin{rule.pin} needs {_range_str} capacitor{count_str} to {rule.net}"

    ic_pins = pinmap.get(ref_des, {})
    target_net = ic_pins.get(rule.pin)

    if target_net is None:
        return {"rule_type": "pin_to_net_capacitor", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin} not found in netlist"}

    matched = []
    wrong_value = []
    wrong_net = []

    for entry in netmap.get(target_net, []):
        comp_ref = entry["ref"]
        comp_pin = entry["pin"]
        if comp_ref == ref_des:
            continue
        if not is_capacitor_general(comp_ref, partmap):
            continue

        comp_pins = pinmap.get(comp_ref, {})
        for other_pin, other_net in comp_pins.items():
            if other_pin == comp_pin:
                continue
            comp_value = valuemap.get(comp_ref, "")
            if _nets_match(other_net, rule.net, ruleset.gnd_nets, equiv):
                if rule.min_value is None and rule.max_value is None:
                    matched.append(f"{comp_ref}({comp_value or 'N/A'})")
                else:
                    ok, reason = _value_in_range(comp_value, rule.min_value, rule.max_value, normalize_capacitance)
                    if ok:
                        matched.append(f"{comp_ref}({comp_value})")
                    else:
                        wrong_value.append(f"{comp_ref}={comp_value} ({reason})")
            else:
                wrong_net.append(f"{comp_ref}(other end on {other_net})")

    if rule.count is not None:
        if len(matched) == rule.count:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": "PASS",
                    "detail": f"Found {len(matched)} matching capacitor(s): {', '.join(matched)}"}
        elif len(matched) > 0:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": rule.severity.upper(),
                    "detail": f"Found {len(matched)}/{rule.count} matching capacitor(s): {', '.join(matched)}"}
        elif wrong_value:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": rule.severity.upper(),
                    "detail": f"Capacitor(s) to {rule.net} found but value out of range: {', '.join(wrong_value)}"}
        else:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": rule.severity.upper(),
                    "detail": f"No matching capacitor ({_range_str}) to '{rule.net}' found on pin{rule.pin} (net: {target_net})"}
    else:
        # No count requirement — any match is sufficient
        if matched:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": "PASS",
                    "detail": f"Found: {', '.join(matched)}"}
        elif wrong_value:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": rule.severity.upper(),
                    "detail": f"Capacitor to {rule.net} found but value out of range: {', '.join(wrong_value)}"}
        elif wrong_net:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": rule.severity.upper(),
                    "detail": f"Capacitor found but other end not on '{rule.net}': {', '.join(wrong_net[:3])}"}
        else:
            return {"rule_type": "pin_to_net_capacitor", "description": desc,
                    "status": rule.severity.upper(),
                    "detail": f"No capacitor ({_range_str}) to net '{rule.net}' found on pin{rule.pin} (net: {target_net})"}


def _check_fb_vout_divider(
    ref_des: str,
    rule: FbVoutDividerRule,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    equiv: dict[str, str] | None = None,
) -> dict:
    """
    Verify output voltage via FB pin resistor voltage divider.

    Topology:
        Vout ── R_high ── FB(pin) ── R_low ── GND

    Formula: Vout_calc = Vfb * (R_high + R_low) / R_low

    Finds two resistors on the FB net:
      - R_low : other end connects to GND (any gnd_net)
      - R_high: other end connects to vout_net (= ${rail_name} by default)
    """
    if equiv is None:
        equiv = {}

    desc = rule.description or f"FB divider Vout check (expected {rule.vout})"

    # ── Resolve FB pin net ───────────────────────────────────────────────────
    ic_pins = pinmap.get(ref_des, {})
    fb_net = ic_pins.get(rule.pin)
    if fb_net is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin} (FB) not found in netlist"}

    # ── Parse reference voltages ─────────────────────────────────────────────
    vfb = normalize_voltage(rule.fb_voltage)
    if vfb is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot parse fb_voltage '{rule.fb_voltage}'"}

    vout_expected = normalize_voltage(rule.vout)
    if vout_expected is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot parse expected vout '{rule.vout}'"}

    if vout_expected == 0:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": "Expected Vout is 0V — invalid specification"}

    # ── Find R_low (FB→GND) and R_high (FB→Vout) ────────────────────────────
    r_low: tuple | None = None   # (ref, value_str, other_net)
    r_high: tuple | None = None  # (ref, value_str, other_net)
    all_resistors: list[str] = []

    for entry in netmap.get(fb_net, []):
        comp_ref = entry["ref"]
        comp_pin = entry["pin"]
        if comp_ref == ref_des:
            continue
        if not is_resistor(comp_ref):
            continue

        comp_pins = pinmap.get(comp_ref, {})
        other_pins = [p for p in comp_pins if p != comp_pin]
        for other_pin in other_pins:
            other_net = comp_pins[other_pin]
            val_str = valuemap.get(comp_ref, "")
            all_resistors.append(f"{comp_ref}({val_str}→{other_net})")

            if _nets_match(other_net, "GND", ruleset.gnd_nets, equiv):
                r_low = (comp_ref, val_str, other_net)
            elif rule.vout_net and _nets_match(other_net, rule.vout_net, ruleset.gnd_nets, equiv):
                r_high = (comp_ref, val_str, other_net)

    # ── Diagnostics when resistors not found ─────────────────────────────────
    resistors_found = f"Resistors on FB net ({fb_net}): {', '.join(all_resistors) or 'none'}"

    if r_low is None and r_high is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"No FB divider resistors found. {resistors_found}"}

    if r_low is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"R_low (FB→GND) not found. {resistors_found}"}

    if r_high is None:
        vout_net_name = rule.vout_net or "Vout net"
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"R_high (FB→{vout_net_name}) not found. {resistors_found}"}

    # ── Calculate Vout ───────────────────────────────────────────────────────
    r_low_ohm = normalize_resistance(r_low[1])
    r_high_ohm = normalize_resistance(r_high[1])

    if r_low_ohm is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot parse {r_low[0]} resistance value '{r_low[1]}'"}

    if r_high_ohm is None:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot parse {r_high[0]} resistance value '{r_high[1]}'"}

    if r_low_ohm == 0:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"{r_low[0]} (R_low) is 0Ω — causes division by zero in Vout formula"}

    vout_calc = vfb * (r_high_ohm + r_low_ohm) / r_low_ohm
    error_pct = abs(vout_calc - vout_expected) / vout_expected

    detail = (
        f"R_high={r_high[0]}({r_high[1]}→{r_high[2]}), "
        f"R_low={r_low[0]}({r_low[1]}→{r_low[2]}), "
        f"Vfb={rule.fb_voltage} → Vout_calc={vout_calc:.4f}V "
        f"(expected {rule.vout}, err={error_pct*100:.2f}%)"
    )

    if error_pct <= rule.tolerance:
        return {"rule_type": "fb_vout_divider", "description": desc,
                "status": "PASS", "detail": detail}

    return {"rule_type": "fb_vout_divider", "description": desc,
            "status": rule.severity.upper(), "detail": detail}


# ── PMBus decode helpers ─────────────────────────────────────────────────────

def _decode_linear16_vout(vout_mode_hex: str, vout_cmd_hex: str) -> float | None:
    """Decode PMBus Linear16 VOUT: Vout = mantissa * 2^exponent."""
    try:
        mode_val = int(vout_mode_hex, 16)
        cmd_val = int(vout_cmd_hex, 16)
    except (ValueError, TypeError):
        return None
    # Exponent from VOUT_MODE[4:0], 5-bit 2's complement
    exp = mode_val & 0x1F
    if exp >= 16:
        exp -= 32
    return cmd_val * (2.0 ** exp)


def _decode_linear11(hex_value: str) -> float | None:
    """Decode PMBus Linear11: [15:11]=exponent, [10:0]=mantissa (both 2's complement)."""
    try:
        val = int(hex_value, 16)
    except (ValueError, TypeError):
        return None
    # Exponent: bits [15:11], 5-bit 2's complement
    exp = (val >> 11) & 0x1F
    if exp >= 16:
        exp -= 32
    # Mantissa: bits [10:0], 11-bit 2's complement
    mantissa = val & 0x7FF
    if mantissa >= 1024:
        mantissa -= 2048
    return mantissa * (2.0 ** exp)


def _normalize_numeric(value_str: str) -> float | None:
    """Parse a numeric string that may have a unit suffix (V, kHz, A, etc.)."""
    s = value_str.strip().lower().replace(" ", "")
    # Try stripping common unit suffixes
    for suffix in ["khz", "mhz", "hz", "v", "a", "w", "ohm"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    try:
        return float(s)
    except ValueError:
        return None


# ── Digital POL config checkers ──────────────────────────────────────────────

def _check_pmbus_vout(rule: PmbusVoutCheckRule, regpair) -> dict:
    """Check VOUT_COMMAND via Linear16 decode against expected voltage."""
    desc = rule.description or f"VOUT register check"

    if regpair is None:
        return {"rule_type": "pmbus_vout_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": "No regpair config file loaded for this IC"}

    mode_hex = regpair.pmbus.get(rule.vout_mode_register)
    cmd_hex = regpair.pmbus.get(rule.vout_command_register)

    if mode_hex is None:
        return {"rule_type": "pmbus_vout_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Register '{rule.vout_mode_register}' not found in regpair"}
    if cmd_hex is None:
        return {"rule_type": "pmbus_vout_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Register '{rule.vout_command_register}' not found in regpair"}

    vout_calc = _decode_linear16_vout(mode_hex, cmd_hex)
    if vout_calc is None:
        return {"rule_type": "pmbus_vout_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot decode VOUT_MODE={mode_hex}, VOUT_COMMAND={cmd_hex}"}

    expected = normalize_voltage(rule.expected_vout)
    if expected is None:
        expected = _normalize_numeric(rule.expected_vout)
    if expected is None or expected == 0:
        return {"rule_type": "pmbus_vout_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot parse expected voltage '{rule.expected_vout}'"}

    error_pct = abs(vout_calc - expected) / expected
    detail = (
        f"VOUT_MODE=0x{mode_hex}, VOUT_COMMAND=0x{cmd_hex} → "
        f"Vout={vout_calc:.4f}V (expected {rule.expected_vout}, err={error_pct*100:.2f}%)"
    )

    if error_pct <= rule.tolerance:
        return {"rule_type": "pmbus_vout_check", "description": desc,
                "status": "PASS", "detail": detail}
    return {"rule_type": "pmbus_vout_check", "description": desc,
            "status": rule.severity.upper(), "detail": detail}


def _check_pmbus_linear11(rule: PmbusLinear11CheckRule, regpair) -> dict:
    """Check a PMBus Linear11 register against expected value."""
    desc = rule.description or f"PMBus {rule.register_name} check"

    if regpair is None:
        return {"rule_type": "pmbus_linear11_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": "No regpair config file loaded for this IC"}

    hex_val = regpair.pmbus.get(rule.register_name)
    if hex_val is None:
        return {"rule_type": "pmbus_linear11_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Register '{rule.register_name}' not found in regpair"}

    decoded = _decode_linear11(hex_val)
    if decoded is None:
        return {"rule_type": "pmbus_linear11_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot decode Linear11 value 0x{hex_val}"}

    expected = _normalize_numeric(rule.expected_value)
    if expected is None:
        return {"rule_type": "pmbus_linear11_check", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Cannot parse expected value '{rule.expected_value}'"}

    if expected == 0:
        error_pct = 0.0 if decoded == 0 else 1.0
    else:
        error_pct = abs(decoded - expected) / abs(expected)

    unit_str = f" {rule.unit}" if rule.unit else ""
    detail = (
        f"{rule.register_name}=0x{hex_val} → {decoded:.4g}{unit_str} "
        f"(expected {rule.expected_value}{unit_str}, err={error_pct*100:.2f}%)"
    )

    if error_pct <= rule.tolerance:
        return {"rule_type": "pmbus_linear11_check", "description": desc,
                "status": "PASS", "detail": detail}
    return {"rule_type": "pmbus_linear11_check", "description": desc,
            "status": rule.severity.upper(), "detail": detail}


def _check_register_value(rule: RegisterValueRule, regpair) -> dict:
    """Check a config register bit-field against expected hex value."""
    desc = rule.description or f"Register {rule.register_name} check"

    if regpair is None:
        return {"rule_type": "register_value", "description": desc,
                "status": rule.severity.upper(),
                "detail": "No regpair config file loaded for this IC"}

    # Search in both registers and pmbus sections
    actual = regpair.registers.get(rule.register_name)
    if actual is None:
        actual = regpair.pmbus.get(rule.register_name)
    if actual is None:
        return {"rule_type": "register_value", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"Register '{rule.register_name}' not found in regpair"}

    # Compare as case-insensitive hex strings
    if actual.lower() == rule.expected.lower():
        return {"rule_type": "register_value", "description": desc,
                "status": "PASS",
                "detail": f"{rule.register_name}=0x{actual} (matches expected 0x{rule.expected})"}

    return {"rule_type": "register_value", "description": desc,
            "status": rule.severity.upper(),
            "detail": f"{rule.register_name}=0x{actual} (expected 0x{rule.expected})"}


# ── Top-level entry point ──────────────────────────────────────────────────────

def check_ic(
    ref_des: str,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    regpair=None,
) -> dict:
    # Build net equivalence map for 0Ω resistor bridges
    equiv = _build_net_equiv(partmap, netmap, pinmap, valuemap)

    results = []
    for rule in ruleset.rules:
        result = check_rule(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap, equiv, regpair)
        results.append(result)
    return {
        "ref_des": ref_des,
        "component_type": ruleset.component,
        "results": results,
    }
