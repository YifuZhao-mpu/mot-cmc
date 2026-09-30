"""Assemble the whole project into one self-sufficient folder.

The repository is the canonical tree, but it is 67 GB on disk (benchmark images,
model weights, vendored third-party trees, raw per-frame tracker output) and it
excludes the built PDF and the submission package. This writes a folder that holds
everything the project itself produced, in the same layout -- the layout matters,
because `paths.py` and the release manifest resolve against it -- and then proves
the folder stands on its own by running both checkers inside it.

    python rac/make_bundle.py [--out DIR]

Refuses to finish if either checker fails, so a bundle that exists is a bundle
that verified. Counts printed into the guide are computed here, never typed.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rac.paths import p  # noqa: E402

ROOT = p("")
# Built or curated artefacts the repository deliberately does not track, but which
# a handover folder must contain.
EXTRA = [
    "99_artifacts/SUBMISSION",
    "02_paper/latex/manuscript.tex",
    "02_paper/latex/manuscript.pdf",
    "02_paper/latex/figs",
]


# Everything the repository deliberately does not track, but which a complete
# working copy needs: the benchmarks themselves, the model weights, the raw
# per-frame tracker output, the warp bundles and the vendored source trees.
HEAVY = [
    ("datasets", ["04_experiments/data"]),
    ("model weights", ["04_experiments/weights", "03_code/yolo11x.pt"]),
    ("raw experiment output", ["04_experiments/trackers", "04_experiments/detections",
                               "04_experiments/eval", "04_experiments/rac_logs",
                               "04_experiments/oracle"]),
    ("warp bundles", ["04_experiments"]),          # kitti_warps*/ and ref_warps*/
    ("third-party source", ["03_code/BoT-SORT", "03_code/ByteTrack",
                            "03_code/TrackEval", "03_code/Depth-Anything-V2"]),
]
WARP_GLOBS = ("kitti_warps*", "ref_warps*")


def _link_or_copy(src: str, dst: str) -> tuple[int, int, int]:
    """Mirror a tree, hard-linking where the filesystem allows it.

    The benchmarks alone are 64 GB. On one filesystem a hard link makes the file
    appear in both trees at no cost in space or time; a copy is used only when the
    link cannot be made. Either way the folder holds real files, and copying the
    folder elsewhere expands them.
    """
    linked = copied = nbytes = 0
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        out = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(out, exist_ok=True)
        for f in files:
            a, b = os.path.join(root, f), os.path.join(out, f)
            if os.path.exists(b):
                continue
            try:
                os.link(a, b)
                linked += 1
            except OSError:
                shutil.copy2(a, b)
                copied += 1
            nbytes += os.path.getsize(a)
    return linked, copied, nbytes


def add_heavy(dst: str) -> None:
    """Add the datasets, the weights and every experiment artefact to the bundle."""
    import glob as _glob
    for what, rels in HEAVY:
        linked = copied = nbytes = 0
        targets = []
        for rel in rels:
            src = os.path.join(ROOT, rel)
            if what == "warp bundles":
                for g in WARP_GLOBS:
                    targets += [os.path.relpath(x, ROOT)
                                for x in _glob.glob(os.path.join(src, g))]
            elif os.path.exists(src):
                targets.append(rel)
        for rel in targets:
            src = os.path.join(ROOT, rel)
            if os.path.isdir(src):
                l, c, n = _link_or_copy(src, os.path.join(dst, rel))
            else:
                os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
                try:
                    os.link(src, os.path.join(dst, rel)); l, c = 1, 0
                except OSError:
                    shutil.copy2(src, os.path.join(dst, rel)); l, c = 0, 1
                n = os.path.getsize(src)
            linked += l; copied += c; nbytes += n
        if targets:
            print(f"  {what:24s} {linked + copied:7d} files, {nbytes / 2**30:7.2f} GB"
                  f"  ({linked} linked, {copied} copied)")


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"],
                         capture_output=True, text=True, check=True).stdout
    return [f for f in out.split("\0") if f]


def copy_into(dst: str) -> int:
    n = 0
    for rel in tracked():
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        dest = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        n += 1
    for rel in EXTRA:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            print(f"  note: {rel} is absent and was not copied")
            continue
        dest = os.path.join(dst, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)
            n += sum(len(f) for _, _, f in os.walk(src))
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            n += 1
    return n


def _human(n: int) -> str:
    return f"{n / 2**30:.1f} GB" if n >= 2**30 else f"{round(n / 2**20)} MB"


def counts(dst: str) -> dict:
    def n(pat, **kw):
        return len(glob.glob(os.path.join(dst, pat), **kw))

    runs = {}
    for bench in ("KITTI", "MOT17-val-half", "UAVDT"):
        runs[bench] = len({os.path.dirname(f) for f in glob.glob(
            os.path.join(dst, f"04_experiments/trackers/{bench}/**/*_summary.txt"),
            recursive=True)})
    manifest = os.path.join(dst, "99_artifacts/RELEASE/MANIFEST.sha256")
    # a manifest line is a hash entry only if it is 64 hex plus two spaces plus a
    # path; the file also carries group comments and blank separators
    hashed = sum(1 for L in open(manifest)
                 if len(L.split("  ", 1)) == 2 and len(L.split("  ", 1)[0]) == 64) \
        if os.path.exists(manifest) else 0
    return dict(
        files=sum(len(f) for _, _, f in os.walk(dst)),
        size=_human(sum(os.path.getsize(os.path.join(r, f))
                        for r, _, fs in os.walk(dst) for f in fs)),
        scripts=n("03_code/rac/*.py") + n("03_code/rac/*.sh"),
        csvs=n("04_experiments/*.csv"),
        figures=n("05_figures/*.pdf"),
        tables=sum(1 for L in open(os.path.join(dst, "02_paper/manuscript.md"))
                   if L.startswith("**Table ")),
        runs_total=sum(runs.values()), hashed=hashed, **runs)


def verify(dst: str) -> bool:
    ok = True
    env = dict(os.environ, MOTCMC_ROOT=os.path.abspath(dst),
               PYTHONPATH=os.path.join(os.path.abspath(dst), "03_code"))
    code = os.path.join(dst, "03_code")
    for script, what in (("rac/verify_numbers.py", "the paper's numbers"),
                         ("rac/make_release.py --check", "the release manifest")):
        r = subprocess.run([sys.executable] + script.split(), cwd=code, env=env,
                           capture_output=True, text=True)
        lines = [L.strip() for L in r.stdout.splitlines() if L.strip()]
        # On failure the useful lines are the ones naming the problems, not the
        # trailing note; on success, the count.
        if r.returncode == 0:
            note = next((L for L in lines if "problems" in L or "0 problems" in L), lines[-1] if lines else "")
        else:
            bad = [L for L in lines if L.split(" ")[0] in
                   ("MISMATCH", "PROVENANCE", "COVERAGE", "PARSE", "MISSING",
                    "UNRESOLVED", "CLAIM", "CHANGED", "ERROR")]
            note = "; ".join(bad[:3]) or (r.stderr.strip().splitlines() or [""])[-1] or "see output"
        print(f"  {what}: {'OK' if r.returncode == 0 else 'FAILED'} -- {note}")
        ok = ok and r.returncode == 0
    return ok


NO_DATA_NOTE = """## What is deliberately not here

