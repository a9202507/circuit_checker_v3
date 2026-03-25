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
) -> dict:
    """Check a single rule for a given IC instance. Returns a result dict."""

    if isinstance(rule, PinCountRule):
        return _check_pin_count(ref_des, rule, pinmap)

    if isinstance(rule, PinToPinConnectionRule):
        return _check_pin_to_pin_connection(ref_des, rule, pinmap)

    if isinstance(rule, PinToGndCapRule):
        return _check_pin_to_gnd_cap(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap)

    if isinstance(rule, PinToPinCapRule):
        return _check_pin_to_pin_cap(ref_des, rule, partmap, netmap, pinmap, valuemap)

    if isinstance(rule, PinFloatingRule):
        return _check_pin_floating(ref_des, rule, netmap, pinmap)

    if isinstance(rule, PinToNetResistorRule):
        return _check_pin_to_net_passive(ref_des, rule, partmap, netmap, pinmap, valuemap,
                                         "pin_to_net_resistor", is_resistor, normalize_resistance)

    if isinstance(rule, PinToNetCapacitorRule):
        return _check_pin_to_net_passive(ref_des, rule, partmap, netmap, pinmap, valuemap,
                                         "pin_to_net_capacitor",
                                         lambda r: is_capacitor_general(r, partmap),
                                         normalize_capacitance)

    if isinstance(rule, PinToNetInductorRule):
        return _check_pin_to_net_passive(ref_des, rule, partmap, netmap, pinmap, valuemap,
                                         "pin_to_net_inductor", is_inductor, normalize_inductance)

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


def _check_pin_to_pin_connection(ref_des: str, rule: PinToPinConnectionRule, pinmap: dict) -> dict:
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
    if net1 == net2:
        return {"rule_type": "pin_to_pin_connection", "description": desc,
                "status": "PASS", "detail": f"Both pins on net {net1}"}
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
) -> dict:
    desc = rule.description or f"pin{rule.pin} needs {rule.capacitance} cap to GND"
    ic_pins = pinmap.get(ref_des, {})
    target_net = ic_pins.get(rule.pin)

    if target_net is None:
        return {"rule_type": "pin_to_gnd_cap", "description": desc,
                "status": rule.severity.upper(),
                "detail": f"pin{rule.pin} not found in netlist"}

    gnd_nets = set(ruleset.gnd_nets)
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
            if other_net in gnd_nets:
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
) -> dict:
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
            if cap_ic_pins[other_pin] == net2:
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
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
    rule_type: str,
    is_comp_fn,
    normalizer,
) -> dict:
    """
    Generic checker for pin_to_net_resistor / pin_to_net_capacitor / pin_to_net_inductor.
    Finds a passive component on the pin's net whose other terminal connects to rule.net,
    and whose value falls within [rule.min_value, rule.max_value].
    """
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

            if other_net == rule.net:
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


# ── Top-level entry point ──────────────────────────────────────────────────────

def check_ic(
    ref_des: str,
    ruleset: ComponentRuleSet,
    partmap: dict,
    netmap: dict,
    pinmap: dict,
    valuemap: dict,
) -> dict:
    results = []
    for rule in ruleset.rules:
        result = check_rule(ref_des, rule, ruleset, partmap, netmap, pinmap, valuemap)
        results.append(result)
    return {
        "ref_des": ref_des,
        "component_type": ruleset.component,
        "results": results,
    }
