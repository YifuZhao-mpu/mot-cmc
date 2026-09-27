"""
Build the open-source release manifest.

The paper claims that every number in it can be regenerated from the released
code and data. This script produces the artefact that makes that checkable: a
SHA-256 for every released file, grouped by what it is for, plus the exact
commands that regenerate each table and figure.

    python make_release.py            # write 99_artifacts/RELEASE/MANIFEST.sha256 + README
    python make_release.py --check    # verify the manifest against the tree
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import os
import subprocess
import sys

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import ROOT as _R
ROOT = str(_R)
OUT = f"{ROOT}/99_artifacts/RELEASE"

# what goes in the release, and why. Raw benchmark data and model weights are
# NOT redistributed -- they are public at their own addresses and large.
GROUPS = {
    "code — measurement instruments": [
        "03_code/rac/instrumented_gmc.py", "03_code/rac/reference_warp.py",
        "03_code/rac/kitti_egomotion.py", "03_code/rac/rac_tracker.py",
        "03_code/rac/paths.py",
    ],
    "code — experiments": [
        "03_code/rac/scan_mot.py", "03_code/rac/oracle_contrast.py",
        "03_code/rac/gate_flip.py", "03_code/rac/freeze_detections.py",
        "03_code/rac/kitti_freeze_dets.py", "03_code/rac/kitti_warps.py",
        "03_code/rac/kitti_warps_v2.py", "03_code/rac/kitti_warps_v3.py",
        "03_code/rac/kitti_depth_warps.py", "03_code/rac/kitti_track.py",
        "03_code/rac/kitti_warps_anchored.py",
        "03_code/rac/uavdt_track.py", "03_code/rac/run_rac.py",
        "03_code/rac/synthetic_failure_study.py",
    ],
    "code — analysis": [
        "03_code/rac/kitti_parallax_study.py", "03_code/rac/kitti_per_object.py",
        "03_code/rac/kitti_model_class.py", "03_code/rac/kitti_global_family.py",
        "03_code/rac/kitti_global_family_v2.py", "03_code/rac/spread_2d.py",
        "03_code/rac/depth_ratio_scan.py", "03_code/rac/parallax_indicator.py",
        "03_code/rac/runtime_cost.py",
        "03_code/rac/kitti_causal_link.py", "03_code/rac/kitti_class_split.py",
        "03_code/rac/bootstrap_ci.py", "03_code/rac/signal_search.py",
        "03_code/rac/confound_placebo.py", "03_code/rac/analyse_n1.py",
        "03_code/rac/analyse_oracle.py", "03_code/rac/power_gate.py",
        "03_code/rac/build_val_half.py",
    ],
    "code — paper build and verification": [
        "03_code/rac/make_figures.py", "03_code/rac/build_latex.py",
        "03_code/rac/verify_numbers.py", "03_code/rac/make_release.py",
    ],
    "code — shell drivers": [
        "03_code/rac/evaluate.sh", "03_code/rac/evaluate_kitti.sh",
        "03_code/rac/evaluate_uavdt.sh", "03_code/rac/run_power_gate.sh",
    ],
    "measurement data": None,          # filled from 04_experiments/*.csv
    "detection manifests": None,       # filled from detections/**/manifest.json
    "tracker output (TrackEval summaries)": None,
    "figures": None,
    "manuscript": ["02_paper/manuscript.md", "02_paper/latex/manuscript.tex",
                   "02_paper/REPRODUCE.md", "02_paper/supplementary.md"],
}

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect() -> dict[str, list[str]]:
    g = {k: (v[:] if v else []) for k, v in GROUPS.items()}
    g["measurement data"] = sorted(
        f"04_experiments/{f}" for f in os.listdir(f"{ROOT}/04_experiments")
        if f.endswith(".csv"))
    g["detection manifests"] = sorted(
        os.path.relpath(os.path.join(dp, f), ROOT)
        for dp, _, fs in os.walk(f"{ROOT}/04_experiments/detections")
        for f in fs if f == "manifest.json")
    g["tracker output (TrackEval summaries)"] = sorted(
        os.path.relpath(os.path.join(dp, f), ROOT)
        for dp, _, fs in os.walk(f"{ROOT}/04_experiments/trackers")
        for f in fs if f.endswith("_summary.txt") or f.endswith("_detailed.csv"))
    g["figures"] = sorted(
        f"05_figures/{f}" for f in os.listdir(f"{ROOT}/05_figures") if f.endswith(".pdf"))
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    groups = collect()

    if a.check:
        bad, n = [], 0
        for line in open(f"{OUT}/MANIFEST.sha256"):
            if not line.strip() or line.startswith("#"):
                continue
            digest, rel = line.split(None, 1)
            rel = rel.strip()
            n += 1
            p = os.path.join(ROOT, rel)
            if not os.path.exists(p):
                bad.append(f"MISSING  {rel}")
            elif sha256(p) != digest:
                bad.append(f"CHANGED  {rel}")
        print(f"checked {n} files; {len(bad)} problems")
        for b in bad:
            print("  ", b)
        sys.exit(1 if bad else 0)

    os.makedirs(OUT, exist_ok=True)
    lines, total, missing = [], 0, []
    for name, files in groups.items():
        lines.append(f"\n# {name}  ({len(files)} files)")
        for rel in files:
            p = os.path.join(ROOT, rel)
            if not os.path.exists(p):
                missing.append(rel)
                continue
            lines.append(f"{sha256(p)}  {rel}")
            total += 1
    header = ["# mot-cmc release manifest",
              "# verify with:  python 03_code/rac/make_release.py --check",
              f"# {total} files"]
    open(f"{OUT}/MANIFEST.sha256", "w").write("\n".join(header + lines) + "\n")

    # REPRODUCE.md is a maintained document, not a generated one: it had been
    # generated from a list in this file, and that list went stale across two
    # table renumberings without anything noticing. It now lives beside the
    # manuscript and verify_numbers.py checks that it maps every table the
    # manuscript prints and names no script, flag or --mode that does not exist.
    src = f"{ROOT}/02_paper/REPRODUCE.md"
    if not os.path.exists(src):
        raise SystemExit(f"missing {src}: the release page is maintained, not generated")
    shutil.copyfile(src, f"{OUT}/REPRODUCE.md")

    print(f"{total} files hashed -> {OUT}/MANIFEST.sha256")
    for name, files in groups.items():
        present = sum(os.path.exists(os.path.join(ROOT, f)) for f in files)
        print(f"  {name:42s} {present:5d}")
    if missing:
        print(f"\nlisted but not present ({len(missing)}):")
        for m in missing:
            print("  ", m)


if __name__ == "__main__":
    main()
