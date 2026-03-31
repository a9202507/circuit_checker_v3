#!/usr/bin/env python3
"""
Converter: Infineon TDA38725A raw config .txt -> *_regpair.txt

Usage:
    python raw_to_regpair.py <input.txt> [output.txt]

If output is not specified, the output file is placed in the same directory
as the input with "_regpair.txt" appended to the base name.

No external dependencies — stdlib only.
"""
from __future__ import annotations
import os
import sys

# ---------------------------------------------------------------------------
# Register map for TDA38725A (AN235722-V1.0.pdf)
# Each entry: (address, high_bit, low_bit, name)
# Ordered by address ascending, then low_bit ascending within each address.
# ---------------------------------------------------------------------------
REGISTER_MAP: list[tuple[int, int, int, str]] = [
    # 0x0000 — OTP config image selection
    (0x0000,  3,  0, "cnfg_num_user_configs"),
    (0x0000, 13,  8, "cnfg_first_user_image"),
    # 0x0002 — General-purpose register
    (0x0002, 15,  8, "cnfg_gpr_0"),
    # 0x0040 — I2C / PMBus addressing
    (0x0040,  6,  0, "pmb_device_addr"),
    (0x0040, 14,  8, "i2c_device_addr"),
    # 0x0042 — I2C / PMBus protocol options
    (0x0042,  1,  0, "i2c_sda_deglitch_en"),
    (0x0042,  3,  2, "i2c_scl_deglitch_en"),
    (0x0042,  4,  4, "i2c_add_din_hold"),
    (0x0042,  5,  5, "i2c_add_dout_hold"),
    (0x0042,  6,  6, "i2c_disable_addr_offset"),
    (0x0042,  7,  7, "i2c_input_dly_sel"),
    (0x0042,  9,  8, "pmb_pec_mode"),
    (0x0042, 10, 10, "pmb_timeout_disable"),
    (0x0042, 11, 11, "pmb_salert_disable"),
    (0x0042, 12, 12, "pmb_nak_while_nvm_busy"),
    (0x0042, 13, 13, "pmb_no_cml_on_bus_scan"),
    (0x0042, 14, 14, "pmb_page_plus_latch_new_page"),
    # 0x0044 — SVID slew / VR13 / protocol
    (0x0044,  1,  0, "svid_slew_rate_slow"),
    (0x0044,  3,  2, "svid_slew_rate_slow_dflt"),
    (0x0044,  6,  6, "vr13_hc_active"),
    (0x0044,  7,  7, "vr13_hc_support"),
    (0x0044, 12,  8, "svid_protocol_id"),
    (0x0044, 13, 13, "svid_vid_res_override_pin"),
    (0x0044, 14, 14, "svid_vid_res"),
    (0x0044, 15, 15, "svid_mode"),
    # 0x0046 — SVID allcall / local address / slew
    (0x0046,  1,  0, "svid_allcall_act"),
    (0x0046,  3,  2, "svid_allcall_act_dflt"),
    (0x0046,  7,  4, "svid_local_address"),
    (0x0046,  8,  8, "svid_addr_override_pin"),
    (0x0046, 11, 10, "svid_en_to_vrrdy_latency"),
    (0x0046, 15, 12, "svid_slew_rate_fast"),
    # 0x0048 — SVID multi-VR / VBOOT
    (0x0048,  2,  0, "svid_multi_vr_cfg"),
    (0x0048, 15,  8, "svid_vboot"),
    # 0x004A — SVID VID offset / max
    (0x004A,  7,  0, "svid_vid_offset"),
    (0x004A, 15,  8, "svid_vid_max"),
    # 0x004C — SVID VIDO / high-power
    (0x004C,  0,  0, "svid_high_pwr_w_per_bit"),
    (0x004C, 13,  4, "svid_vido_max"),
    # 0x004E — SVID power / ICC
    (0x004E,  7,  0, "svid_pwr_in_max"),
    (0x004E, 13,  8, "svid_icc_max"),
    (0x004E, 14, 14, "svid_iccmax_latches"),
    # 0x0050 — SVID PIN alert thresholds
    (0x0050,  7,  0, "svid_pin_alert_thresh_add"),
    (0x0050, 15,  8, "svid_pin_alert_thresh"),
    # 0x0052 — SVID timeout / temperature max / decay step
    (0x0052,  7,  0, "svid_timeout_value"),
    (0x0052, 13,  8, "svid_temp_max"),
    (0x0052, 15, 14, "svid_decay_step_size"),
    # 0x0054 — Phase shedding / IIN offset / VIN fullscale
    (0x0054,  3,  0, "svid_phshed_sup"),
    (0x0054,  5,  4, "svid_phshed_act"),
    (0x0054, 11,  8, "svid_iin_offset"),
    (0x0054, 13, 12, "svid_vout_pg_offset_sel"),
    (0x0054, 15, 14, "svid_vin_fullscale_sel"),
    # 0x0056 — NegVREN / SVID cfg file ID
    (0x0056,  2,  0, "svid_negvren_act"),
    (0x0056,  7,  3, "svid_negvren_sup"),
    (0x0056, 15,  8, "svid_cfg_file_id"),
    # 0x0058 — SVID alert / VRRDY / PS4
    (0x0058,  5,  0, "svid_alert_delay"),
    (0x0058,  7,  6, "svid_vrrdy_delay"),
    (0x0058,  8,  8, "svid_v12_low_clear_regs_en"),
    (0x0058,  9,  9, "svid_settled_after_decay_0v"),
    (0x0058, 10, 10, "svid_hysteresis_en"),
    (0x0058, 11, 11, "svid_auto_alert"),
    (0x0058, 12, 12, "svid_alert_on_0v"),
    (0x0058, 13, 13, "svid_alert_in_decay"),
    (0x0058, 14, 14, "ps4_dvid_or_decay"),
    (0x0058, 15, 15, "ps4_enable"),
    # 0x005A — SVID PS override / filter / delay
    (0x005A,  2,  0, "svid_ps_override_val"),
    (0x005A,  3,  3, "svid_ps_override"),
    (0x005A,  4,  4, "svid_disable_ps_in_dvid"),
    (0x005A,  5,  5, "ps4_ack_response"),
    (0x005A,  7,  6, "ps3_exit_latency"),
    (0x005A,  9,  8, "svid_filter_corner"),
    (0x005A, 11, 10, "svid_delay_sel"),
    (0x005A, 13, 12, "svid_glitch_eater_del"),
    (0x005A, 14, 14, "svid_tco_delay_mode"),
    # 0x005C — VID DAC / FCCM / OV / I2C level
    (0x005C,  0,  0, "vid_dac_high_res"),
    (0x005C,  1,  1, "fccm_mode"),
    (0x005C,  2,  2, "d2a_pll_en"),
    (0x005C,  5,  4, "ov_neg_current_limit"),
    (0x005C,  6,  6, "ov_asserts_lsfet"),
    (0x005C,  7,  7, "ov_asserts_lsfet_src"),
    (0x005C,  9,  8, "i2c_input_level_sel"),
    (0x005C, 10, 10, "i2c_drive_strength_control"),
    (0x005C, 11, 11, "chip_enable_debounce_delay"),
    (0x005C, 13, 12, "svid_input_level_sel"),
    (0x005C, 14, 14, "svid_drive_strength_control"),
    # 0x005E — Override pins / OVP/UVP relative thresholds
    (0x005E,  0,  0, "ilim_docp_override_pin"),
    (0x005E,  1,  1, "ilim_aocp_override_pin"),
    (0x005E,  2,  2, "lcf_zero_override_pin"),
    (0x005E,  3,  3, "vboot_override_pin"),
    (0x005E,  4,  4, "ton_override_pin"),
    (0x005E,  5,  5, "fccm_override_pin"),
    (0x005E,  6,  6, "fovp_override_pin"),
    (0x005E,  7,  7, "rovp_override_pin"),
    (0x005E, 10,  8, "relative_uvp_thresh"),
    (0x005E, 11, 11, "relative_uvp_thresh_en"),
    (0x005E, 14, 12, "relative_ovp_thresh"),
    (0x005E, 15, 15, "relative_ovp_thresh_en"),
    # 0x0060 — Fixed OVP / AOCP / OCP / blanking / relative disable
    (0x0060,  2,  0, "fixed_ovp_thresh"),
    (0x0060,  3,  3, "docp_from_aocp"),
    (0x0060,  6,  4, "aocp_thresh_sel"),
    (0x0060,  7,  7, "disable_digital_ocp"),
    (0x0060,  9,  8, "blank_oc_sel"),
    (0x0060, 11, 10, "blank_uv_sel"),
    (0x0060, 13, 12, "blank_ov_sel"),
    (0x0060, 14, 14, "disable_relative_uvp"),
    (0x0060, 15, 15, "disable_relative_ovp"),
    # 0x0062 — Loop compensation filter zeros 1-4
    (0x0062,  2,  0, "loop_compensation_filter_zero_1"),
    (0x0062,  6,  4, "loop_compensation_filter_zero_2"),
    (0x0062, 10,  8, "loop_compensation_filter_zero_3"),
    (0x0062, 14, 12, "loop_compensation_filter_zero_4"),
    # 0x0064 — IIN sense / LDO / AFE / GPR / prebias / filter zero 0
    (0x0064,  0,  0, "iin_sense_pd"),
    (0x0064,  1,  1, "iin_sense_mode_pmbus"),
    (0x0064,  2,  2, "input_power_vin_sel"),
    (0x0064,  3,  3, "ldo_en_int_drv"),
    (0x0064,  7,  4, "afe_dig_offset_user"),
    (0x0064,  9,  8, "gpr_usr_0"),
    (0x0064, 10, 10, "svid_use_pmb_cmd"),
    (0x0064, 11, 11, "d2a_enable_prebias"),
    (0x0064, 14, 12, "loop_compensation_filter_zero_0"),
    # 0x0066 — IIN sense gain / offset / mode
    (0x0066,  3,  0, "iin_rsense_value"),
    (0x0066,  7,  4, "iin_gain_user"),
    (0x0066, 13,  8, "iin_offset_user"),
    (0x0066, 15, 14, "iin_sense_mode"),
    # 0x0068 — Current estimation DT / P-term
    (0x0068, 10,  0, "current_est_dt_l"),
    (0x0068, 15, 12, "current_est_p_term"),
    # 0x006A — Load-line / CSA / current est I-term
    (0x006A,  3,  0, "loadline_bandwidth"),
    (0x006A,  5,  4, "loadline_current_sel"),
    (0x006A,  6,  6, "loadline_range_sel"),
    (0x006A,  7,  7, "csa_sample_300mV_valley_in_dem"),
    (0x006A, 11,  8, "loadline_ignore_adc_window"),
    (0x006A, 15, 12, "current_est_i_term"),
    # 0x006C — Low-power / SST / DRV / load-line follow
    (0x006C,  6,  0, "low_power_when_enable_off"),
    (0x006C,  8,  8, "sst_immed_off_ramp"),
    (0x006C,  9,  9, "sst_pgood_off_on_fault"),
    (0x006C, 10, 10, "drv_uvlo_boot_dis"),
    (0x006C, 11, 11, "drv_hss_det_dis"),
    (0x006C, 15, 12, "loadline_follow_adc_window"),
    # 0x006E — COT / OVP/UVP debounce / period range
    (0x006E,  2,  0, "period_range"),
    (0x006E,  3,  3, "vid_direct_clr_on_0v_vid"),
    (0x006E,  6,  4, "cot_freq_comp_entry_dly_sel"),
    (0x006E, 10,  8, "cot_mintoff_sel"),
    (0x006E, 11, 11, "cot_dem_fast_exit"),
    (0x006E, 13, 12, "ovp_fixed_db_sel"),
    (0x006E, 14, 14, "ovp_rel_db_sel"),
    (0x006E, 15, 15, "uvp_rel_db_sel"),
    # 0x0070 — Write/read protect / GPIO / OVP extend / no-pulse
    (0x0070,  1,  0, "write_protect_section"),
    (0x0070,  3,  2, "read_protect_section"),
    (0x0070,  4,  4, "write_protect_mode"),
    (0x0070,  5,  5, "read_protect_mode"),
    (0x0070,  8,  8, "relative_ovp_thresh_res"),
    (0x0070,  9,  9, "fixed_ovp_thresh_ext"),
    (0x0070, 10, 10, "drv_hss_db_sel"),
    (0x0070, 11, 11, "extend_25a_ocp_range"),
    (0x0070, 12, 12, "gpio_ctrl_en"),
    (0x0070, 13, 13, "gpio_ctrl_pin_db_sel"),
    (0x0070, 15, 14, "no_pulse_window"),
    # 0x0072-0x007A — Manufacturer info / user password
    (0x0072, 15,  0, "pmb_mfr_id"),
    (0x0074, 15,  0, "pmb_mfr_date"),
    (0x0076, 15,  0, "pmb_mfr_model"),
    (0x0078, 15,  0, "pmb_mfr_revision"),
    (0x007A, 15,  0, "user_password"),
    # 0x007C-0x0084 — Status masks (5 consecutive 16-bit regs, mask in high byte)
    (0x007C, 15,  8, "status_vout_mask"),
    (0x007E, 15,  8, "status_iout_mask"),
    (0x0080, 15,  8, "status_input_mask"),
    (0x0082, 15,  8, "status_temperature_mask"),
    (0x0084, 15,  8, "status_cml_mask"),
]

