"""
SIH 26124 — Backend Package Root
Bootstraps sys.path so that 'app' and 'ai' packages resolve cleanly whether
the application is executed from the repository root or the backend/ directory.
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

_repo_root = _backend_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
