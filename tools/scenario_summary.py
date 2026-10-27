"""Validate scenario/JUnit agreement before exposing individual feature results in CI."""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def render(report_path, junit_path):
    report = json.loads(Path(report_path).read_text())
    cases = ET.parse(junit_path).getroot().findall('.//testcase')
    assert cases and report['scenarios'], 'Missing test results or scenario inventory'
    observed = {}
    for case in cases:
        key = (case.attrib['classname'], case.attrib['name'])
        assert key not in observed, f'Duplicate JUnit case: {key}'
        observed[key] = ('failed' if case.find('failure') is not None or
                        case.find('error') is not None else
                        'skipped' if case.find('skipped') is not None else 'passed')
    lines = ['## Consumer feature scenarios', '',
             f"Revision: `{report['source_commit']}`; dirty: `{report['source_dirty']}`.", '',
             'Bounded inventory; unspecified behavior is outside this denominator.', '',
             '| Scenario | Test | Result |', '| --- | --- | --- |']
    for row in report['scenarios']:
        path, name = row['test'].split('::', 1)
        key = (path.removesuffix('.py').replace('/', '.'), name)
        assert observed.get(key) == row['status'], f'Incomplete or inconsistent result: {key}'
        lines.append(f"| {row['scenario']} | `{row['test']}` | {row['status']} |")
    lines += ['', f"Scenario counts: {dict(Counter(r['status'] for r in report['scenarios']))}. "
              f"Full JUnit suite: {len(cases)} cases.", '',
              'Manual previews: 14 days. Raw library reports: 30 days. '
              'See this run’s artifact links below.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    Path('artifacts/scenario-summary.md').write_text(
        render('artifacts/scenarios.json', 'artifacts/tests.xml'))
