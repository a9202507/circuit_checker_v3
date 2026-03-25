from src.backend.parser import StreamParser

def test_iter_elements_small(tmp_path):
    xml = '<root><Defn objectType="SCHEMATIC"/><GlobalSymbol name="VCC"/></root>'
    p = tmp_path / 's.xml'
    p.write_text(xml, encoding='utf8')
    sp = StreamParser(str(p))
    elems = list(sp.iter_elements())
    tags = [e.tag for e in elems]
    assert 'Defn' in tags and 'GlobalSymbol' in tags
