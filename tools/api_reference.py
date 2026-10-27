"""Run against the installed candidate wheel, never the editable source tree."""
import inspect
from pathlib import Path
import sys

from livingproof_common import versioning

assert Path(versioning.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
NAMES = ('Consumer', 'current_version', 'source_identity', 'display',
         'build_provenance', 'record_build', 'read_provenance')
print('# API reference\n\nGenerated from the installed candidate wheel.\n')
for name in NAMES:
    value = getattr(versioning, name)
    print(f'<a id="livingproof_common.versioning.{name}"></a>\n')
    print(f'## {name}\n\n```python\n{name}{inspect.signature(value)}\n```\n')
    print((inspect.getdoc(value) or 'No docstring supplied.') + '\n')
