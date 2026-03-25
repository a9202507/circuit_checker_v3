"""
YAML rule file loader and Pydantic models.
"""
from __future__ import annotations
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
