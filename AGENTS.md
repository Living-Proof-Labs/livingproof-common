# Living Proof Labs common library

Read and apply [collaboration-guidelines v4.2.1](https://github.com/Living-Proof-Labs/collaboration-guidelines/blob/v4.2.1/AGENTS.md)
and relevant procedures at that exact tag. Resolved adoption commit:
`12861dc824d934fbd53814f05ded85761b63c6ec`.

Local additions: this is an Apache-2.0 library, without a CLI or plugin manager.
Keep consumer identity explicit. Do not inspect caller working directories or
expose unapproved branch names. Use Rivet for GitHub writes. Independent agent
review gates merges; no Aaron review unless requested. No credential or global
settings changes. Run host `task setup` then `task verify`; inside the development
container use `task -t Taskfile.runtime.yml` instead. Retain raw test reports for
30 days and publish individual results even for failing runs.