See `EXCLUDED.md`: the benchmark images, the model weights, the vendored
third-party trees and the raw per-frame tracker output. Nothing in the paper needs
them to be *checked* -- only to be *reproduced from scratch*. Rebuild with
`--with-data` to bring them in.

"""

WITH_DATA_NOTE = """## This copy includes the datasets

Built with `--with-data`, so it also holds the MOT17, MOT20, UAVDT and KITTI
benchmarks, the model weights, the raw per-frame tracker output, every warp bundle
and the four vendored third-party source trees. `CONTENTS.md` lists them.

**Do not publish or redistribute this copy.** The benchmarks, the weights and the
third-party trees are other people's, under their own licences, and this project
releases none of them; `99_artifacts/RELEASE/DATA.md` records where each one comes
from. The folder to share is the one built *without* `--with-data`, which is what
the public repository and the archived release contain.

"""

WITH_DATA = """# What this copy contains

Built with `python rac/make_bundle.py --with-data`, which adds to the project's own
output everything needed to rerun it from the images up.

| Part | What it is |
|---|---|
| `04_experiments/data/` | MOT17, MOT20, UAVDT and KITTI, as downloaded, with the SHA-256 of the two archives |
| `04_experiments/weights/`, `03_code/yolo11x.pt` | the YOLOX-X ablation weights, YOLO11x, the FastReID model and the Depth-Anything-V2 metric checkpoint |
| `04_experiments/trackers/*/*/data/` | raw per-frame tracker output for every evaluated run |
| `04_experiments/kitti_warps*/`, `ref_warps*/` | every warp bundle, including the depth-noise sweeps |
| `04_experiments/detections/`, `eval/`, `rac_logs/`, `oracle/` | frozen detections, TrackEval working directories and run logs |
| `03_code/BoT-SORT`, `ByteTrack`, `TrackEval`, `Depth-Anything-V2` | the source trees the experiments import, patched only for modern NumPy and PyTorch |

