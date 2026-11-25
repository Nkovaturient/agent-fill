import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    return _REPO_ROOT


def ensure_scripts_on_path() -> Path:
    scripts = _REPO_ROOT / "scripts"
    scripts_str = str(scripts)
    if scripts.is_dir() and scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)
    return scripts