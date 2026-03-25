"""
Circuit Checker Backend - FastAPI application.
"""
from __future__ import annotations
import io
import zipfile
from datetime import datetime
from typing import List
import yaml
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from parsers.asc_parser import parse_asc
from parsers.bom_parser import parse_bom
from checker.rule_loader import load_ruleset, ComponentRuleSet
from checker.rule_checker import check_ic

app = FastAPI(title="Circuit Checker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
store: dict = {
    "partmap": None,
    "netmap": None,
    "pinmap": None,
    "valuemap": None,
    "rulesets": {},       # {filename: ComponentRuleSet}
    "yaml_contents": {},  # {filename: raw yaml string}
    "asc_filename": "",
    "asc_content": "",
    "bom_filename": "",
    "bom_content": "",
}

# Prefixes that indicate non-IC components
NON_IC_PREFIXES = ("C", "R", "J", "TP", "L", "D", "F", "Y", "T", "FB", "SW")


def _detect_ic_refs(partmap: dict) -> list[str]:
    ic_refs = []
    for ref in sorted(partmap.keys()):
        is_non_ic = any(ref.upper().startswith(p) and (len(ref) == len(p) or ref[len(p)].isdigit())
                        for p in NON_IC_PREFIXES)
        if not is_non_ic:
            ic_refs.append(ref)
    return ic_refs


@app.post("/api/upload/asc")
async def upload_asc(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="replace")
    partmap, netmap, pinmap = parse_asc(content)
    store["partmap"] = partmap
    store["netmap"] = netmap
    store["pinmap"] = pinmap
    store["asc_filename"] = file.filename or "netlist.asc"
    store["asc_content"] = content
    ic_refs = _detect_ic_refs(partmap)
    ic_component_types = {ref: partmap[ref] for ref in ic_refs}
    return {
        "status": "ok",
        "part_count": len(partmap),
        "net_count": len(netmap),
        "ic_refs": ic_refs,
        "all_refs": sorted(partmap.keys()),
        "ic_component_types": ic_component_types,
    }


@app.post("/api/upload/bom")
async def upload_bom(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="replace")
    valuemap = parse_bom(content)
    store["valuemap"] = valuemap
    store["bom_filename"] = file.filename or "bom.BOM"
    store["bom_content"] = content
    return {"status": "ok", "component_count": len(valuemap)}


@app.post("/api/upload/yaml")
async def upload_yaml(files: List[UploadFile] = File(...)):
    loaded = []
    errors = []
    for file in files:
        content = (await file.read()).decode("utf-8", errors="replace")
        filename = file.filename or "unknown.yaml"
        try:
            ruleset = load_ruleset(content)
            store["rulesets"][filename] = ruleset
            store["yaml_contents"][filename] = content
            loaded.append(filename)
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})
    return {"status": "ok", "loaded": loaded, "errors": errors}


@app.get("/api/status")
async def get_status():
    partmap = store["partmap"] or {}
    ic_refs = _detect_ic_refs(partmap) if partmap else []
    return {
        "asc_loaded": store["partmap"] is not None,
        "bom_loaded": store["valuemap"] is not None,
        "yaml_files": list(store["rulesets"].keys()),
        "ic_refs": ic_refs,
    }


class MappingItem(BaseModel):
    ref_des: str
    yaml_file: str


class CheckRequest(BaseModel):
    mappings: list[MappingItem]


@app.post("/api/check")
async def run_check(req: CheckRequest):
    if store["partmap"] is None:
        raise HTTPException(400, "ASC file not loaded")
    if store["valuemap"] is None:
        raise HTTPException(400, "BOM file not loaded")

    results = []
    for mapping in req.mappings:
        ref_des = mapping.ref_des
        yaml_file = mapping.yaml_file
        ruleset = store["rulesets"].get(yaml_file)
        if ruleset is None:
            results.append({
                "ref_des": ref_des,
                "yaml_file": yaml_file,
                "component_type": "",
                "results": [{"rule_type": "load", "description": "Load rule file",
                              "status": "ERROR", "detail": f"YAML file '{yaml_file}' not loaded"}],
            })
            continue

        ic_result = check_ic(
            ref_des=ref_des,
            ruleset=ruleset,
            partmap=store["partmap"],
            netmap=store["netmap"],
            pinmap=store["pinmap"],
            valuemap=store["valuemap"],
        )
        ic_result["yaml_file"] = yaml_file
        results.append(ic_result)

    return {"results": results}


