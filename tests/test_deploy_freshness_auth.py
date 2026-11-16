# SPDX-License-Identifier: Apache-2.0
"""The pages freshness read must stay an authenticated gh api call.

This repository already calls git/ref/heads/main with gh api and
GH_TOKEN: ${{ github.token }}. An anonymous call shares the runner rate
limit, fails with HTTP 403, and leaves the published site on the previous
release. contents: read is enough; the deploy job must not gain contents: write.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
FRESHNESS = "git/ref/heads/main"
TOKEN_VALUE = re.compile(r"\$\{\{\s*(?:github\.token|secrets\.GITHUB_TOKEN)\s*\}\}")
DIRECT_HTTP = re.compile(
    r"urlopen|urllib\.request|requests\.(?:get|post|request)"
    r"|(?:^|[^\w])curl\s|http\.client|\bfetch\("
)
GH_API = re.compile(r"\bgh\s+api\b")
EXPECTED_SHA = "a" * 40

UNAUTHENTICATED = """\
jobs:
  deploy:
    permissions:
      pages: write
      id-token: write
    steps:
      - name: Check current main inside deployment lock
        env:
          EXPECTED_SHA: abcdef
        run: |
          python - <<'PYCODE'
          import json, os, urllib.request
          url = 'https://api.github.com/repos/example/repo/git/ref/heads/main'
          with urllib.request.urlopen(url, timeout=30) as response:
              current = json.load(response)['object']['sha']
          PYCODE
"""

TOKEN_PRESENT_BUT_UNUSED = """\
jobs:
  deploy:
    permissions:
      contents: read
    steps:
      - name: Check current main
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          python - <<'PYCODE'
          import urllib.request
          url = 'https://api.github.com/repos/example/repo/git/ref/heads/main'
          urllib.request.urlopen(url)
          PYCODE
"""

GH_WITHOUT_TOKEN = """\
permissions:
  contents: read
jobs:
  deploy:
    steps:
      - name: Require current main
        run: |
          current=$(gh api repos/example/repo/git/ref/heads/main --jq .object.sha)
          test "$current" = "$GITHUB_SHA"
"""

AUTHENTICATED_GH = """\
permissions:
  contents: read
jobs:
  deploy:
    permissions:
      contents: read
    steps:
      - name: Require current main
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          ref="repos/${GITHUB_REPOSITORY}/git/ref/heads/main"
          current=$(gh api "$ref" --jq .object.sha)
          test "$current" = "$GITHUB_SHA"
"""

AUTHENTICATED_URLLIB = """\
jobs:
  deploy:
    permissions:
      contents: read
      pages: write
      id-token: write
    steps:
      - name: Require current main
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          python - <<'PYCODE'
          import json, os, urllib.request
          token = os.environ["GITHUB_TOKEN"]
          repo = os.environ["GITHUB_REPOSITORY"]
          url = f"https://api.github.com/repos/{repo}/git/ref/heads/main"
          request = urllib.request.Request(
              url,
              headers={"Authorization": f"Bearer {token}"},
          )
          with urllib.request.urlopen(request, timeout=30) as response:
              current = json.load(response)["object"]["sha"]
          PYCODE
"""

GH_STUB = """\
#!/bin/sh
if [ -z "$GH_TOKEN" ]; then
  echo "gh: missing GH_TOKEN" >&2
  exit 1
fi
printf '%s\\n' "$*" > "$GH_CAPTURE"
if [ "$GH_STATUS" != 0 ]; then
  echo "HTTP Error $GH_STATUS: rate limit exceeded" >&2
  exit "$GH_STATUS"
