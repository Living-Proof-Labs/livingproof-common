# Common library manual publication

Target: `https://docs.livingprooflabs.com/livingproof-common/`. No project CNAME,
custom domain, DNS or mail change is needed or authorized here.

Scoped approval covers main-only deployment. The deployment job has
`contents: read`, `pages: write`, and `id-token: write`. The main-freshness
read calls `gh api` with `GH_TOKEN: ${{ github.token }}`. `contents: read`
is enough, and the job does not get `contents: write`. Documentation builds
and pull requests use `contents: read`. The parent browser worker owns settings:

- Enable this repository's Pages source as GitHub Actions (`build_type: workflow`).
- Configure the `github-pages` environment to permit deployments from `main` only.
- Leave repository-wide token defaults, domains and other settings unchanged.

The release writer waits for the library matrix and the sealed candidate
manual's browser tests. The deployment renders and tests the manual anew using
the exact checkout and the matching wheel downloaded from the immutable
published release. The Pages job verifies the final archive by both same-run
artifact ID and attempt-qualified name. A read-only `gh api` check,
authenticated with the workflow token, compares that commit to current `main`
inside the deployment lock, immediately before publication. The job fails
closed if any of these checks fail. A branch can still advance after the final
check, so the successful deployment must be verified live.

For Pages delivery only, use the same workflow on `main` with its existing
published stable tag. This route does not create a tag or rebuild, edit, or
republish release assets.

A successful artifact upload is not a verified live manual. Record the deployed
revision/run/URL and exercise navigation, search and result opening, themes,
assets, a deep link and related manual links before declaring adoption complete.
Replace the README's temporary source-documentation link only after that evidence.
