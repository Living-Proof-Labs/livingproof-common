"""Content identity for the public source and test inputs behind a report."""
import hashlib
from pathlib import Path


def source_digest(root):
    root = Path(root)
    paths = [root / name for name in ('pyproject.toml', 'uv.lock', 'hatch_build.py', 'docs/usage.md')]
    paths += sorted((root / 'src').rglob('*.py'))
    paths += sorted((root / 'tests').rglob('*.py'))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode() + b'\0' + path.read_bytes())
    return digest.hexdigest()
