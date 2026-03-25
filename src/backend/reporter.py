from jinja2 import Environment, FileSystemLoader
import os
from typing import List

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'templates'))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def render_report(findings: List[object], out_path: str):
    tpl = env.get_template('report.html.j2')
    summary = {'total': len(findings),
               'errors': sum(1 for f in findings if f.severity == 'ERROR'),
               'warnings': sum(1 for f in findings if f.severity == 'WARN')}
    html = tpl.render(summary=summary, findings=findings)
    with open(out_path, 'w', encoding='utf8') as f:
        f.write(html)
