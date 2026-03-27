component: TDA38806

# IC-level parameter knowledge (datasheet encoding)
# Each pin_parameter defines how a design specification maps to circuit values
pin_parameters:

  pin12:
    name: "FSW / Mode"
    type: resistor_to_gnd
    specification: fsw    # Links to rail spec's specifications.fsw
    options:
      "1.1MHz FCCM":
        pin12_resistor: "0"
      "2MHz FCCM":
        pin12_resistor: "30.1k"
      "600kHz FCCM":
        pin12_resistor: "60.4k"
      "800kHz FCCM":
        pin12_resistor: "49.9k"

  pin6:
    name: "FB Reference Voltage"
    type: fixed
    variables:
      pin6_fb_voltage: "0.6V"
