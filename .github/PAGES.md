# Common library manual publication

Target: `https://docs.livingprooflabs.com/livingproof-common/`. No project CNAME,
custom domain, DNS or mail change is needed or authorized here.

Scoped approval covers main-only deployment and `pages: write` plus
`id-token: write` only in the separate deployment job. Documentation builds and
pull requests use `contents: read`. The parent browser worker owns settings:

- Enable this repository's Pages source as GitHub Actions (`build_type: workflow`).
- Configure the `github-pages` environment to permit deployments from `main` only.
- Leave repository-wide token defaults, domains and other settings unchanged.

The deployment consumes only this run's verified public HTML, after the library
matrix and browser verification pass. A read-only GitHub API check compares the
candidate commit to current `main` immediately before deploying. Concurrency
cancels obsolete deployments. No project checkout or code execution happens in
the deployment job. These safeguards reduce stale publication; a branch can still
advance after the freshness check, so the newest successful deployment must be
verified live.

A successful artifact upload is not a verified live manual. Record the deployed
revision/run/URL and exercise navigation, search and result opening, themes,
assets, a deep link and related manual links before declaring adoption complete.
Replace the README's temporary source-documentation link only after that evidence.
