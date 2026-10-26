"""Generate Task reference from this reviewed repository and Sphinx API docs."""
import json
import os
from pathlib import Path
import subprocess
import sys

from links import check_links

root = Path(__file__).resolve().parents[1]
env = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
       "SOURCE_DATE_EPOCH": "0", "PYTHONHASHSEED": "0", "NO_COLOR": "1"}
tasks = json.loads(subprocess.check_output(
    ["task", "-t", "Taskfile.runtime.yml", "--list", "--json"], cwd=root, env=env, text=True))
lines = []
for task in tasks["tasks"]:
    lines.extend([f"``{task['name']}``", f"   {task['desc']}", ""])
(root / "docs/tasks.rst").write_text("\n".join(lines))
subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-b", "html",
                "docs", "artifacts/docs"], cwd=root, env=env, check=True)

check_links(root / "artifacts/docs")
