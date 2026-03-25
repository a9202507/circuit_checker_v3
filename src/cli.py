import argparse
import sys
import os

# Ensure project root is on sys.path so running `python src\cli.py` can import `src` package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backend.parser import StreamParser
from src.backend.rule_evaluator import RuleEvaluator
from src.backend.reporter import render_report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--rules', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--ignore-tags', nargs='*', default=[])
    args = p.parse_args()

    parser = StreamParser(args.input, ignore_tags=args.ignore_tags)
    evaluator = RuleEvaluator(args.rules)
    findings = []
    for elem in parser.iter_elements():
        findings.extend(evaluator.evaluate_element(elem))
    render_report(findings, args.out)
    print(f'Wrote report: {args.out}')


if __name__ == '__main__':
    main()
