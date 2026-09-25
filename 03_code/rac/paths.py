"""
Where the project lives.

The scripts in this directory were written with the project root hard-coded,
which is fine on the machine that produced the results and useless to anyone
reproducing them. The root is now resolved once, here, in this order:

  1. the MOTCMC_ROOT environment variable, if set;
  2. otherwise, two directories above this file -- `03_code/rac/paths.py`
     puts the root at `../..`, which holds wherever the tree is checked out.

Every other module imports ROOT from here. Nothing else should contain an
absolute path.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("MOTCMC_ROOT")
            or Path(__file__).resolve().parents[2]).resolve()

CODE = ROOT / "03_code"
EXPERIMENTS = ROOT / "04_experiments"
DATA = EXPERIMENTS / "data"
TRACKERS = EXPERIMENTS / "trackers"
WEIGHTS = EXPERIMENTS / "weights"
FIGURES = ROOT / "05_figures"
PAPER = ROOT / "02_paper"


def p(*parts: str) -> str:
    """Path under the project root, as a string (most call sites want str)."""
    return str(ROOT.joinpath(*parts))


if __name__ == "__main__":
    print(ROOT)
