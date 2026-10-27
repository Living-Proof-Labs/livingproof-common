# Verification and preview evidence

## Initial inventory and bounded adoption

The initial repository had a Sphinx page, README usage examples, Git identity
regressions, wheel/source-archive tests and two installed fixture consumers.
It had no Markdown-rendered manual, explicit scenario inventory, browser checks,
or Pages deployment. Raw tests already published individual JUnit cases.

This adoption uses [collaboration-guidelines v5.0.0](https://github.com/Living-Proof-Labs/collaboration-guidelines/tree/v5.0.0).
It follows the [feature verification standard](https://github.com/Living-Proof-Labs/collaboration-guidelines/blob/v5.0.0/docs/developer-interface.md#observable-behavior-and-feature-coverage)
and [manual standard](https://github.com/Living-Proof-Labs/collaboration-guidelines/blob/v5.0.0/docs/tool-usability.md).
Zensical 0.0.73 follows the [reviewed root adoption](https://github.com/Living-Proof-Labs/livingproof/pull/16).
Repository Markdown is staged from an explicit allowlist. API signatures and
docstrings come from an installed candidate wheel, tasks from Task, and scenarios
from executed pytest cases. No product CLI, simulator or runtime behavior is added.

Five named scenarios cover seven collected cases: release/development identity,
three dirty-state forms, branch privacy, installed/source-archive provenance,
and two distinct installed consumers. Other existing regressions remain ordinary
pytest cases. These scenarios do not claim exhaustive feature coverage. Software
line coverage is a separate measured report, not robot capability or safety.

## Reproduce

```sh
task setup
task verify
task docs:test
```

Inside the prepared environment, use `task -t Taskfile.runtime.yml` for the same
task names. Browser setup is separate: `task -t Taskfile.runtime.yml docs:setup`
installs the locked test dependency and matching Chromium. The repository's
`documentation-test` Docker target supplies browser system libraries for CI.

Download `common-manual-ubuntu-24.04` from the candidate workflow run; previews,
browser results and screenshots expire after **14 days**. Extract the archive,
serve its parent over loopback HTTP, and visit `/docs/html/index.html`:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

CI publishes individual library and browser JUnit cases in the job summary.
Build jobs use read-only tokens; dedicated Checks API publication is replaced by
individual cases in Actions summaries for both trusted branches and restricted forks. Raw library results/coverage retain the
existing 30-day diagnostic window; this is a local exception to the 14-day default.
Tests fail the job even if report generation or publication succeeds.

`artifacts/scenarios.json` records passed, failed, skipped and untested collected
cases. The generator rejects absent inventory or stale source. The manual links
these observed results and its exact commit, wheel digest and workflow run.
A deliberately failing `ci/reporting-failure` branch exercises failure reporting;
never interpret that fixture as a passing product run.

## Review limits and activation

Linux amd64 and arm64 remain library CI targets. Browser checks run Chromium on
Linux amd64, including mobile emulation; this does not establish real mobile,
Firefox, Safari, macOS or Windows behavior. Local checks validate assets, anchors,
search/opening a result, navigation, themes and version context under the project
base path. External links are checked separately.

Independent installed-product review and live Pages verification remain required.
After deployment, check the exact source commit, navigation, deep links, search,
theme switching and related manuals from the public URL before changing the README
start-here link to the rendered manual or adding it to the documentation directory.
The parent owns that directory update and repository Pages settings.
