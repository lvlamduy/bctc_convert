from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from bctc_ai.cli.main import main

    main(["--project-root", str(ROOT), "audit"])
