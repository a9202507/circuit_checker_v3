"""
IC spec file (TDA38806.spec) parser.

An IC .spec file encodes the IC's datasheet knowledge: how each pin's
behaviour changes based on external component values. This allows the
system to translate design specifications (e.g. fsw="1.1MHz FCCM")
into concrete circuit values (e.g. pin12 resistor = 0 ohm).

Two pin_parameter types:
  - resistor_to_gnd: External resistor selects a mode/frequency.
      Uses `specification` key to look up the value in rail spec.
      `options` maps the spec value to concrete variables.
  - fixed: The IC has a fixed characteristic (e.g. internal FB reference = 0.6V).
      Contributes directly to the variable table via `variables`.

Example filename: TDA38806.spec
"""
from __future__ import annotations
from pydantic import BaseModel
import yaml


class PinParameter(BaseModel):
    name: str = ""
    type: str                                       # "resistor_to_gnd" | "fixed"
    specification: str = ""                         # rail spec key for selection (type=resistor_to_gnd)
    variables: dict[str, str | None] = {}          # for type=fixed
    options: dict[str, dict[str, str | None]] = {} # for type=resistor_to_gnd: option_label → vars


class IcSpec(BaseModel):
    component: str
    pin_parameters: dict[str, PinParameter] = {}   # key = "pin12", "pin6", etc.


def parse_ic_spec(yaml_content: str) -> IcSpec:
    data = yaml.safe_load(yaml_content)
    return IcSpec.model_validate(data)


def build_var_table(rail_spec, ic_spec: IcSpec | None) -> dict[str, str | None]:
    """Build a complete variable substitution table from rail + IC specs.

    Resolution order:
    1. Fixed pin_parameters in IC spec (e.g. FB voltage)
    2. Option-based pin_parameters in IC spec, looked up by rail spec value
    3. Rail spec specifications themselves (${fsw}, ${vout} usable directly)
    4. Rail spec extra variables (highest priority, override everything)
    """
    var_table: dict[str, str | None] = {}

    if ic_spec:
        for pin_key, pin_param in ic_spec.pin_parameters.items():
            if pin_param.type == "fixed":
                var_table.update(pin_param.variables)
            else:
                # Look up the selected option from rail spec
                selected = (rail_spec.specifications or {}).get(pin_param.specification)
                if selected and selected in pin_param.options:
                    var_table.update(pin_param.options[selected])

    # Rail spec top-level fields (${rail_name}, ${ref_des}, ${component} usable in rules)
    if hasattr(rail_spec, 'rail_name'):
        var_table['rail_name'] = rail_spec.rail_name
    if hasattr(rail_spec, 'ref_des'):
        var_table['ref_des'] = rail_spec.ref_des
    if hasattr(rail_spec, 'component'):
        var_table['component'] = rail_spec.component

    # Rail spec specifications override (${fsw}, ${vout} etc. available directly)
    if hasattr(rail_spec, 'specifications'):
        var_table.update(rail_spec.specifications)

    # Extra direct variables at highest priority
    if hasattr(rail_spec, 'variables') and rail_spec.variables:
        var_table.update(rail_spec.variables)

    return var_table
