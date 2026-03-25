# src/main.py
import shutil
import tempfile
import yaml
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from starlette.templating import Jinja2Templates
import jinja2

from src.backend.parser import StreamParser
from src.backend.rule_evaluator import RuleEvaluator

# --- Pydantic Models for YAML Generation ---
class Match(BaseModel):
    tag: str
    attr: Dict[str, Optional[str]]

class Rule(BaseModel):
    id: str
    description: str
    severity: str
    match: Match

class Ruleset(BaseModel):
    rules: List[Rule]

# --- FastAPI App Setup ---
app = FastAPI()

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"), cache_size=0)
templates = Jinja2Templates(env=jinja_env)

# --- FastAPI Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    """Provides the main file upload page."""
    return templates.TemplateResponse(request, "index.html.j2", {})

@app.get("/generator", response_class=HTMLResponse)
async def read_generator(request: Request):
    """Provides the Rule Generator page."""
    return templates.TemplateResponse(request, "generator.html.j2", {})

@app.post("/generate-yaml")
async def generate_yaml(ruleset: Ruleset):
    """
    Receives rule data as JSON, converts it to YAML, and returns it as a downloadable file.
    """
    # Convert Pydantic models to a standard dict for dumping
    data_to_dump = ruleset.dict()
    
    # Dump the data to a YAML string
    yaml_data = yaml.dump(data_to_dump, allow_unicode=True, sort_keys=False)
    
    # Return as a downloadable file
    return Response(
        content=yaml_data,
        media_type="application/x-yaml",
        headers={"Content-Disposition": "attachment; filename=generated_rules.yaml"}
    )

@app.post("/check", response_class=HTMLResponse)
async def run_check(request: Request, xml_file: UploadFile = File(...), yaml_file: UploadFile = File(...)):
    """
    Receives uploaded files, performs the check, and returns an HTML report.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        rules_path = f"{temp_dir}/rules.yaml"
        with open(rules_path, "wb") as f:
            shutil.copyfileobj(yaml_file.file, f)

        xml_path = f"{temp_dir}/circuit.xml"
        with open(xml_path, "wb") as f:
            shutil.copyfileobj(xml_file.file, f)

        evaluator = RuleEvaluator(rules_path=rules_path)
        parser = StreamParser(input_path=xml_path)
        
        all_findings = []
        for element in parser.iter_elements():
            findings = evaluator.evaluate_element(element)
            if findings:
                all_findings.extend(findings)

        summary = {
            'total': len(all_findings),
            'errors': sum(1 for f in all_findings if f.severity.upper() == 'ERROR'),
            'warnings': sum(1 for f in all_findings if f.severity.upper() == 'WARN'),
            'info': sum(1 for f in all_findings if f.severity.upper() == 'INFO'),
        }
        context = {"request": request, "summary": summary, "findings": all_findings}
        return templates.TemplateResponse(request, "report.html.j2", context)

    finally:
        shutil.rmtree(temp_dir)
