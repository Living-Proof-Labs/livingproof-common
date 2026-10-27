"""Render repository Markdown plus installed API, Task and observed pytest scenarios."""
import hashlib
import json
import os
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
           'docs/search.md': 'search.md'}


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
    context = f'\n\nDevelopment manual: `{commit}` (dirty checkout: {str(dirty).lower()}). '
    context += '[Build and test context](provenance.md).\n'
    for path, destination in SOURCES.items():
        text = (ROOT / path).read_text()
        # This bounded allowlist is also the complete relative link mapping.
        for original, target in SOURCES.items():
            text = text.replace(f']({original})', f']({target})')
        (source / destination).write_text(text + context)
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
    tasks = json.loads(run('task', '-t', 'Taskfile.runtime.yml', '--list', '--json'))
    lines = ['# Contributor tasks', '', 'Inside the prepared environment, use '
             '`task -t Taskfile.runtime.yml TASK`. Host tasks wrap Docker Compose.', '']
    for task in tasks['tasks']:
        lines += [f"## {task['name']}", '', task['desc'], '']
    (source / 'tasks.md').write_text('\n'.join(lines) + context)
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
              'guidelines': 'v5.0.0', 'guidelines_commit': 'dd4b0391a9a66fa7944f6655aac57c67d3f8c002'}
    (source / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    (source / 'provenance.md').write_text('# Build context\n\n'
        'This is development documentation for the exact source below, not a released manual. '
        'Historical manuals are unavailable; use the '
        '[release source tags](https://github.com/Living-Proof-Labs/livingproof-common/tags).\n\n'
        'The wheel is built and installed to generate API signatures and docstrings. '
        'Scenario tests separately build and exercise consumer wheels. '
        'Local results do not establish hosted CI or independent review.\n\n'
        '```json\n' + json.dumps(record, indent=2) + '\n```\n\n[Build record](build.json)\n')
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
