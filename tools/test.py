"""Keep the original test failure while still generating available coverage."""
import subprocess
import sys

result = subprocess.run([sys.executable, '-m', 'coverage', 'run',
                         '--source=livingproof_common', '-m', 'pytest',
                         '--junitxml=artifacts/tests.xml',
                         '--scenario-report=artifacts/scenarios.json'])
coverage = subprocess.run([sys.executable, '-m', 'coverage', 'html', '-d', 'artifacts/coverage'])
raise SystemExit(result.returncode or coverage.returncode)
