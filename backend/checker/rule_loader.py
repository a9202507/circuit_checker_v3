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


Rule = Annotated[
    Union[PinCountRule, PinToGndCapRule, PinToPinCapRule, PinToPinConnectionRule],
    Field(discriminator="type"),
]


class ComponentRuleSet(BaseModel):
    component: str
    gnd_nets: list[str] = ["GND"]
    rules: list[Rule]


def load_ruleset(yaml_content: str) -> ComponentRuleSet:
    data = yaml.safe_load(yaml_content)
    return ComponentRuleSet.model_validate(data)
