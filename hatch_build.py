"""Bootstrap this library's own build; consumers import the released library."""
import importlib.util
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        spec = importlib.util.spec_from_file_location(
            "common_build_versioning", root / "src/livingproof_common/versioning.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        consumer = module.Consumer("livingproof-common", root / "src/livingproof_common")
        artifact = module.record_build(root, self.metadata.version, consumer)
        build_data.setdefault("artifacts", []).append(artifact)
