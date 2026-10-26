Living Proof Labs common library
================================

This package supplies shared Python libraries. It has no command-line entry point
and does not discover or manage plugins.

Consumer identity
-----------------

Pass the consumer distribution and its own package directory explicitly. A source
checkout uses only its direct ``root/src/package`` repository; installed wheels
use their recorded build snapshot. Never pass the common library directory when
asking for another tool's identity.

Clean release tags display X.Y.Z. Development displays identify release base,
commits since release, bounded public branch slug, commit and clean/dirty state.
Private or unverified local branch names become ``local`` or ``detached``.
Shallow, empty and unavailable history are explicit. Snapshots identify builds;
they are not signatures or proof of trusted origin. Dirty snapshots record state,
not a digest of uncommitted bytes. Two dirty builds can share an identifier.

Package versions remain the build backend's PEP 440 metadata. Use Hatch-VCS with
``local_scheme = "no-local-version"`` to avoid clock-dependent dirty suffixes.
No runtime dependency on Hatch, setuptools-scm, Click or either consumer exists.

API reference
-------------

.. automodule:: livingproof_common.versioning
   :members: Consumer, current_version, source_identity, display, build_provenance, record_build, read_provenance

Contributor tasks
-----------------

.. include:: tasks.rst

Software test coverage
----------------------

The retained ``coverage`` artifact is measured software test coverage. It does
not measure robot capability, safety or evidence sufficiency.
