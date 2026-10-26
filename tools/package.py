"""Build standard Python artifacts plus a pure Python Debian library."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def main():
    version = os.environ.get("VERSION", "0.0.0")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise SystemExit("Expected VERSION=X.Y.Z for release package metadata")
    out = Path("dist")
    out.mkdir(exist_ok=True)
    subprocess.run(["uv", "build", "--out-dir", str(out)], check=True,
                   env={**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": version})
    wheel = out / f"livingproof_common-{version}-py3-none-any.whl"
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        packages = stage / "usr/lib/python3/dist-packages"
        with zipfile.ZipFile(wheel) as archive:
            for entry in archive.infolist():
                path = Path(entry.filename)
                if (path.is_absolute() or ".." in path.parts or not path.parts
                        or path.parts[0] not in {"livingproof_common",
                                                 f"livingproof_common-{version}.dist-info"}):
                    raise ValueError("Unexpected wheel path")
                data = archive.read(entry)
                if data.startswith(b"\x7fELF") or path.suffix in {".so", ".dll", ".dylib", ".pyc"}:
                    raise ValueError("Architecture: all cannot include native code")
                if not entry.is_dir():
                    target = packages / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
        control = stage / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(f"""Package: python3-livingproof-common
Version: {version}
Section: python
Priority: optional
Architecture: all
Depends: python3 (>= 3.11)
Maintainer: Living Proof Labs <rivet@rollerbot.ai>
Description: Shared version and build provenance library for Living Proof Labs
""")
        copyright = stage / "usr/share/doc/python3-livingproof-common/copyright"
        copyright.parent.mkdir(parents=True)
        shutil.copyfile("LICENSE", copyright)
        stage.chmod(0o755)
        for path in stage.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage),
                        str(out / f"python3-livingproof-common_{version}_all.deb")], check=True)
    files = sorted(p for p in out.iterdir() if p.suffix in {".whl", ".gz", ".deb"})
    (out / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))


if __name__ == "__main__":
    main()
