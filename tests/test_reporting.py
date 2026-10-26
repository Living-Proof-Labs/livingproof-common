"""Opt-in fixture proves hosted failing tests retain their failure status."""
import os


def test_reporting_failure_fixture():
    assert os.environ.get("REPORTING_FAILURE_FIXTURE") != "1", "Deliberate reporting fixture"
