#!/bin/sh
# Linux host checks: Docker only, no host Python or nested Docker.
set -eu
probe='from importlib.metadata import distribution; from pathlib import Path; import livingproof_common; from livingproof_common.versioning import Consumer,current_version; d=distribution("livingproof-common"); assert not d.entry_points; v=current_version(Consumer("livingproof-common",Path(livingproof_common.__file__).parent)); assert v[2]=="recorded-build",v; print(v)'
docker run --rm --network=none -v "$PWD/dist:/packages:ro" python:3.12.12-slim-bookworm sh -ec 'pip install --no-index /packages/*.whl && python -c "$1"' sh "$probe"
for image in debian:12-slim ubuntu:24.04; do
  docker run --rm -v "$PWD/dist:/packages:ro" "$image" sh -ec 'apt-get update -qq && apt-get install -y /packages/*.deb && python3 -c "$1"' sh "$probe"
done
