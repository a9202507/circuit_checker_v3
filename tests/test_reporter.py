from src.backend.reporter import render_report
from types import SimpleNamespace

def test_reporter_creates_file(tmp_path):
    f = tmp_path / 'out.html'
    findings = [SimpleNamespace(severity='ERROR', rule_id='r1', message='m', element_ref={'tag':'A','path':'root/A','line':1,'id':''})]
    render_report(findings, str(f))
    assert f.exists()
