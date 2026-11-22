"""Bind preview or production manuals to exact version, source, attempt and wheel."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

STABLE = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
PREVIEW = rf"{STABLE}(?:-(?:pr|main)\.[0-9.]+)?"
PYTHON_PREVIEW = rf"{STABLE}(?:\.dev[0-9]+(?:\+[a-z0-9.]+)?)?"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def released_wheel(directory, tag, version, commit):
    if re.fullmatch(STABLE, version) is None or tag != f"v{version}":
        raise ValueError("Expected matching stable manual version and tag")
    release = json.loads((directory / "release.json").read_text())
    if not (release["tag_name"] == tag and release["draft"] is False
            and release["prerelease"] is False and release["immutable"] is True
            and release["published_at"]):
        raise ValueError("Expected the exact immutable published stable release")
    name = f"livingproof_common-{version}-py3-none-any.whl"
    required = {name, "SHA256SUMS", f"livingproof_common-{version}.tar.gz",
                f"python3-livingproof-common_{version}_all.deb"}
    uploaded = [asset for asset in release["assets"] if asset["state"] == "uploaded"]
    if any(sum(asset["name"] == item for asset in uploaded) != 1 for item in required):
        raise ValueError("Missing or ambiguous published package assets")
    assets = {asset["name"]: asset for asset in uploaded}
    wheel = directory / name
    sums = directory / "SHA256SUMS"
    actual = digest(wheel)
    if (assets[name]["digest"] != f"sha256:{actual}"
            or assets["SHA256SUMS"]["digest"] != f"sha256:{digest(sums)}"
            or sums.read_text().splitlines().count(f"{actual}  {name}") != 1):
        raise ValueError("Published wheel digest does not match release and checksum manifest")
    with zipfile.ZipFile(wheel) as archive:
        (member,) = [path for path in archive.namelist()
                     if path == "livingproof_common/_build_provenance.json"]
        record = json.loads(archive.read(member))
    identity = record["identity"]
    if not (record["distribution"] == "livingproof-common"
            and record["package_version"] == version
            and identity["commit"] == commit and identity["base_version"] == version
            and identity["distance"] == 0 and identity["state"] == "clean"
            and identity["history"] == "tagged"):
        raise ValueError("Released wheel was not built from the exact clean stable tag")
    return wheel


def manual_seal(html, version, wheel_version, commit, run, attempt, channel):
    record = json.loads((html / "build.json").read_text())
    expected = {"manual_version": version, "source_commit": commit,
                "run_id": run, "run_attempt": attempt, "channel": channel,
                "source_dirty": False, "package_version": wheel_version}
    if not all(record[key] == value for key, value in expected.items()):
        raise ValueError("Manual identity mismatch: version, commit, run, attempt or channel")
    files = {}
    for path in sorted(html.rglob("*")):
        if path.is_symlink():
            raise ValueError("Manual output must not contain symbolic links")
        if path.is_file():
            files[path.relative_to(html).as_posix()] = digest(path)
    return files


def main():
    mode, version, wheel_version, commit, run, attempt, channel = sys.argv[1:]
    output = Path("artifacts/docs")
    record = manual_seal(output / "html", version, wheel_version, commit, run, attempt, channel)
    seal = output / "seal.json"
    if mode == "seal":
        seal.write_text(json.dumps(record, sort_keys=True) + "\n")
    elif mode == "verify":
        if json.loads(seal.read_text()) != record:
            raise ValueError("Rendered manual does not match the verified seal")
        print(digest(seal))
    else:
        raise ValueError("Expected seal or verify")


if __name__ == "__main__":
    main()