# ---------------------------------------------------------------------------
# PMBus command map for TDA38725A
# Each entry: (command_code, name, byte_width)
# command_code * 2 = byte offset from PMBus base address 0x0200
# ---------------------------------------------------------------------------
PMBUS_MAP: list[tuple[int, str, int]] = [
    (0x01, "OPERATION",              1),
    (0x02, "ON_OFF_CONFIG",          1),
    (0x10, "WRITE_PROTECT",          1),
    (0x20, "VOUT_MODE",              1),
    (0x21, "VOUT_COMMAND",           2),
    (0x24, "VOUT_MAX",               2),
    (0x25, "VOUT_MARGIN_HIGH",       2),
    (0x26, "VOUT_MARGIN_LOW",        2),
    (0x27, "VOUT_TRANSITION_RATE",   2),
    (0x28, "VOUT_DROOP",             2),
    (0x29, "VOUT_SCALE_LOOP",        2),
    (0x2B, "VOUT_MIN",               2),
    (0x33, "FREQUENCY_SWITCH",       2),
    (0x35, "VIN_ON",                 2),
    (0x36, "VIN_OFF",                2),
    (0x38, "IOUT_CAL_GAIN",          2),
    (0x39, "IOUT_CAL_OFFSET",        2),
    (0x40, "VOUT_OV_FAULT_LIMIT",    2),
    (0x41, "VOUT_OV_FAULT_RESPONSE", 1),
    (0x44, "VOUT_UV_FAULT_LIMIT",    2),
    (0x45, "VOUT_UV_FAULT_RESPONSE", 1),
    (0x46, "IOUT_OC_FAULT_LIMIT",    2),
    (0x47, "IOUT_OC_FAULT_RESPONSE", 1),
    (0x4F, "OT_FAULT_LIMIT",         2),
    (0x50, "OT_FAULT_RESPONSE",      1),
    (0x51, "OT_WARN_LIMIT",          2),
    (0x55, "VIN_OV_FAULT_LIMIT",     2),
    (0x56, "VIN_OV_FAULT_RESPONSE",  1),
    (0x5E, "POWER_GOOD_ON",          2),
    (0x5F, "POWER_GOOD_OFF",         2),
    (0x60, "TON_DELAY",              2),
    (0x61, "TON_RISE",               2),
    (0x64, "TOFF_DELAY",             2),
    (0x65, "TOFF_FALL",              2),
    (0x7A, "STATUS_VOUT",            1),
    (0x7B, "STATUS_IOUT",            1),
    (0x7C, "STATUS_INPUT",           1),
    (0x7D, "STATUS_TEMPERATURE",     1),
    (0x7E, "STATUS_CML",             1),
    (0xC2, "MFR_VENDOR_INFO_2",      2),
]