@app.get("/api/yaml/{filename}")
async def get_yaml(filename: str):
    content = store["yaml_contents"].get(filename)
    if content is None:
        raise HTTPException(404, f"YAML file '{filename}' not found")
    return PlainTextResponse(content, media_type="text/plain")


@app.delete("/api/yaml/{filename}")
async def delete_yaml(filename: str):
    store["rulesets"].pop(filename, None)
    store["yaml_contents"].pop(filename, None)
    return {"status": "ok"}


@app.post("/api/yaml/generate")
async def generate_yaml(ruleset: ComponentRuleSet):
    """Validate a ruleset and return it as formatted YAML text."""
    data = ruleset.model_dump()
    yaml_text = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return PlainTextResponse(yaml_text, media_type="text/plain")


# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    results: list[dict]
    yaml_files_used: list[str]


def _generate_html_report(req: ExportRequest, asc_filename: str, bom_filename: str, export_dt: str) -> str:
    results = req.results
    total_ics = len(results)
    all_rules = [r for ic in results for r in ic.get("results", [])]
    pass_c  = sum(1 for r in all_rules if r["status"] == "PASS")
    warn_c  = sum(1 for r in all_rules if r["status"] == "WARNING")
    err_c   = sum(1 for r in all_rules if r["status"] == "ERROR")

    def badge(status: str) -> str:
        colors = {"PASS": ("#007A52", "#E6F7F2"), "WARNING": ("#B07700", "#FFF8E6"), "ERROR": ("#C0392B", "#FFF0EE")}
        fg, bg = colors.get(status, ("#333", "#eee"))
        return f'<span style="background:{bg};color:{fg};padding:2px 9px;border-radius:3px;font-size:11px;font-weight:700;letter-spacing:.3px">{status}</span>'

    ic_rows = ""
    for ic in results:
        overall = "ERROR" if any(r["status"] == "ERROR" for r in ic["results"]) else \
                  "WARNING" if any(r["status"] == "WARNING" for r in ic["results"]) else "PASS"
        rule_rows = ""
        for idx, r in enumerate(ic["results"], 1):
            row_bg = {"PASS": "#F9FFFC", "WARNING": "#FFFEF5", "ERROR": "#FFF9F9"}.get(r["status"], "#fff")
            rule_rows += f"""
            <tr style="background:{row_bg}">
              <td style="color:#bbb;text-align:center;padding:6px 10px">{idx}</td>
              <td style="padding:6px 10px">{r.get("description") or r.get("rule_type","")}</td>
              <td style="padding:6px 10px;text-align:center">{badge(r["status"])}</td>
              <td style="padding:6px 10px;color:#555;font-size:12px">{r.get("detail","")}</td>
            </tr>"""
        ic_rows += f"""
        <div style="border:1px solid #E4E8EE;border-radius:8px;margin-bottom:14px;overflow:hidden">
          <div style="padding:10px 16px;background:#F5F7FA;display:flex;align-items:center;gap:12px;border-left:4px solid {'#E84040' if overall=='ERROR' else '#F0A500' if overall=='WARNING' else '#009B77'}">
            {badge(overall)}
            <strong style="font-size:14px">{ic["ref_des"]}</strong>
            <span style="color:#777;font-size:13px">({ic.get("component_type","")})</span>
            <span style="color:#AAA;font-size:12px">{ic.get("yaml_file","")}</span>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr style="background:#F5F7FA">
                <th style="padding:7px 12px;text-align:left;width:36px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#777;border-bottom:1px solid #E4E8EE">#</th>
                <th style="padding:7px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#777;border-bottom:1px solid #E4E8EE">Description</th>
                <th style="padding:7px 12px;text-align:center;width:90px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#777;border-bottom:1px solid #E4E8EE">Status</th>
                <th style="padding:7px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#777;border-bottom:1px solid #E4E8EE">Detail</th>
              </tr>
            </thead>
            <tbody>{rule_rows}</tbody>
          </table>
        </div>"""

    yaml_list = "".join(f"<li>{f}</li>" for f in req.yaml_files_used)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CircuitChecker — {asc_filename}</title>
