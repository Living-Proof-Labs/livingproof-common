# Living Proof Labs common library

Shared Python libraries for Living Proof Labs tools. Apache-2.0. **No CLI or plugin manager.**

## Develop with the existing environment

The host needs Git, Docker Engine with Compose v2, and Task 3.54.0 on PATH.
It needs permission to use the existing Docker daemon and public network access
to GitHub, Docker Hub, ghcr.io, Debian package mirrors and Python package indexes.
Python, uv, Git test tooling and Debian packaging tools run inside the container.
No credentials, host Python installation or global settings changes are needed.

```sh
git clone https://github.com/Living-Proof-Labs/livingproof-common.git
cd livingproof-common
# For hosts whose checkout owner is not uid/gid 1000:
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
task setup
task verify
task package
task smoke
```

`task setup` builds the pinned development image and synchronizes the committed
lock. Other host tasks reuse that image and named dependency volumes. If Task is
not on the saved environment PATH, that is a bootstrap gap, not a requirement to
install Python. Do not bypass TLS or modify firewall/credentials to repair builds.
Inside the development container, run `task -t Taskfile.runtime.yml verify`.
It reuses the same Dockerfile and never requires nested Docker.

Open `artifacts/docs/index.html` for generated API/Task reference and
`artifacts/coverage/index.html` for software coverage. Tests write
`artifacts/tests.xml`; CI publishes individual cases and retains reports 30 days.
Linux amd64 and arm64 are CI targets; macOS/Windows host behavior is unverified.

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

## Packages and release

`VERSION=1.0.0 task package` builds a wheel, source distribution, and
`python3-livingproof-common_1.0.0_all.deb` with SHA256SUMS. VERSION controls package
metadata only; build identity still describes the actual checkout. There is no
executable, runtime application container or PyPI publication in this change.
Install the release wheel with pip/uv; Debian consumers depend on
`python3-livingproof-common` and install its downloaded `.deb` alongside theirs
using apt. No apt repository is introduced.

Release automation uses collaboration-guidelines **v4.2.1**, assembles a draft
release only after verified main, tests installed packages and attaches artifacts
before publication. Independent review controls merge. Reporter and root consumer
migrations happen only after this library is released; plugin management stays root.
