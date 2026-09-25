"""
Run the detector ONCE and freeze its output to disk.

METHODOLOGY_BLUEPRINT §3.1 requires every compared configuration to consume
byte-identical detections. The most robust way to guarantee that is not to
promise it -- it is to run the detector a single time, hash the result, and have
every tracker variant read the same file.

Reproduces BoT-SORT tools/track.py exactly:
  * same Predictor (yolox preproc with rgb_means/std, test_size from the exp)
  * same postprocess (exp.test_conf, exp.nmsthre, num_classes)
  * same rescale: scale = min(test_h/height, test_w/width); boxes /= scale
  * same ablation split: files[len(files)//2 + 1:], frame ids from 1

Output: one .npz per sequence holding a single concatenated float32 array
        [frame_id, x1, y1, x2, y2, obj_conf, cls_conf, cls] plus a manifest with
        the SHA-256 of every file, the checkpoint hash and the exact settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import cv2
import numpy as np
import torch
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

BOT = p("03_code/BoT-SORT")
sys.path.insert(0, BOT)

from yolox.data.data_augment import preproc  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import fuse_model, postprocess  # noqa: E402

RGB_MEANS = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)

# Per-sequence overrides from tools/track.py --default-parameters
TRACK_HIGH = {"MOT17-01-FRCNN": 0.65, "MOT17-06-FRCNN": 0.65,
              "MOT17-12-FRCNN": 0.70, "MOT17-14-FRCNN": 0.67}
TRACK_BUFFER = {"MOT17-05-FRCNN": 14, "MOT17-06-FRCNN": 14,
                "MOT17-13-FRCNN": 25, "MOT17-14-FRCNN": 25}


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def build_model(exp, ckpt: str, device, fp16: bool, fuse: bool):
    model = exp.get_model().to(device)
    model.eval()
    sd = torch.load(ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(sd["model"])
    if fuse:
        model = fuse_model(model)
    if fp16:
        model = model.half()
    return model


@torch.no_grad()
def detect_sequence(model, exp, seq_dir: str, device, fp16: bool,
                    ablation: bool) -> np.ndarray:
    img_dir = os.path.join(seq_dir, "img1")
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png")))
    if ablation:                      # tools/track.py:151-152
        files = files[len(files) // 2 + 1:]

    rows = []
    for frame_id, fn in enumerate(files, start=1):
        img = cv2.imread(os.path.join(img_dir, fn))
        h, w = img.shape[:2]
        inp, _ = preproc(img, exp.test_size, RGB_MEANS, STD)
        t = torch.from_numpy(inp).unsqueeze(0).float().to(device)
        if fp16:
            t = t.half()
        out = model(t)
        out = postprocess(out, exp.num_classes, exp.test_conf, exp.nmsthre)
        if out[0] is None:
            continue
        o = out[0].cpu().numpy()
        scale = min(exp.test_size[0] / float(h), exp.test_size[1] / float(w))
        o[:, :4] /= scale
        fid = np.full((len(o), 1), frame_id, np.float32)
        rows.append(np.concatenate([fid, o[:, :7].astype(np.float32)], axis=1))
    return np.concatenate(rows, 0) if rows else np.zeros((0, 8), np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=p("04_experiments/data/MOT17/train"))
    ap.add_argument("--out", default=p("04_experiments/detections/MOT17-val-half"))
    ap.add_argument("--exp-file", default=f"{BOT}/yolox/exps/example/mot/yolox_x_ablation.py")
    ap.add_argument("--ckpt", default=p("04_experiments/weights/bytetrack_ablation.pth.tar"))
    ap.add_argument("--filter", default="FRCNN")
    ap.add_argument("--ablation", action="store_true", default=True)
    ap.add_argument("--fp16", action="store_true", default=False,
                    help="BoT-SORT's published command uses --fp16; fp32 is more reproducible")
    ap.add_argument("--fuse", action="store_true", default=False)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    exp = get_exp(a.exp_file, None)
    exp.test_conf = max(0.001, 0.1 - 0.01)      # tools/track.py: track_low_thresh - 0.01
    model = build_model(exp, a.ckpt, device, a.fp16, a.fuse)

    seqs = sorted(d for d in os.listdir(a.data_root)
                  if os.path.isdir(os.path.join(a.data_root, d, "img1")) and a.filter in d)

    manifest = dict(
        created="2026-09-20", exp_file=a.exp_file, ckpt=a.ckpt,
        ckpt_sha256=sha256_file(a.ckpt),
        test_size=list(exp.test_size), test_conf=float(exp.test_conf),
        nmsthre=float(exp.nmsthre), num_classes=int(exp.num_classes),
        fp16=bool(a.fp16), fuse=bool(a.fuse), ablation=bool(a.ablation),
        torch=torch.__version__, cuda=torch.version.cuda,
        gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        sequences={},
    )

    for s in seqs:
        t0 = time.time()
        det = detect_sequence(model, exp, os.path.join(a.data_root, s),
                              device, a.fp16, a.ablation)
        p = os.path.join(a.out, f"{s}.npz")
        np.savez_compressed(p, det=det)
        manifest["sequences"][s] = dict(
            n_frames=int(det[:, 0].max()) if len(det) else 0,
            n_detections=int(len(det)), sha256=sha256_file(p),
            seconds=round(time.time() - t0, 1),
            track_high_thresh=TRACK_HIGH.get(s, 0.6),
            track_buffer=TRACK_BUFFER.get(s, 30),
        )
        print(f"  {s:22s} {len(det):7d} dets  {time.time()-t0:6.1f}s", flush=True)

    mp = os.path.join(a.out, "manifest.json")
    json.dump(manifest, open(mp, "w"), indent=1)
    print(f"\nmanifest -> {mp}")
    print(f"detector ckpt sha256: {manifest['ckpt_sha256'][:32]}...")


if __name__ == "__main__":
    main()