PMBUS_BASE = 0x0200


# ---------------------------------------------------------------------------
# Core conversion functions
# ---------------------------------------------------------------------------

def parse_raw_config(text: str) -> dict[int, int]:
    """Parse the hex dump section of a raw config file into {addr: byte}."""
    mem: dict[int, int] = {}
    in_data = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[Configuration Data]":
            in_data = True
            continue
        if stripped in ("[End Configuration Data]", "[End]"):
            in_data = False
            continue
        if not in_data or not stripped:
            continue
        parts = stripped.split()
        # First token must be a 4-digit hex address
        if len(parts) < 2 or len(parts[0]) != 4:
            continue
        try:
            addr = int(parts[0], 16)
        except ValueError:
            continue
        for i, b in enumerate(parts[1:]):
            try:
                mem[addr + i] = int(b, 16)
            except ValueError:
                continue
    return mem


def read_word16(mem: dict[int, int], addr: int) -> int:
    """Read a 16-bit little-endian word from memory."""
    return (mem.get(addr + 1, 0) << 8) | mem.get(addr, 0)


def extract_bits(word: int, high: int, low: int) -> int:
    """Extract bit field [high:low] from a 16-bit word."""
    mask = (1 << (high - low + 1)) - 1
    return (word >> low) & mask


def read_pmbus_value(mem: dict[int, int], cmd_code: int, width: int) -> int:
    """Read a PMBus register value (little-endian) by command code."""
    addr = PMBUS_BASE + cmd_code * 2
    val = 0
    for i in range(width):
        val |= mem.get(addr + i, 0) << (8 * i)
    return val


