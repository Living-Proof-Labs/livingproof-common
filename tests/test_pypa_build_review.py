"""The pinned pypa/build dev tool builds the same wheel as uv build (Vera review of #15)."""

import importlib.metadata
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_pin_lock_and_installed_version_agree():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    pins = [spec for spec in project["dependency-groups"]["dev"] if spec.startswith("build==")]
    assert len(pins) == 1
    wanted = pins[0].removeprefix("build==")
    lock = (ROOT / "uv.lock").read_text()
    assert re.search(rf'^name = "build"\nversion = "{re.escape(wanted)}"$', lock, re.MULTILINE)
    assert importlib.metadata.version("build") == wanted


@pytest.mark.skipif(
    not os.environ.get("LIVINGPROOF_NETWORK"),
    reason="set LIVINGPROOF_NETWORK=1 (isolated build fetches hatchling)",
)
def test_pypa_build_wheel_matches_uv_build(tmp_path):
    source = tmp_path / "project"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "dist", "artifacts", "__pycache__", ".pytest_cache", ".ruff_cache"
        ),
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("SETUPTOOLS_SCM_")}
    env["SETUPTOOLS_SCM_PRETEND_VERSION"] = "1.2.3"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path / "uv")],
        cwd=source,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path / "pypa")],
        cwd=source,
        env=env,
        check=True,
        capture_output=True,
    )
    uv_wheel = next((tmp_path / "uv").glob("*.whl"))
    pypa_wheel = next((tmp_path / "pypa").glob("*.whl"))
    assert uv_wheel.name == pypa_wheel.name
    with zipfile.ZipFile(uv_wheel) as left, zipfile.ZipFile(pypa_wheel) as right:
        assert sorted(left.namelist()) == sorted(right.namelist())
        for name in left.namelist():
            assert left.read(name) == right.read(name), name