fi
printf '%s\\n' "$GH_SHA"
"""


def _token_names(env):
    if not isinstance(env, dict):
        return []
    return [
        name
        for name, value in env.items()
        if name in {"GH_TOKEN", "GITHUB_TOKEN"}
        and isinstance(value, str)
        and TOKEN_VALUE.search(value)
    ]


def _sends_bearer(script, token_names):
    if "Authorization" not in script or "Bearer" not in script:
        return False
    return any(name in script for name in token_names)


def _contains_freshness(value, *, skip_run=False):
    if isinstance(value, str):
        return FRESHNESS in value
    if isinstance(value, dict):
        return any(
            _contains_freshness(item)
            for key, item in value.items()
            if not (skip_run and key == "run")
        )
    if isinstance(value, list):
        return any(_contains_freshness(item) for item in value)
    return False


def _contents(job, document):
    permissions = job.get("permissions") if "permissions" in job else document.get("permissions")
    if not isinstance(permissions, dict):
        return None
    value = permissions.get("contents")
    return value.strip() if isinstance(value, str) else None


def _outside_run(filename):
    return (
        f"{filename}: {FRESHNESS} is outside the run script, "
        "so the call is not an authenticated read"
    )


def freshness_problems(filename, text):
    """Problems for one workflow. An empty list means every freshness read is authenticated."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        if FRESHNESS in text:
            return [f"{filename}: could not parse workflow YAML ({exc})"]
        return []
    if not isinstance(document, dict):
        if FRESHNESS in text:
            return [_outside_run(filename)]
        return []
    jobs = document.get("jobs") or {}
    if not isinstance(jobs, dict):
        if FRESHNESS in text:
            return [_outside_run(filename)]
        return []
    problems = []
    workflow_tokens = _token_names(document.get("env"))
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_tokens = _token_names(job.get("env"))
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            script = step.get("run") if isinstance(step.get("run"), str) else ""
            if FRESHNESS not in script:
                if _contains_freshness(step, skip_run=True):
                    problems.append(
                        f"{filename} job {job_name}: {FRESHNESS} is outside the run script, "
                        "so the call is not an authenticated read"
                    )
                continue
            tokens = [*workflow_tokens, *job_tokens, *_token_names(step.get("env"))]
            gh_api = GH_API.search(script) is not None
            direct_http = DIRECT_HTTP.search(script) is not None
            where = f"{filename} job {job_name}"
            if not gh_api and not direct_http:
                problems.append(
                    f"{where}: {FRESHNESS} is called without authentication. "
                    "Pass GH_TOKEN or GITHUB_TOKEN from github.token and use gh api, "
                    "or send Authorization: Bearer."
                )
                continue
            if gh_api and not tokens:
                problems.append(
                    f"{where}: gh api reads {FRESHNESS} without authentication. "
                    "Set GH_TOKEN or GITHUB_TOKEN to ${{ github.token }} in the step env."
                )
            if direct_http and (not tokens or not _sends_bearer(script, tokens)):
                problems.append(
                    f"{where}: {FRESHNESS} is called without authentication. "
                    "Pass GITHUB_TOKEN from github.token in the step env and send "
                    "Authorization: Bearer with that token."
                )
            if _contents(job, document) != "read":
                problems.append(
                    f"{where}: the freshness read must set permissions contents: read. "
                    "That scope is enough; do not grant contents: write."
                )
    return problems


def _workflow_texts():
    return [
        (path.name, path.read_text()) for path in sorted(WORKFLOWS.glob("*.yml")) if path.is_file()
    ]


