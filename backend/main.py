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
        colors = {"PASS": ("#155724", "#d4edda"), "WARNING": ("#856404", "#fff3cd"), "ERROR": ("#721c24", "#f8d7da")}
        fg, bg = colors.get(status, ("#333", "#eee"))
        return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">{status}</span>'

    ic_rows = ""
    for ic in results:
        overall = "ERROR" if any(r["status"] == "ERROR" for r in ic["results"]) else \
                  "WARNING" if any(r["status"] == "WARNING" for r in ic["results"]) else "PASS"
        rule_rows = ""
        for idx, r in enumerate(ic["results"], 1):
            row_bg = {"PASS": "#f9fff9", "WARNING": "#fffef0", "ERROR": "#fff8f8"}.get(r["status"], "#fff")
            rule_rows += f"""
            <tr style="background:{row_bg}">
              <td style="color:#bbb;text-align:center;padding:6px 10px">{idx}</td>
              <td style="padding:6px 10px">{r.get("description") or r.get("rule_type","")}</td>
              <td style="padding:6px 10px;text-align:center">{badge(r["status"])}</td>
              <td style="padding:6px 10px;color:#555;font-size:12px">{r.get("detail","")}</td>
            </tr>"""
        ic_rows += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;margin-bottom:14px;overflow:hidden">
          <div style="padding:10px 16px;background:#f8f9fa;display:flex;align-items:center;gap:12px">
            {badge(overall)}
            <strong style="font-size:14px">{ic["ref_des"]}</strong>
            <span style="color:#666;font-size:13px">({ic.get("component_type","")})</span>
            <span style="color:#999;font-size:12px">{ic.get("yaml_file","")}</span>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr style="background:#f5f5f5">
                <th style="padding:6px 10px;text-align:left;width:36px">#</th>
                <th style="padding:6px 10px;text-align:left">描述</th>
                <th style="padding:6px 10px;text-align:center;width:90px">狀態</th>
                <th style="padding:6px 10px;text-align:left">詳細</th>
              </tr>
            </thead>
            <tbody>{rule_rows}</tbody>
          </table>
        </div>"""

    yaml_list = "".join(f"<li>{f}</li>" for f in req.yaml_files_used)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>線路檢查報告 — {asc_filename}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 32px; background:#f4f6fb; color:#222; }}
  .card {{ background:#fff; border-radius:10px; padding:24px 28px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  h1 {{ font-size:22px; color:#1a73e8; margin:0 0 4px; }}
  .meta {{ font-size:13px; color:#666; }}
  .summary-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .stat {{ text-align:center; padding:16px; border-radius:8px; background:#f8f9fa; }}
  .stat-num {{ font-size:28px; font-weight:700; }}
  .stat-label {{ font-size:12px; color:#666; margin-top:4px; }}
  ul {{ margin:6px 0; padding-left:20px; font-size:13px; color:#444; }}
</style>
</head>
<body>
  <div class="card">
    <h1>線路檢查報告</h1>
    <div class="meta">匯出時間：{export_dt} &nbsp;|&nbsp; 來源 Netlist：{asc_filename} &nbsp;|&nbsp; BOM：{bom_filename}</div>
    <div class="meta" style="margin-top:6px">規則 YAML：<ul>{yaml_list}</ul></div>
  </div>

  <div class="card">
    <div class="summary-grid">
      <div class="stat"><div class="stat-num">{total_ics}</div><div class="stat-label">檢查 IC 數</div></div>
      <div class="stat"><div class="stat-num" style="color:#155724">{pass_c}</div><div class="stat-label">PASS</div></div>
      <div class="stat"><div class="stat-num" style="color:#856404">{warn_c}</div><div class="stat-label">WARNING</div></div>
      <div class="stat"><div class="stat-num" style="color:#721c24">{err_c}</div><div class="stat-label">ERROR</div></div>
    </div>
  </div>

  <div class="card">
    <h2 style="font-size:16px;color:#1a73e8;margin:0 0 16px">詳細結果</h2>
    {ic_rows}
  </div>
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
