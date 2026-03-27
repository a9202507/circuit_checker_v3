"""
Rail spec file (.spec) parser.

A rail .spec file is YAML-formatted, named after the output power rail
(which must match a net name in the .asc netlist). It defines:
  - Which IC ref_des implements this rail
  - The IC component type (must match BOM)
  - Design specifications: Vout, FSW, OCP, I2C address, etc.
  - Optional extra variables for direct ${} substitution

Example filename: P1V8_AUX.spec
"""
from __future__ import annotations
from pydantic import BaseModel
import yaml


class RailSpec(BaseModel):
    rail_name: str                       # Must match a net name in the .asc
    ref_des: str                         # IC reference designator (e.g. U69)
    component: str                       # IC component type (e.g. TDA38806)
    specifications: dict[str, str] = {}  # Design specs: {fsw: "1.1MHz FCCM", vout: "1.8V"}
    variables: dict[str, str] = {}       # Extra direct-substitution variables


def parse_rail_spec(yaml_content: str) -> RailSpec:
    data = yaml.safe_load(yaml_content)
    return RailSpec.model_validate(data)
