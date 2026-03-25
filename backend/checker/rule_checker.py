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
)


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


def capacitance_match(val_str: str, expected_str: str) -> bool:
    a = normalize_capacitance(val_str)
    b = normalize_capacitance(expected_str)
    if a is None or b is None:
        return False
    if b == 0:
        return a == 0
    return abs(a - b) / b < 0.01


def is_capacitor(ref: str, partmap: dict) -> bool:
    footprint = partmap.get(ref, "").lower()
    return footprint.startswith("cc")


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

    return {"rule_type": "unknown", "description": "", "status": "ERROR", "detail": "Unknown rule type"}


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

        # Find the other pin of the capacitor
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