Most of these files are **hard links** to the working copy they were taken from:
they are real files and read exactly like files, they cost no extra disk while both
folders are on the same filesystem, and copying this folder anywhere else expands
them into independent copies.

**None of it is ours to redistribute.** The benchmarks, the weights and the
third-party trees carry their own licences; see `99_artifacts/RELEASE/DATA.md` for
where each came from and which SHA-256 we used. This copy is for working and
archiving, not for sharing. The shareable copy is the one built without
`--with-data`, and is what the public repository and the archived release contain.
"""


GUIDE = """# Project guide

Everything this project produced, in one folder. Assembled by
`03_code/rac/make_bundle.py`, which refuses to finish unless both checkers below
pass inside the folder -- so this folder existing means it verified.

**Paper**: *Camera-Motion Compensation Is Not the Bottleneck: A Measurement Study
of Shared Warps in Tracking-by-Detection* · target venue *International Journal of
Computer Vision* · {tables} tables, {figures} figures.

**Contents**: {files} files, {size}. {scripts} scripts, {csvs} result CSVs,
TrackEval output for {runs_total} evaluated tracker runs ({KITTI} on KITTI,
{MOT17-val-half} on MOT17, {UAVDT} on UAVDT), {hashed} files hashed in the manifest.

## Start here

| If you want to | Open |
|---|---|
| read the paper | `02_paper/latex/manuscript.pdf`, or `02_paper/manuscript.md` for the source |
| upload to the journal | `99_artifacts/SUBMISSION/` -- PDF, LaTeX, class, figures, cover letter, checklist, author metadata |
| check that the paper's numbers are real | `cd 03_code && python rac/verify_numbers.py` |
| rerun one measurement | `99_artifacts/RELEASE/REPRODUCE.md` maps every table and figure to its command |
| know what data is needed, and where to get it | `99_artifacts/RELEASE/DATA.md`; {datarow} |
| see how the conclusions changed, and why | `00_pipeline/state.md`, then `02_paper/supplementary.md` S2 |
| read it in Chinese | `02_paper/03_ABSTRACT_ZH.md` |

## Layout

