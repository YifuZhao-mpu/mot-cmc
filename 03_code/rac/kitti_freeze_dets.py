"""
Freeze COCO-pretrained detections on KITTI tracking.

Detector choice matters for the integrity of the comparison:

  * A COCO-pretrained model has **never seen KITTI**, so there is no train/val
    leakage and all 21 training sequences can be evaluated. No split is needed
    and none is invented.
  * Running it once and hashing the output makes the fixed-detection discipline
    structural rather than a promise: every compensation configuration reads the
    same file.
  * It is deliberately NOT tuned for KITTI. The experiment is about the
    association stage; a mediocre-but-identical detector across configurations
    is exactly what isolates that.

COCO class mapping to KITTI evaluation classes:
    car        <- car(2), truck(7), bus(5)      [KITTI evaluates 'car', and its
                                                 label set merges Van/Truck-ish
                                                 vehicles as ignore regions]
    pedestrian <- person(0)
Cyclists are ambiguous in COCO (person + bicycle) and are left to KITTI's own
ignore handling rather than guessed at.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import torch
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

COCO_CAR = {2, 7, 5}        # car, truck, bus
COCO_PERSON = {0}
KITTI_CAR, KITTI_PED = 1, 4


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=p("04_experiments/data/KITTI/training"))
    ap.add_argument("--out", default=p("04_experiments/detections/KITTI"))
    ap.add_argument("--model", default="yolo11x.pt")
    ap.add_argument("--conf", type=float, default=0.10)
    ap.add_argument("--iou", type=float, default=0.70)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--device", default="0")
    a = ap.parse_args()

    from ultralytics import YOLO
    os.makedirs(a.out, exist_ok=True)
    model = YOLO(a.model)

    img_root = os.path.join(a.root, "image_02")
    seqs = sorted(d for d in os.listdir(img_root) if os.path.isdir(os.path.join(img_root, d)))

    manifest = dict(created="2026-09-21", detector=a.model, source="COCO-pretrained, never trained on KITTI",
                    conf=a.conf, iou=a.iou, imgsz=a.imgsz,
                    coco_car_classes=sorted(COCO_CAR), coco_person_classes=sorted(COCO_PERSON),
                    torch=torch.__version__, sequences={})

    for seq in seqs:
        t0 = time.time()
        d = os.path.join(img_root, seq)
        files = sorted(f for f in os.listdir(d) if f.lower().endswith(".png"))
        rows = []
        for fid, fn in enumerate(files):          # KITTI frames are 0-indexed
            r = model.predict(os.path.join(d, fn), conf=a.conf, iou=a.iou,
                              imgsz=a.imgsz, device=a.device, verbose=False)[0]
            if r.boxes is None or len(r.boxes) == 0:
                continue
            xyxy = r.boxes.xyxy.cpu().numpy()
            cls = r.boxes.cls.cpu().numpy().astype(int)
            conf = r.boxes.conf.cpu().numpy()
            for b, c, s in zip(xyxy, cls, conf):
                if c in COCO_CAR:
                    k = KITTI_CAR
                elif c in COCO_PERSON:
                    k = KITTI_PED
                else:
                    continue
                rows.append([fid, b[0], b[1], b[2], b[3], s, k])
        arr = np.asarray(rows, np.float32) if rows else np.zeros((0, 7), np.float32)
        p = os.path.join(a.out, f"{seq}.npz")
        np.savez_compressed(p, det=arr)
        manifest["sequences"][seq] = dict(n_frames=len(files), n_detections=int(len(arr)),
                                          sha256=sha256_file(p), seconds=round(time.time() - t0, 1))
        print(f"  {seq}  {len(files):5d} frames  {len(arr):7d} dets  "
              f"{time.time()-t0:6.1f}s", flush=True)

    mp = os.path.join(a.out, "manifest.json")
    json.dump(manifest, open(mp, "w"), indent=1)
    tot = sum(v["n_detections"] for v in manifest["sequences"].values())
    print(f"\ntotal {tot} detections -> {mp}")


if __name__ == "__main__":
    main()
