# Living Proof Labs common library

Read and apply [collaboration-guidelines v7.8.2](https://github.com/Living-Proof-Labs/collaboration-guidelines/blob/v7.8.2/AGENTS.md)
and relevant procedures at that exact tag. Resolved adoption commit:
`1470bd46deffd62d6badf568996225e56872258a`.

Local additions: this is an Apache-2.0 library, without a CLI or plugin manager.
Keep consumer identity explicit. Do not inspect caller working directories or
expose unapproved branch names. Use Rivet for GitHub writes. Independent agent
review gates merges; no Aaron review unless requested. No credential or global
settings changes. Run host `task setup` then `task verify`; inside the development
container use `task -t Taskfile.runtime.yml` instead. Retain raw test reports for
30 days and publish individual results even for failing runs.

Documentation previews use the shared 14-day retention. Raw library test reports
retain the existing 30-day window for consumer release diagnosis. Pages deployment is authorized only from verified main; write permissions stay
on the deployment job. The parent owns repository settings and live acceptance.

Current rendered-manual, organization-root and source-directory links are bounded
navigation exceptions to cross-repository version pinning. They do not float
guidance, dependencies, templates, workflows or executable download examples.
The organization root owns vision and the directory; this repository owns only
its library usage, APIs, verification and contributor operations.
