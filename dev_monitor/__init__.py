"""Thin wrapper to expose the implementation in ``src/dev_monitor``.

The test suite imports ``dev_monitor`` directly. When the package has not been
installed this small shim adjusts ``sys.path`` so that modules under the
``src`` layout can be resolved transparently.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parent.parent / "src" / "dev_monitor"
if str(SRC_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SRC_PATH.parent))

_spec = spec_from_file_location("dev_monitor_real", SRC_PATH / "__init__.py")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore

__all__ = getattr(_module, "__all__", [])
__doc__ = _module.__doc__
__path__ = [str(SRC_PATH)]

for name, value in _module.__dict__.items():
    if not name.startswith("_"):
        globals()[name] = value
