"""
YAML rule file loader and Pydantic models.
"""
from __future__ import annotations
import re
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field
import yaml


class Severity:
    error = "error"
    warning = "warning"


class PinCountRule(BaseModel):
    type: Literal["pin_count"]
    count: list[int]
    severity: str = "error"
    description: str = ""


class PinToGndCapRule(BaseModel):
    type: Literal["pin_to_gnd_cap"]
    pin: str
    capacitance: str
    severity: str = "error"
    description: str = ""


class PinToPinCapRule(BaseModel):
    type: Literal["pin_to_pin_cap"]
    pin1: str
    pin2: str
    capacitance: str
    severity: str = "error"
    description: str = ""


class PinToPinConnectionRule(BaseModel):
    type: Literal["pin_to_pin_connection"]
    pin1: str
    pin2: str
    severity: str = "error"
    description: str = ""


class PinFloatingRule(BaseModel):
    type: Literal["pin_floating"]
    pin: str
    severity: str = "error"
    description: str = ""


class PinToNetResistorRule(BaseModel):
    type: Literal["pin_to_net_resistor"]
    pin: str
    net: str
    min_value: str | None = None  # e.g. "10k"
    max_value: str | None = None  # e.g. "100k"
    severity: str = "error"
    description: str = ""


class PinToNetCapacitorRule(BaseModel):
    type: Literal["pin_to_net_capacitor"]
    pin: str
    net: str
    min_value: str | None = None  # e.g. "100nF"
    max_value: str | None = None  # e.g. "10uF"
    count: int | None = None      # required number of matching capacitors
    severity: str = "error"
    description: str = ""


class PinToNetInductorRule(BaseModel):
    type: Literal["pin_to_net_inductor"]
    pin: str
    net: str
    min_value: str | None = None  # e.g. "10uH"
    max_value: str | None = None  # e.g. "100uH"
    severity: str = "error"
    description: str = ""


class FbVoutDividerRule(BaseModel):
    """Verify output voltage via FB pin voltage divider.

    Finds two resistors on the FB pin's net:
      - R_low : FB pin → GND  (bottom of divider)
      - R_high: FB pin → Vout net (top of divider)

    Calculates: Vout_calc = fb_voltage * (R_high + R_low) / R_low
    Compares against `vout` spec within `tolerance` (default 2%).

    Variables resolved from rail/IC spec via ${...} substitution:
      fb_voltage  — e.g. "${pin6_fb_voltage}"  → "0.6V"
      vout        — e.g. "${vout}"              → "1.8V"
      vout_net    — e.g. "${rail_name}"         → "P1V8_AUX"
    """
    type: Literal["fb_vout_divider"]
    pin: str                       # FB pin number
    fb_voltage: str                # IC internal reference voltage, e.g. "0.6V"
    vout: str                      # Expected output voltage from rail spec, e.g. "1.8V"
    vout_net: str | None = None    # Net name at Vout (top of divider); resolved from ${rail_name}
    tolerance: float = 0.02       # Allowed relative error, default 2%
    severity: str = "error"
    description: str = ""


# ── Digital POL config rules (regpair-based) ─────────────────────────────────


class PmbusVoutCheckRule(BaseModel):
    """Check VOUT_COMMAND register against expected output voltage (Linear16 decode)."""
    type: Literal["pmbus_vout_check"]
    vout_mode_register: str = "VOUT_MODE"
    vout_command_register: str = "VOUT_COMMAND"
    expected_vout: str                # e.g. "0.9V"
    tolerance: float = 0.03
    severity: str = "error"
    description: str = ""


class PmbusLinear11CheckRule(BaseModel):
    """Check a PMBus Linear11 register (FSW, OCP, etc.) against expected value."""
    type: Literal["pmbus_linear11_check"]
    register_name: str = Field(alias="register")  # PMBus command name, e.g. "FREQUENCY_SWITCH"
    expected_value: str               # Numeric string, e.g. "400"
    unit: str = ""                    # Display unit, e.g. "kHz", "A"
    tolerance: float = 0.05
    severity: str = "error"
    description: str = ""

    model_config = {"populate_by_name": True}


class RegisterValueRule(BaseModel):
    """Check a config register bit-field against expected hex value."""
    type: Literal["register_value"]
    register_name: str = Field(alias="register")  # Register name, e.g. "fccm_mode"
    expected: str                     # Expected hex value, e.g. "1"
    severity: str = "error"
    description: str = ""

    model_config = {"populate_by_name": True}


Rule = Annotated[
    Union[
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
    ],
    Field(discriminator="type"),
]


class ComponentRuleSet(BaseModel):
    component: str
    gnd_nets: list[str] = ["GND"]
    rules: list[Rule]


def load_ruleset(yaml_content: str) -> ComponentRuleSet:
    data = yaml.safe_load(yaml_content)
    return ComponentRuleSet.model_validate(data)


_VAR_RE = re.compile(r"\$\{(\w+)\}")


def resolve_rules(
    ruleset: ComponentRuleSet,
    var_table: dict[str, str | None],
) -> ComponentRuleSet:
    """Resolve ${variable} placeholders in rules using a pre-built variable table.

    Args:
        ruleset: The original rule set with ${...} placeholders.
        var_table: Fully resolved {var_name: value} dict (built by _build_var_table).

    Returns:
        A new ComponentRuleSet with all ${...} replaced by concrete values.
    """
    if not var_table:
        return ruleset

    def _resolve_str(val: str | None) -> str | None:
        if val is None:
            return None
        # If entire value is a single ${var}, may resolve to None
        m = _VAR_RE.fullmatch(val)
        if m:
            var_name = m.group(1)
            if var_name in var_table:
                return var_table[var_name]
            return val  # unresolved — keep as-is
        # Partial substitution within a larger string
        def _sub(match):
            vn = match.group(1)
            v = var_table.get(vn)
            if v is None:
                return match.group(0)  # keep placeholder if None
            return v
        return _VAR_RE.sub(_sub, val)

    resolved_rules = []
    for rule in ruleset.rules:
        rule_dict = rule.model_dump(by_alias=True)
        for key, val in rule_dict.items():
            if isinstance(val, str):
                rule_dict[key] = _resolve_str(val)
        resolved_rules.append(rule_dict)

    return ComponentRuleSet(
        component=ruleset.component,
        gnd_nets=ruleset.gnd_nets,
        rules=resolved_rules,
    )