def test_repository_workflows_authenticate_every_main_freshness_read():
    calls = []
    problems = []
    for name, text in _workflow_texts():
        if FRESHNESS in text:
            calls.append(name)
        problems.extend(freshness_problems(name, text))
    assert problems == [], "\n".join(problems)
    assert calls == ["verify.yml"]
    document = yaml.safe_load((WORKFLOWS / "verify.yml").read_text())
    job = document["jobs"]["deploy-documentation"]
    assert job["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    steps = job["steps"]
    guard = steps[0]
    assert guard["name"] == "Require current main before deploying this run's artifact"
    assert guard["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert guard["env"]["CANDIDATE"] == "${{ github.sha }}"
    assert "gh api repos/Living-Proof-Labs/livingproof-common/git/ref/heads/main" in guard["run"]
    assert 'test "$current" = "$CANDIDATE"' in guard["run"]
    assert "urlopen" not in guard["run"]
    assert steps[1]["uses"].startswith("actions/deploy-pages@")


def test_removing_the_workflow_token_from_the_real_step_fails():
    text = (WORKFLOWS / "verify.yml").read_text()
    stripped = text.replace(
        "          GH_TOKEN: ${{ github.token }}\n          CANDIDATE: ${{ github.sha }}\n",
        "          CANDIDATE: ${{ github.sha }}\n",
        1,
    )
    assert stripped != text
    problems = freshness_problems("verify.yml", stripped)
    assert any("gh api" in problem and "without authentication" in problem for problem in problems)


def test_replacing_the_real_gh_api_read_with_anonymous_urlopen_fails():
    text = (WORKFLOWS / "verify.yml").read_text()
    old = (
        "current=$(gh api repos/Living-Proof-Labs/livingproof-common/"
        "git/ref/heads/main --jq .object.sha)"
    )
    new = (
        'python -c "import urllib.request; urllib.request.urlopen('
        "'https://api.github.com/repos/Living-Proof-Labs/livingproof-common/git/ref/heads/main')\""
    )
    replaced = text.replace(old, new, 1)
    assert replaced != text
    problems = freshness_problems("verify.yml", replaced)
    assert any("without authentication" in problem for problem in problems), problems


def test_unauthenticated_urllib_freshness_read_fails():
    problems = freshness_problems("sample.yml", UNAUTHENTICATED)
    assert any("without authentication" in problem for problem in problems), problems
    assert any("contents: read" in problem for problem in problems), problems
    assert any("contents: write" in problem for problem in problems), problems


def test_token_that_is_not_sent_on_the_request_still_fails():
    problems = freshness_problems("sample.yml", TOKEN_PRESENT_BUT_UNUSED)
    assert any("without authentication" in problem for problem in problems), problems


def test_gh_api_without_a_token_fails():
    problems = freshness_problems("sample.yml", GH_WITHOUT_TOKEN)
    assert any("without authentication" in problem for problem in problems), problems


def test_gh_api_with_gh_token_and_urllib_with_authorization_bearer_pass():
    assert freshness_problems("gh.yml", AUTHENTICATED_GH) == []
    assert freshness_problems("urllib.yml", AUTHENTICATED_URLLIB) == []


def test_contents_write_fails_even_when_the_read_sends_a_token():
    text = AUTHENTICATED_URLLIB.replace("contents: read", "contents: write", 1)
    problems = freshness_problems("sample.yml", text)
    assert any("contents: read" in problem and "contents: write" in problem for problem in problems)


def _run_guard(tmp_path, *, remote_sha, gh_status):
    document = yaml.safe_load((WORKFLOWS / "verify.yml").read_text())
    guard = document["jobs"]["deploy-documentation"]["steps"][0]
    stub = tmp_path / "gh"
    stub.write_text(GH_STUB)
    stub.chmod(0o755)
    capture = tmp_path / "capture.txt"
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", guard["run"]],
        env={
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "GH_TOKEN": "workflow-token",
            "CANDIDATE": EXPECTED_SHA,
            "GH_CAPTURE": str(capture),
            "GH_STATUS": str(gh_status),
            "GH_SHA": remote_sha,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert "workflow-token" not in result.stdout
    assert "workflow-token" not in result.stderr
    recorded = capture.read_text() if capture.is_file() else ""
    assert "workflow-token" not in recorded
    return result, recorded


@pytest.mark.parametrize(
    ("remote_sha", "gh_status", "expected_code"),
    [
        (EXPECTED_SHA, 0, 0),
        ("b" * 40, 0, 1),
        ("", 0, 1),
        (EXPECTED_SHA, 403, None),
    ],
)
def test_deploy_guard_fails_closed_when_main_moved_or_the_read_fails(
    tmp_path, remote_sha, gh_status, expected_code
):
    result, recorded = _run_guard(tmp_path, remote_sha=remote_sha, gh_status=gh_status)
    if expected_code is None:
        assert result.returncode != 0, result.stderr
    else:
        assert result.returncode == expected_code, result.stderr
    assert "git/ref/heads/main" in recorded
    assert "Living-Proof-Labs/livingproof-common" in recorded
