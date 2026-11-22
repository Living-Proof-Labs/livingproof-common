"""Release delivery must be bound to the tested commit and immutable wheel."""
import json
import zipfile
from pathlib import Path

import pytest
import yaml

from manual_release import digest, manual_seal, released_wheel

COMMIT = "a" * 40
VERSION = "1.0.31"
TAG = f"v{VERSION}"
WHEEL = f"livingproof_common-{VERSION}-py3-none-any.whl"


@pytest.fixture
def publication(tmp_path):
    wheel = tmp_path / WHEEL
    record = {"distribution": "livingproof-common", "package_version": VERSION,
              "identity": {"commit": COMMIT, "base_version": VERSION, "distance": 0,
                           "state": "clean", "history": "tagged"}}
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("livingproof_common/_build_provenance.json", json.dumps(record))
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{digest(wheel)}  {WHEEL}\n")
    assets = [{"name": name, "state": "uploaded",
               "digest": f"sha256:{digest(tmp_path / name)}"
               if name in {WHEEL, sums.name} else "unused"}
              for name in (WHEEL, sums.name, f"livingproof_common-{VERSION}.tar.gz",
                           f"python3-livingproof-common_{VERSION}_all.deb")]
    release = {"tag_name": TAG, "draft": False, "prerelease": False, "immutable": True,
               "published_at": "2026-11-22T00:00:00Z", "assets": assets}
    (tmp_path / "release.json").write_text(json.dumps(release))
    return tmp_path, release


def test_exact_immutable_publish_returns_only_the_released_wheel(publication):
    directory, _ = publication
    assert released_wheel(directory, TAG, VERSION, COMMIT) == directory / WHEEL


@pytest.mark.parametrize("field,value", [
    ("tag_name", "v1.0.30"), ("draft", True), ("prerelease", True),
    ("immutable", False), ("published_at", None), ("assets", []),
])
def test_failed_missing_or_mismatched_release_never_uses_a_wheel(publication, field, value):
    directory, release = publication
    release[field] = value
    (directory / "release.json").write_text(json.dumps(release))
    with pytest.raises(ValueError):
        released_wheel(directory, TAG, VERSION, COMMIT)


def test_reject_a_wheel_even_of_the_right_version_if_for_different_source(publication):
    directory, _ = publication
    with pytest.raises(ValueError, match="exact clean stable tag"):
        released_wheel(directory, TAG, VERSION, "b" * 40)


@pytest.mark.parametrize("file", [WHEEL, "SHA256SUMS"])
def test_reject_mutated_published_assets(publication, file):
    directory, _ = publication
    with (directory / file).open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="digest"):
        released_wheel(directory, TAG, VERSION, COMMIT)


def test_manual_seal_binds_every_rendered_byte_and_job_identity(tmp_path):
    index = tmp_path / "index.html"
    index.write_text("verified")
    (tmp_path / "build.json").write_text(json.dumps(
        {"manual_version": VERSION, "package_version": VERSION, "source_commit": COMMIT,
         "run_id": "9", "run_attempt": "2", "channel": "candidate", "source_dirty": False}))
    arguments = (tmp_path, VERSION, VERSION, COMMIT, "9", "2", "candidate")
    original = manual_seal(*arguments)
    index.write_text("different")
    assert original["index.html"] != manual_seal(*arguments)["index.html"]
    with pytest.raises(ValueError, match="identity mismatch"):
        manual_seal(*arguments[:-2], "1", "candidate")
    with pytest.raises(ValueError, match="identity mismatch"):
        manual_seal(*arguments[:-1], "release")


def test_retry_is_delivery_only_and_publication_retains_asset_order():
    root = Path(__file__).resolve().parents[1]
    jobs = yaml.safe_load((root / ".github/workflows/verify.yml").read_text())["jobs"]
    writer = jobs["release"]
    assert writer["with"]["draft-release"] is True
    assert writer["with"]["expected-version"] == "${{ needs.version.outputs.version }}"
    assert "needs.documentation.outputs.manual-seal" in writer["if"]
    assert "github.event_name == 'push'" in writer["if"]
    assert "github.event_name == 'push'" in jobs["publish"]["if"]
    steps = jobs["publish"]["steps"]
    commands = [step.get("run", "") for step in steps]
    upload = next(i for i, line in enumerate(commands) if "gh release upload" in line)
    finish = next(i for i, line in enumerate(commands) if "gh release edit" in line)
    assert "dist/*.whl dist/*.tar.gz dist/*.deb dist/SHA256SUMS" in commands[upload]
    assert commands.index("task package") < commands.index("task smoke") < upload < finish
    deploy = jobs["deploy-documentation"]
    assert "github.event_name == 'workflow_dispatch'" in deploy["if"]
    assert "needs.release.result == 'skipped'" in deploy["if"]
    assert "needs.publish.result == 'skipped'" in deploy["if"]
    assert "github.ref == 'refs/heads/main'" in deploy["if"]
