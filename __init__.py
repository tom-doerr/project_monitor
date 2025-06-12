# Ensure the project modules in the ``src`` directory are importable when the
# package is used without being installed.  The tests import ``dev_monitor`` and
# ``project_watch`` directly, so the ``src`` directory needs to be on
# ``sys.path``.
from pathlib import Path
import sys

# Compute the absolute path to the ``src`` directory relative to this file and
# add it to ``sys.path`` if it is not already present.
SRC_PATH = str(Path(__file__).resolve().parent / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
