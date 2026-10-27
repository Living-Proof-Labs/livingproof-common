"""Actual installed artifact behavior, including a Git-free sdist rebuild."""
import re

import pytest

import json
import os
from pathlib import Path
import shutil
import subprocess

from livingproof_common.versioning import PROVENANCE, read_provenance, display
from test_versioning import git

@pytest.mark.scenario('Installed and rebuilt provenance')
def test_built_wheel_and_source_archive_retain_provenance(tmp_path):
    """Given a tagged consumer library built into a wheel and source archive.
    When the wheel is imported without Git and the source archive is rebuilt.
    Then both retain the original consumer identity and repeated dirty builds agree."""
    import sys
    import tarfile
    import zipfile

    root = tmp_path / "project"
    shutil.copytree(Path(__file__).parents[1], root,
                    ignore=shutil.ignore_patterns(".git", ".venv", "dist", "artifacts",
                                                 "__pycache__", ".pytest_cache", ".ruff_cache",
                                                 PROVENANCE))
    git(root, "init", "-b", "main")
    git(root, "add", ".")
    git(root, "commit", "-m", "release fixture")
    git(root, "tag", "v1.4.0")
    env = {k: v for k, v in os.environ.items() if not k.startswith("SETUPTOOLS_SCM_")}
    subprocess.run(["uv", "build", "--offline", "--out-dir", "dist"], cwd=root,
                   env=env, check=True, capture_output=True)
    wheel = next((root / "dist").glob("*.whl"))
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)
    saved = read_provenance(installed / "livingproof_common" / PROVENANCE, "livingproof-common")
    assert saved["identity"]["state"] == "clean"
    assert saved["identity"]["commit"] == git(root, "rev-parse", "HEAD")
    assert display(saved["identity"]) == "1.4.0"
    # Import the actual wheel files outside a checkout, with no Git on PATH.
    probe = ("import sys; sys.path.insert(0, sys.argv[1]); "
             "from livingproof_common.versioning import current_version, Consumer; from pathlib import Path; "
             "import json; print(json.dumps(current_version(Consumer('livingproof-common', Path(sys.argv[1]) / 'livingproof_common'))))")
    output = subprocess.check_output([sys.executable, "-c", probe, str(installed)],
                                     cwd=tmp_path, env={**env, "PATH": ""}, text=True)
    assert json.loads(output) == ["1.4.0", "1.4.0", "recorded-build"]
    with tarfile.open(next((root / "dist").glob("*.tar.gz"))) as archive:
        archive.extractall(tmp_path / "sdist", filter="data")
    source = next((tmp_path / "sdist").iterdir())
    subprocess.run(["uv", "build", "--offline", "--wheel", "--out-dir", "dist"],
                   cwd=source, env=env, check=True, capture_output=True)
    with zipfile.ZipFile(next((source / "dist").glob("*.whl"))) as archive:
        rebuilt = json.loads(archive.read("livingproof_common/" + PROVENANCE))
    assert rebuilt == saved

    (root / "README.md").write_text("Dirty build fixture\n")
    snapshots = []
    for number in range(2):
        output_dir = tmp_path / f"dirty-{number}"
        subprocess.run(["uv", "build", "--offline", "--wheel", "--out-dir", str(output_dir)],
                       cwd=root, env=env, check=True, capture_output=True)
        with zipfile.ZipFile(next(output_dir.glob("*.whl"))) as archive:
            snapshots.append(json.loads(archive.read("livingproof_common/" + PROVENANCE)))
    assert snapshots[0] == snapshots[1]
    assert snapshots[0]["package_version"] == "1.4.1.dev0"
    assert display(snapshots[0]["identity"]).endswith(".dirty")





@pytest.mark.scenario('Distinct installed consumers')
def test_two_installed_consumers_keep_distinct_build_identity(tmp_path):
    """Given two independently tagged consumers built with this library.
    When their installed wheel files report identity without Git.
    Then each reports its own release rather than the library or caller identity."""
    import sys
    import zipfile

    library = tmp_path / 'library'
    library.mkdir()
    subprocess.run(['uv', 'build', '--offline', '--wheel', '--out-dir', str(library)],
                   cwd=Path(__file__).parents[1], check=True, capture_output=True)
    wheel = next(library.glob('*.whl'))
    installed = tmp_path / 'installed'
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)
    for number, name in enumerate(['fixture_root', 'fixture_reporter'], start=5):
        root = tmp_path / name
        package = root / 'src' / name
        package.mkdir(parents=True)
        usage = (Path(__file__).parents[1] / 'docs/usage.md').read_text()
        example = re.findall(r'```python\n(.*?)```', usage, re.S)[0]
        (package / '__init__.py').write_text(example.replace('"my-tool"', f'"{name}"'))
        (root / '.gitignore').write_text(f'src/{name}/{PROVENANCE}\n__pycache__/\ndist/\n')
        (root / 'pyproject.toml').write_text(f'''[build-system]
requires = ["hatchling==1.27.0", "livingproof-common @ {wheel.as_uri()}"]
build-backend = "hatchling.build"
[project]
name = "{name}"
version = "{number}.0.0"
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
''')
        usage = (Path(__file__).parents[1] / 'docs/usage.md').read_text()
        hook = re.findall(r'```python\n(.*?)```', usage, re.S)[1]
        hook = hook.replace('"my-tool"', f'"{name}"').replace('src/my_tool', f'src/{name}')
        (root / 'hatch_build.py').write_text(hook)
        git(root, 'init', '-b', 'main')
        git(root, 'add', '.')
        git(root, 'commit', '-m', 'consumer fixture')
        git(root, 'tag', f'v{number}.0.0')
        subprocess.run(['uv', 'build', '--offline', '--wheel', '--out-dir', str(tmp_path / name / 'dist')],
                       cwd=root, check=True, capture_output=True)
        with zipfile.ZipFile(next((root / 'dist').glob('*.whl'))) as archive:
            archive.extractall(installed)
    probe = '''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import importlib
modules = [importlib.import_module(name) for name in ('fixture_root', 'fixture_reporter')]
print(json.dumps([[m.display_version, m.package_version, m.source] for m in modules]))
'''
    output = subprocess.check_output([sys.executable, '-c', probe, str(installed)],
                                     cwd=tmp_path, env={**os.environ, 'PATH': ''}, text=True)
    assert json.loads(output) == [['5.0.0', '5.0.0', 'recorded-build'],
                                 ['6.0.0', '6.0.0', 'recorded-build']]
