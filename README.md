# Living Proof Labs common library

Shared Python libraries for Living Proof Labs tools. Apache-2.0. **No CLI or plugin manager.**

**Start here: [consumer documentation](docs/usage.md).** The rendered manual is
currently a tested preview; live publication and verification remain pending.
See [verification and preview instructions](docs/verification.md).

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

Serve `artifacts/docs/html/` over HTTP for generated API/Task reference and
`artifacts/coverage/index.html` for software coverage. Tests write
`artifacts/tests.xml`; CI publishes individual cases and retains reports 30 days.
Linux amd64 and arm64 are CI targets; macOS/Windows host behavior is unverified.

## Consumer usage

See [consumer usage and the build-hook example](docs/usage.md).

## Packages and release

`VERSION=1.0.0 task package` builds a wheel, source distribution, and
`python3-livingproof-common_1.0.0_all.deb` with SHA256SUMS. VERSION controls package
metadata only; build identity still describes the actual checkout. There is no
executable, runtime application container or PyPI publication in this change.
Install the release wheel with pip/uv; Debian consumers depend on
`python3-livingproof-common` and install its downloaded `.deb` alongside theirs
using apt. No apt repository is introduced.

Release automation uses collaboration-guidelines **v4.2.1** (retained independently of the v6.0.0 guidance adoption), assembles a draft
release only after verified main, tests installed packages and attaches artifacts
before publication. Independent review controls merge. Reporter and root consumer
migrations happen only after this library is released; plugin management stays root.
