import yaml
from dataclasses import dataclass
from typing import List


@dataclass
class Finding:
    rule_id: str
    severity: str
    message: str
    element_ref: dict


class RuleEvaluator:
    def __init__(self, rules_path: str):
        with open(rules_path, 'r', encoding='utf8') as f:
            self.rules = yaml.safe_load(f) or {}

    def match(self, rule: dict, elem) -> bool:
        m = rule.get('match', {})
        # simple matches: tag, attr equality, depth_gt
        if 'tag' in m and m['tag'] != elem.tag:
            return False
        if 'attr' in m:
            for k, v in m['attr'].items():
                # allow null/None to mean existence check
                if v is None:
                    if k not in elem.attrs:
                        return False
                else:
                    if elem.attrs.get(k) != v:
                        return False
        if 'depth_gt' in m:
            depth = len(elem.path.split('/')) if elem.path else 0
            if not (depth > int(m['depth_gt'])):
                return False
        return True

    def evaluate_element(self, elem) -> List[Finding]:
        findings = []
        for r in self.rules.get('rules', []):
            if self.match(r, elem):
                findings.append(Finding(
                    rule_id=r.get('id'),
                    severity=r.get('severity', 'INFO'),
                    message=r.get('description',''),
                    element_ref={'tag': elem.tag, 'path': elem.path, 'line': elem.line, 'id': elem.id}
                ))
        return findings
