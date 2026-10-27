# Consumer usage

## Consumer contract

```python
from pathlib import Path
from livingproof_common.versioning import Consumer, current_version

consumer = Consumer("my-tool", Path(__file__).resolve().parent)
display_version, package_version, source = current_version(consumer)
```

The distribution and package directory belong to **the consumer**. The default
hides branch names; an explicit tuple of approved public origin URLs permits a
bounded branch slug only when an origin tracking ref is present. This is local
observation, not authenticated provenance. A clean exact `vX.Y.Z` release displays
`X.Y.Z`; other builds report development identity, commit and state. Prerelease
or malformed tags never hide an older valid release. Shallow history is explicit.

Build hooks call `record_build(root, package_version, consumer)` and add the
returned relative file to backend artifacts. For example, a consumer Hatch hook
can use the released dependency directly:

```python
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from livingproof_common.versioning import Consumer, record_build

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        consumer = Consumer("my-tool", Path(self.root) / "src/my_tool")
        artifact = record_build(self.root, self.metadata.version, consumer)
        build_data.setdefault("artifacts", []).append(artifact)
```

Add the same exact released `livingproof-common` version to the consumer's
build-system requirements and runtime dependencies. Configure Hatch's custom hook
path to this adapter. The adapter supplies context; all identity logic stays in
the shared library. Two installed fixture consumers exercise this contract in CI.

Ignore `_build_provenance.json` in
Git. Hatch-VCS/setuptools-scm continue to own PEP 440 metadata; configure
`local_scheme = "no-local-version"` for deterministic dirty metadata. Consumer
build and runtime dependencies must both pin the published common library.
Wheel/sdist/Debian retain consumer-bound snapshots without `.git`. Editable
`root/src/package` checkouts report live dirty state. Other layouts use snapshots.
Dirty identity is not a digest of uncommitted content; no wall-clock suffix is added.


## Related projects

The [Living Proof manual](https://docs.livingprooflabs.com/livingproof/) explains
the consuming command home. This common package supplies identity only.

Install a released wheel from [GitHub Releases](https://github.com/Living-Proof-Labs/livingproof-common/releases).
The current verified release is v1.0.0; pin the same wheel in build and runtime dependencies.
