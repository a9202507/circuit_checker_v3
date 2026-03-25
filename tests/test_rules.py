from src.backend.rule_evaluator import RuleEvaluator
from types import SimpleNamespace

def test_rule_evaluate():
    # create simple rule file
    import yaml, tempfile
    rules = {'rules':[{'id':'r1','description':'test','severity':'ERROR','match':{'tag':'A'}}]}
    tf = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf8')
    yaml.safe_dump(rules, tf)
    tf.close()
    re = RuleEvaluator(tf.name)
    elem = SimpleNamespace(tag='A', attrs={}, path='root/A', line=1, id='')
    findings = re.evaluate_element(elem)
    assert len(findings) == 1
