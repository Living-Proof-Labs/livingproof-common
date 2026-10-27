"""Render repository Markdown plus installed API, Task and observed pytest scenarios."""
import hashlib
import json
import os
import posixpath
import re
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from links import check_links
from evidence import source_digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts/docs'
SOURCES = {'README.md': 'index.md', 'docs/usage.md': 'usage.md',
           'docs/verification.md': 'verification.md', '.github/PAGES.md': 'pages.md',
           'docs/search.md': 'search.md', 'docs/development.md': 'development.md',
           'docs/contributing.md': 'contributing.md', 'docs/license.md': 'license.md'}
REPOSITORY = 'https://github.com/Living-Proof-Labs/livingproof-common'
GUIDELINES = 'v6.0.0'
GUIDELINES_COMMIT = '52a2f274576dab20e96ee1152b6c8d187cfbf377'


def rewrite_links(text, path):
    def replace(match):
        url = urlsplit(match[2])
        if url.scheme or url.netloc or not url.path:
            return match[0]
        original = posixpath.normpath(posixpath.join(posixpath.dirname(path), url.path))
        target = {**SOURCES, 'LICENSE': 'assets/LICENSE.txt'}.get(original)
        if target is None:
            return match[0]
        return f'[{match[1]}]({urlunsplit(("", "", target, url.query, url.fragment))})'
    return re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', replace, text)


def task_reference():
    lines = ['# Contributor tasks', '',
             'Generated from the reviewed Taskfiles using native `--list --json` and '
             '`--summary`. Summaries show commands without running task bodies.', '',
             'Use host wrappers from a Docker-equipped host. Inside the prepared '
             'container, use the runtime Taskfile directly; do not nest Docker wrappers.', '']
    records = []
    # Keep the original runtime-task fragment names, then namespace host summaries.
    for filename, label, invocation in [
            ('Taskfile.runtime.yml', 'Prepared container', 'task -t Taskfile.runtime.yml'),
            ('Taskfile.yml', 'Host wrappers', 'task')]:
        lines += [f'## {label}', '', f'Run `{invocation} TASK`.', '']
        tasks = json.loads(run('task', '-t', filename, '--list', '--json'))
        for task in tasks['tasks']:
            summary = run('task', '-t', filename, '--summary', task['name'])
            heading = task['name'] if filename == 'Taskfile.runtime.yml' else f"Host: {task['name']}"
            lines += [f'### {heading}', '', task['desc'], '', '```text', summary, '```', '']
            records.append({'taskfile': filename, 'name': task['name'], 'description': task['desc'],
                            'summary': summary,
                            'taskfile_sha256': hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()})
    return '\n'.join(lines), records



def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, cwd=ROOT, **kwargs).strip()


