"""Thin wrapper to expose ``src/project_watch`` during testing."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parent.parent / "src" / "project_watch"
if str(SRC_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SRC_PATH.parent))

_spec = spec_from_file_location("project_watch_real", SRC_PATH / "__init__.py")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore

__all__ = getattr(_module, "__all__", [])
__doc__ = _module.__doc__
__path__ = [str(SRC_PATH)]

for name, value in _module.__dict__.items():
    if not name.startswith("_"):
        globals()[name] = value
