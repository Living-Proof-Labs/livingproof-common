"""Display source identity separately from Hatch-VCS's PEP 440 package version."""
import hashlib
import json
import os
import re
import subprocess
from importlib import metadata
from dataclasses import dataclass
from pathlib import Path

PROVENANCE = "_build_provenance.json"


@dataclass(frozen=True)
class Consumer:
    """A caller's distribution and package location, never the common library's.

    ``package_dir`` is the consumer module directory (typically derived from its
    own ``__file__``). Only the direct ``root/src/package`` layout probes live Git.
    Public origins are exact approved URLs; default output hides branch names.
    """

    distribution: str
    package_dir: Path
    public_origins: tuple[str, ...] = ()

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*", self.distribution):
            raise ValueError("Expected a Python distribution name")
        object.__setattr__(self, "package_dir", Path(self.package_dir).resolve())


RELEASE = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"


def git(root, *args):
    """Read this root only, without inherited Git redirection or optional writes."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def branch_slug(name):
    """Bound output and disambiguate names with the same normalized prefix."""
    prefix = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")[:24] or "branch"
    return prefix + "-" + hashlib.sha256(name.encode()).hexdigest()[:8]


def public_branch(root, public_origins):
    # Never publish a private local branch name or remote URL. Tracking refs are
    # local observations of this public origin, not authenticated provenance.
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    origin = git(root, "config", "--get", "remote.origin.url")
    if origin is None or origin.lower() not in {url.lower() for url in public_origins}:
        return "local" if branch else "detached"
    if branch:
        if git(root, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}") == "":
            return branch_slug(branch)
        return "local"
    refs = git(root, "for-each-ref", "--points-at=HEAD", "--format=%(refname)",
               "refs/remotes/origin/")
    names = [ref.removeprefix("refs/remotes/origin/") for ref in (refs or "").splitlines()
             if ref != "refs/remotes/origin/HEAD"]
    return branch_slug(names[0]) if len(names) == 1 else "detached"


def unknown():
    return {"format_version": 1, "base_version": None, "distance": None, "commit": None,
            "branch": "unknown", "state": "unknown", "history": "unavailable"}


def source_identity(root, public_origins=()):
    """Return live identity or None; never inspect a parent or caller's repository."""
    root = Path(root).resolve()
    if not (root / ".git").exists():
        return None
    top = git(root, "rev-parse", "--show-toplevel")
    if top is None or Path(top).resolve() != root:
        return None
    status = git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    if status is None:
        return None
    result = unknown()
    result.update(branch=public_branch(root, public_origins), state="dirty" if status else "clean")
    commit = git(root, "rev-parse", "--verify", "HEAD")
    if commit is None:
        result.update(history="empty", distance=0)
        return result
    result["commit"] = commit
    if git(root, "rev-parse", "--is-shallow-repository") == "true":
        result["history"] = "shallow"
        return result
    # Git --match accepts globs, not regular expressions. Filter tag names
    # before describe so a nearer prerelease cannot hide an older release.
    tags = git(root, "tag", "--list", "v*")
    releases = [tag for tag in (tags or "").splitlines()
                if re.fullmatch(rf"v{RELEASE}", tag)]
    description = (git(root, "describe", "--tags", "--long", "--abbrev=12",
                       *(f"--match={tag}" for tag in releases)) if releases else None)
    match = re.fullmatch(rf"v({RELEASE})-(\d+)-g[0-9a-f]+", description or "")
    if match:
        result.update(base_version=match[1], distance=int(match[5]), history="tagged")
    else:
        count = git(root, "rev-list", "--count", "HEAD")
        result.update(history="untagged", distance=int(count) if count else None)
    return result


def display(identity):
    """SemVer display; development values are identification, not release ordering."""
    base = identity["base_version"] or "0.0.0"
    history, state = identity["history"], identity["state"]
    if history == "tagged" and identity["distance"] == 0 and state == "clean":
        return base
    if history == "unavailable":
        return "0.0.0-dev.unknown+nogit.unknown"
    distance = identity["distance"]
    development = (str(distance) if history == "tagged" else
                   f"untagged.{distance}" if history == "untagged" and distance is not None else
                   "empty" if history == "empty" else "unknown")
    commit = "g" + identity["commit"][:12] if identity["commit"] else "empty"
    suffix = ".shallow" if history == "shallow" else ""
    return f"{base}-dev.{development}+branch.{identity['branch']}.{commit}.{state}{suffix}"


def read_provenance(path, distribution):
    """Read a validated snapshot bound to exactly this consumer distribution."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        identity = value["identity"]
        if (value.get("distribution") != distribution
                or value["format_version"] != 1 or identity["format_version"] != 1
                or not isinstance(value.get("package_version"), str)
                or not re.fullmatch(r"[A-Za-z0-9.+!-]{1,100}", value["package_version"])
                or identity["history"] not in {"tagged", "untagged", "empty", "shallow", "unavailable"}
                or identity["state"] not in {"clean", "dirty", "unknown"}
                or not re.fullmatch(r"[a-z0-9-]{1,40}", identity["branch"])
                or (identity["base_version"] is not None
                    and not re.fullmatch(RELEASE, identity["base_version"]))
                or (identity["commit"] is not None
                    and not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", identity["commit"]))
                or (identity["distance"] is not None
                    and (type(identity["distance"]) is not int or identity["distance"] < 0))):
            return None
        if identity["history"] == "tagged" and any(
                identity[key] is None for key in ("base_version", "distance", "commit")):
            return None
        return value
    except (OSError, ValueError, KeyError, TypeError):
        return None


def build_provenance(root, package_version, consumer):
    """Capture identity at build time, preserving a matching sdist snapshot."""
    root = Path(root).resolve()
    if not consumer.package_dir.is_relative_to(root):
        raise ValueError("Consumer package directory must be inside the build root")
    identity = source_identity(root, consumer.public_origins)
    if identity is None and (root / ".git").exists():
        identity = unknown()
    if identity is None:
        saved = read_provenance(consumer.package_dir / PROVENANCE, consumer.distribution)
        identity = saved["identity"] if saved else unknown()
    return {"format_version": 1, "distribution": consumer.distribution,
            "package_version": package_version, "identity": identity}


def record_build(root, package_version, consumer):
    """Write a build snapshot and return its root-relative artifact path.

    Add the returned path to your build backend's artifacts. Ignore this file in
    Git so a previous build does not itself mark the checkout dirty.
    """
    snapshot = build_provenance(root, package_version, consumer)
    path = consumer.package_dir / PROVENANCE
    path.write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(Path(root).resolve()).as_posix()


def current_version(consumer):
    """Return (display identity, installed PEP 440 version, identity source).

    A wheel uses its recorded snapshot even when the caller runs inside an
    unrelated checkout. An editable src layout probes its own Git root each call.
    Missing Git in a checkout is explicit, not masked by a stale snapshot.
    """
    package_dir = consumer.package_dir
    saved = read_provenance(package_dir / PROVENANCE, consumer.distribution)
    try:
        package_version = metadata.version(consumer.distribution)
    except metadata.PackageNotFoundError:
        package_version = saved["package_version"] if saved else "unavailable"
    root = package_dir.parent.parent
    if package_dir.parent.name == "src" and (root / ".git").exists():
        identity = source_identity(root, consumer.public_origins)
        return display(identity or unknown()), package_version, (
            "checkout" if identity else "checkout-unavailable")
    if saved:
        return display(saved["identity"]), package_version, "recorded-build"
    return display(unknown()), package_version, "unavailable"