def main():
    shutil.rmtree(OUTPUT, ignore_errors=True)
    source = OUTPUT / 'source'
    source.mkdir(parents=True)
    commit = run('git', 'rev-parse', 'HEAD')
    dirty = bool(run('git', 'status', '--porcelain'))
    report = json.loads((ROOT / 'artifacts/scenarios.json').read_text())
    assert report['source_commit'] == commit, 'Scenario report is from a different commit'
    assert report['source_digest'] == source_digest(ROOT), 'Scenario report has stale source inputs'
    assert report['scenarios'], 'Missing scenario inventory; run task test'
    context = ('\n\n---\n\n'
               '[Documentation home](https://docs.livingprooflabs.com/) · '
               f'[Source]({REPOSITORY}/tree/{commit}) · '
               f'[Help / report an issue]({REPOSITORY}/issues) · [License](license.md)\n\n'
               f'[Docs: development · {commit[:12]}]({REPOSITORY}/tree/{commit}). '
               f'Source revision: `{commit}` (dirty checkout: {str(dirty).lower()}). '
               '[Version and source](provenance.md).\n')
    for path, destination in SOURCES.items():
        text = rewrite_links((ROOT / path).read_text(), path)
        (source / destination).write_text(text + context)
    (source / 'assets').mkdir()
    shutil.copyfile(ROOT / 'LICENSE', source / 'assets/LICENSE.txt')
    wheels = ROOT / 'artifacts/docs-wheel'
    shutil.rmtree(wheels, ignore_errors=True)
    subprocess.run(['uv', 'build', '--offline', '--wheel', '--out-dir', str(wheels)],
                   cwd=ROOT, check=True)
    wheel, = wheels.glob('*.whl')
    installed = OUTPUT / 'installed'
    subprocess.run(['uv', 'venv', '--no-python-downloads', str(installed)], check=True)
    python = installed / 'bin/python'
    subprocess.run(['uv', 'pip', 'install', '--no-index', '--python', str(python), str(wheel)],
                   check=True)
    reference = run(str(python), '-I', str(ROOT / 'tools/api_reference.py'))
    (source / 'api.md').write_text(reference + context)
    task_text, task_records = task_reference()
    (source / 'tasks.md').write_text(task_text + context)
    (source / 'task-reference.json').write_text(json.dumps(task_records, indent=2) + '\n')
    lines = ['# Executable scenarios', '',
             'Generated from marked native pytest cases and their Given/When/Then docstrings. '
             'Five named behaviors (seven collected cases), not exhaustive library coverage. '
             'Unspecified behavior has no coverage claim. Skipped and untested cases are not passes.', '']
    for row in report['scenarios']:
        lines += [f"## {row['scenario']} — {row['test'].split('::')[-1]}", '',
                  f"Result: **{row['status']}**", '', f"Test: `{row['test']}`", '',
                  '```text', row['steps'], '```', '']
    lines += ['[Raw outcomes](scenarios.json) | [Measured software line coverage](coverage/index.html)', '']
    (source / 'scenarios.md').write_text('\n'.join(lines) + context)
    shutil.copyfile(ROOT / 'artifacts/scenarios.json', source / 'scenarios.json')
    shutil.copytree(ROOT / 'artifacts/coverage', source / 'coverage')
    record = {'source_commit': commit, 'source_dirty': dirty, 'wheel': wheel.name,
              'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'scenario_report_sha256': hashlib.sha256((source / 'scenarios.json').read_bytes()).hexdigest(),
              'workflow_run': ('https://github.com/Living-Proof-Labs/livingproof-common/actions/runs/'
                               + os.environ['GITHUB_RUN_ID'] if os.environ.get('GITHUB_RUN_ID') else None),
              'guidelines': GUIDELINES, 'guidelines_commit': GUIDELINES_COMMIT,
              'candidate_package_version': run(str(python), '-I', '-c',
                  'from importlib.metadata import version; print(version("livingproof-common"))'),
              'task_reference_sha256': hashlib.sha256((source / 'task-reference.json').read_bytes()).hexdigest()}
    (source / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    (source / 'provenance.md').write_text('# Version and source\n\n'
        '<a id="build-context"></a>\n\n'
        f'[Docs: development · {commit[:12]}]({REPOSITORY}/tree/{commit})\n\n'
        f'Candidate package metadata: `{record["candidate_package_version"]}`. '
        f'[Published package releases]({REPOSITORY}/releases) are a separate identity; '
        'the installation guide selects a fixed release example, not a moving latest pin.\n\n'
        'This is development documentation for the exact source below, not a released manual. '
        'Historical manuals are unavailable; use the '
        '[release source tags](https://github.com/Living-Proof-Labs/livingproof-common/tags).\n\n'
        'The wheel is built and installed to generate API signatures and docstrings. '
        'Scenario tests separately build and exercise consumer wheels. '
        'Local results do not establish hosted CI or independent review.\n\n'
        '```json\n' + json.dumps(record, indent=2) + '\n```\n\n[Build record](build.json) · [Task reference inputs](task-reference.json)\n' + context)
    config = yaml.safe_load((ROOT / 'docs/mkdocs.yml').read_text())
    config.update(docs_dir='source', site_dir='html')
    (OUTPUT / 'mkdocs.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    subprocess.run([sys.executable, '-m', 'zensical', 'build', '--clean', '-f',
                    str(OUTPUT / 'mkdocs.yml')], cwd=ROOT, check=True)
    # Keep former single-page Sphinx anchors useful in retained-preview bookmarks.
    home = OUTPUT / 'html/index.html'
    text = home.read_text()
    aliases = {'module-livingproof_common.versioning': 'api.html', 'consumer-identity': 'usage.html', 'api-reference': 'api.html',
               'contributor-tasks': 'tasks.html', 'software-test-coverage': 'coverage/index.html'}
    for name in ('Consumer', 'current_version', 'source_identity', 'display',
                 'build_provenance', 'record_build', 'read_provenance'):
        aliases[f'livingproof_common.versioning.{name}'] = f'api.html#livingproof_common.versioning.{name}'
    compatibility = '<section aria-label="Previous manual bookmarks">' + ''.join(
        f'<p id="{anchor}"><a href="{target}">{anchor}</a></p>'
        for anchor, target in aliases.items()) + '</section>'
    home.write_text(text.replace('</article>', compatibility + '</article>'))
    for filename in ('genindex.html', 'py-modindex.html'):
        (OUTPUT / 'html' / filename).write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>Library API index</title>'
            '<meta http-equiv="refresh" content="0;url=api.html"></head>'
            '<body><a href="api.html">Library API index</a></body></html>')
    check_links(OUTPUT / 'html')
    print(f'Checked manual: {OUTPUT / "html/index.html"}')


if __name__ == '__main__':
    main()
