"""Guard preview asset/anchor integrity and completeness of observed feature results."""
import json
import xml.etree.ElementTree as ET

import pytest

from links import check_links
from scenario_summary import render


def test_project_path_assets_and_fragments(tmp_path):
    (tmp_path / 'index.html').write_text(
        '<a href="/livingproof-common/api.html#Consumer">API</a><img src="icon.png">')
    (tmp_path / 'api.html').write_text('<h1 id="Consumer">Consumer</h1>')
    (tmp_path / 'icon.png').write_bytes(b'fixture')
    check_links(tmp_path)
    (tmp_path / 'icon.png').unlink()
    with pytest.raises(ValueError, match='Broken local link'):
        check_links(tmp_path)
    (tmp_path / 'icon.png').write_bytes(b'fixture')
    (tmp_path / 'api.html').write_text('<h1>Consumer</h1>')
    with pytest.raises(ValueError, match='Broken local fragment'):
        check_links(tmp_path)


def test_feature_summary_preserves_failed_and_skipped_results(tmp_path):
    report = tmp_path / 'scenarios.json'
    junit = tmp_path / 'tests.xml'
    rows = [{'scenario': status, 'test': f'tests/test_example.py::test_{status}',
             'status': status} for status in ['passed', 'failed', 'skipped']]
    report.write_text(json.dumps({'source_commit': 'revision', 'source_dirty': False,
                                 'scenarios': rows}))
    junit.write_text('''<testsuites><testsuite>
      <testcase classname="tests.test_example" name="test_passed"/>
      <testcase classname="tests.test_example" name="test_failed"><failure>actual failure</failure></testcase>
      <testcase classname="tests.test_example" name="test_skipped"><skipped>unavailable</skipped></testcase>
    </testsuite></testsuites>''')
    output = render(report, junit)
    assert '| failed | `tests/test_example.py::test_failed` | failed |' in output
    assert '| skipped | `tests/test_example.py::test_skipped` | skipped |' in output
    rows[1]['status'] = 'passed'
    report.write_text(json.dumps({'source_commit': 'revision', 'source_dirty': False,
                                 'scenarios': rows}))
    with pytest.raises(AssertionError, match='inconsistent'):
        render(report, junit)
    junit.write_text('<testsuites/>')
    with pytest.raises(AssertionError, match='Missing'):
        render(report, junit)
    junit.write_text('<incomplete')
    with pytest.raises(ET.ParseError):
        render(report, junit)
