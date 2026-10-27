"""Record the bounded scenario inventory from native pytest collection and execution."""
import inspect
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from evidence import source_digest  # noqa: E402


def pytest_addoption(parser):
    parser.addoption('--scenario-report', help='Write observed consumer scenario outcomes as JSON')


def pytest_configure(config):
    config._scenario_rows = {}


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        marker = item.get_closest_marker('scenario')
        if marker:
            config._scenario_rows[item.nodeid] = {
                'scenario': marker.args[0], 'test': item.nodeid,
                'steps': inspect.getdoc(item.obj), 'status': 'untested',
            }



class ScenarioRecorder:
    def __init__(self, config):
        self.config = config

    def pytest_runtest_logreport(self, report):
        row = self.config._scenario_rows.get(report.nodeid)
        if row is None:
            return
        if report.failed:
            row['status'] = 'failed'
        elif row['status'] != 'failed':
            if report.skipped:
                row['status'] = 'skipped'
            elif report.when == 'call':
                row['status'] = 'passed'


def pytest_sessionstart(session):
    session.config.pluginmanager.register(ScenarioRecorder(session.config))


def pytest_sessionfinish(session, exitstatus):
    destination = session.config.getoption('--scenario-report')
    if not destination:
        return
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root))
    report = {'source_commit': commit, 'source_dirty': dirty, 'exit_status': int(exitstatus),
              'source_digest': source_digest(root),
              'scenarios': list(session.config._scenario_rows.values())}
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