| Folder | What is in it |
|---|---|
| `00_pipeline/` | the running record: every finding and every self-correction, in order |
| `01_research/` | literature search scripts and logs, the methodology blueprint, two devil's-advocate reviews |
| `02_paper/` | the manuscript in Markdown, the generated LaTeX and PDF, supplementary material, cover letter, Chinese abstract, and nine numbered process records |
| `03_code/rac/` | every measurement, analysis and build script. `verify_numbers.py` is the one that matters |
| `04_experiments/` | the measurement data: result CSVs, detection manifests with per-file SHA-256, TrackEval output for every evaluated run, and the two warp bundles the provenance checks read |
| `05_figures/` | the figures as PDF and PNG |
| `99_artifacts/RELEASE/` | the manifest, the reproduction map, and what is not redistributed |
| `99_artifacts/SUBMISSION/` | the package to upload, with its checklist and author metadata |

## Verified self-sufficient

Run inside this folder before it was handed over:

```bash
cd 03_code
MOTCMC_ROOT=.. python rac/verify_numbers.py       # the paper's numbers and provenance
MOTCMC_ROOT=.. python rac/make_release.py --check  # {hashed} files, by SHA-256
```

`verify_numbers.py` parses the manuscript's own tables and confidence intervals and
recomputes each from the data in this folder, so the paper cannot drift from its
evidence. It also checks provenance: whether a compared configuration is silently
switched off, which run backs which table, whether the reproduction map still names
only commands that exist, and whether the counts the paper gives about its own
release are true.

Scripts locate the project root themselves (`03_code/rac/paths.py`), from
`MOTCMC_ROOT` if set and otherwise from their own location, so this folder can be
moved or renamed freely.

{extra}
## Status

| Item | State |
|---|---|
| Author list | final, seven authors: Zhao, Zou, Li (Yanxiao), Wei, Im, Wang (corresponding), Yang |
| CRediT contributions | supplied and set |
| Funding, ethics, AI-disclosure, competing interests | present |
| Repository | <https://github.com/YifuZhao-mpu/mot-cmc> |
| Archived DOI | outstanding -- enable the repository in Zenodo, publish a release, then replace the placeholder in the Data and Code Availability statement |
| Suggested reviewers | outstanding -- the cover letter leaves the list to the authors |
| Single- vs two-column | outstanding -- the build is two-column; one flag in `build_latex.py` switches it |
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(ROOT.rstrip("/")),
                                                  "mot-cmc-complete"))
    ap.add_argument("--with-data", action="store_true",
                    help="also bring in the benchmarks, the model weights, the raw "
                         "per-frame tracker output, the warp bundles and the vendored "
                         "source trees -- about 67 GB, hard-linked where possible")
    a = ap.parse_args()
    dst = os.path.abspath(a.out)
    if os.path.abspath(ROOT.rstrip("/")) == dst:
        raise SystemExit("--out must not be the project itself")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    print(f"assembling -> {dst}")
    print(f"  copied {copy_into(dst)} files")
    if a.with_data:
        add_heavy(dst)
    c = counts(dst)
    if a.with_data:
        # EXCLUDED.md would be describing files that are now present
        with open(os.path.join(dst, "CONTENTS.md"), "w") as f:
            f.write(WITH_DATA)
        stale = os.path.join(dst, "EXCLUDED.md")
        if os.path.exists(stale):
            os.remove(stale)      # it lists files that are now present
        c["extra"] = WITH_DATA_NOTE
        c["datarow"] = "`CONTENTS.md` for what this copy holds"
    else:
        shutil.copy2(os.path.join(ROOT, "EXCLUDED.md"), os.path.join(dst, "EXCLUDED.md"))
        c["extra"] = NO_DATA_NOTE
        c["datarow"] = "`EXCLUDED.md` for what is not here"
    with open(os.path.join(dst, "PROJECT_GUIDE.md"), "w") as f:
        f.write(GUIDE.format(**c))
    print(f"  {c['files']} files, {c['size']}, {c['runs_total']} evaluated runs")
    print("verifying inside the bundle:")
    if not verify(dst):
        raise SystemExit("bundle did not verify; not handing it over")
    print(f"\nbundle verified -> {dst}")


if __name__ == "__main__":
    main()