def convert(input_path: str, output_path: str) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    mem = parse_raw_config(text)
    if not mem:
        raise ValueError(
            f"No configuration data found in '{input_path}'. "
            "Expected a '[Configuration Data]' section."
        )

    lines: list[str] = ["//register,code,bit,loop,name,value(hex)"]

    # Register bit-field entries
    for addr, high, low, name in REGISTER_MAP:
        word = read_word16(mem, addr)
        val = extract_bits(word, high, low)
        bit_str = f"[{high}:{low}]"
        lines.append(f"register,,{bit_str},,{name},{val:X}")

    # PMBus command entries
    for cmd_code, name, width in PMBUS_MAP:
        val = read_pmbus_value(mem, cmd_code, width)
        lines.append(f"pmbus,{cmd_code:02X},,0,{name},{val:0{width * 2}X}")

    output = "\r\n".join(lines)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write(output)

    reg_count = len(REGISTER_MAP)
    pmb_count = len(PMBUS_MAP)
    print(f"Written: {output_path}  ({reg_count} register fields, {pmb_count} PMBus commands)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.dirname(os.path.abspath(input_path))
        output_path = os.path.join(output_dir, base + "_regpair.txt")

    if not os.path.isfile(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    convert(input_path, output_path)


if __name__ == "__main__":
    main()
