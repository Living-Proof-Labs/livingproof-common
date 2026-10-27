# Living Proof Labs common library

Read and apply [collaboration-guidelines v5.0.0](https://github.com/Living-Proof-Labs/collaboration-guidelines/blob/v5.0.0/AGENTS.md)
and relevant procedures at that exact tag. Resolved adoption commit:
`dd4b0391a9a66fa7944f6655aac57c67d3f8c002`.

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