<style>
  body {{ font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 32px; background:#F5F7FA; color:#1A1A2E; }}
  .card {{ background:#fff; border:1px solid #E4E8EE; border-radius:8px; padding:24px 28px; margin-bottom:20px; }}
  .card-title {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.6px; color:#777; margin-bottom:14px; padding-bottom:10px; border-bottom:1px solid #E4E8EE; }}
  h1 {{ font-size:22px; font-weight:700; letter-spacing:-0.3px; margin:0 0 4px; }}
  .meta {{ font-size:13px; color:#777; }}
  .summary-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .stat {{ text-align:center; padding:16px; border-radius:6px; background:#F5F7FA; }}
  .stat-num {{ font-size:28px; font-weight:700; }}
  .stat-label {{ font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; color:#777; margin-top:4px; }}
  ul {{ margin:6px 0; padding-left:20px; font-size:13px; color:#555; }}
  .footer {{ margin-top:32px; font-size:11px; color:#AAA; text-align:center; border-top:1px solid #E4E8EE; padding-top:16px; }}
</style>
</head>
<body>
  <div class="card">
    <h1><span style="color:#009B77">Circuit</span><span style="color:#1A1A2E">Checker</span> &nbsp;<span style="font-size:15px;font-weight:400;color:#777">— Circuit Check Report</span></h1>
    <div class="meta" style="margin-top:6px">Exported: {export_dt} &nbsp;|&nbsp; Netlist: {asc_filename} &nbsp;|&nbsp; BOM: {bom_filename}</div>
    <div class="meta" style="margin-top:6px">Rule YAML files:<ul>{yaml_list}</ul></div>
  </div>

  <div class="card">
    <div class="card-title">Summary</div>
    <div class="summary-grid">
      <div class="stat"><div class="stat-num">{total_ics}</div><div class="stat-label">ICs Checked</div></div>
      <div class="stat"><div class="stat-num" style="color:#007A52">{pass_c}</div><div class="stat-label">Pass</div></div>
      <div class="stat"><div class="stat-num" style="color:#B07700">{warn_c}</div><div class="stat-label">Warning</div></div>
      <div class="stat"><div class="stat-num" style="color:#C0392B">{err_c}</div><div class="stat-label">Error</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Detailed Results</div>
    {ic_rows}
  </div>

  <div class="footer">Generated by Circuit Checker · {export_dt}</div>
</body>
</html>"""


@app.post("/api/export")
async def export_report(req: ExportRequest):
    asc_filename = store.get("asc_filename") or "netlist.asc"
    bom_filename = store.get("bom_filename") or "bom.BOM"
    asc_content  = store.get("asc_content") or ""
    bom_content  = store.get("bom_content") or ""

    now = datetime.now()
    export_dt  = now.strftime("%Y-%m-%d %H:%M:%S")
    date_tag   = now.strftime("%Y%m%d_%H%M%S")
    asc_base   = asc_filename.rsplit(".", 1)[0]
    report_name = f"{asc_base}_{date_tag}.html"
    zip_name    = f"{asc_base}_{date_tag}.zip"

    html = _generate_html_report(req, asc_filename, bom_filename, export_dt)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(asc_filename, asc_content)
        zf.writestr(bom_filename, bom_content)
        for yaml_file in req.yaml_files_used:
            zf.writestr(yaml_file, store["yaml_contents"].get(yaml_file, ""))
        zf.writestr(report_name, html)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )
