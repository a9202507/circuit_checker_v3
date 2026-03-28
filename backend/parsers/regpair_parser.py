"""
Parser for *_regpair.txt files exported from Infineon GUI config tool.

Format:
  //register,code,bit,loop,name,value(hex)
  register,,[1:1],,fccm_mode,1
  register,,[14:8],,i2c_device_addr,10
  pmbus,21,,0,VOUT_COMMAND,00E6
  pmbus,20,,0,VOUT_MODE,18
"""
from __future__ import annotations
from pydantic import BaseModel


class RegpairData(BaseModel):
    registers: dict[str, str] = {}   # {name: hex_value}
    pmbus: dict[str, str] = {}       # {CMD_NAME: hex_value}


def parse_regpair(content: str) -> RegpairData:
    """Parse a regpair text file into structured data."""
    registers: dict[str, str] = {}
    pmbus: dict[str, str] = {}

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue

        parts = line.split(",")
        if len(parts) < 6:
            continue

        record_type = parts[0].strip().lower()

        if record_type == "register":
            # register,,[bits],,name,value(hex)
            name = parts[4].strip()
            value = parts[5].strip()
            if name:
                registers[name] = value

        elif record_type == "pmbus":
            # pmbus,cmd_code,,loop,CMD_NAME,value(hex)
            name = parts[4].strip()
            value = parts[5].strip()
            if name:
                pmbus[name] = value

    return RegpairData(registers=registers, pmbus=pmbus)
