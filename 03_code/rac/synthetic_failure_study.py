"""
Controlled GMC-failure study with a KNOWN ground-truth warp.

Purpose: validate that the reliability primitives actually respond to the
failure modes the literature names, in a setting where the true camera motion is
known exactly. This is the synthetic analogue of the I1 oracle-warp contrast
(METHODOLOGY_BLUEPRINT §3.0) and is independent of MOT17/MOT20.

Failure modes injected (each named by a primary source):
  clean          textured background, no degradation                 (control)
  low_texture    near-uniform background   -- Safdarnejad 2016 "uniform background"
  blur           motion blur               -- McByte++ 2026 "heavy motion blur"
  foreground     large moving occluders    -- Safdarnejad 2016 "predominant foreground"
  repetitive     periodic pattern          -- classic aperture/aliasing failure
  lowlight       heavy sensor noise + low contrast

Reported per frame: true warp, estimated warp, ACTUAL compensation error in
pixels, and every reliability primitive. The question the study answers is
whether the primitives are *predictive of the actual error* -- not whether they
look plausible.
"""
from __future__ import annotations

from pathlib import Path as _P
import sys
import numpy as np
import cv2
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC, decompose_similarity  # noqa: E402

H_IMG, W_IMG = 540, 960
N_FRAMES = 40
SEED = 20260920


def _texture(rng, h=H_IMG, w=W_IMG, scale=1.0):
    img = (rng.random((h, w, 3)) * 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (7, 7), 0)
    if scale != 1.0:
        img = np.clip(128 + (img.astype(np.float32) - 128) * scale, 0, 255).astype(np.uint8)
    return img


def make_background(mode: str, rng) -> np.ndarray:
    if mode == "low_texture":
        base = np.full((H_IMG, W_IMG, 3), 128, np.uint8)
        noise = (rng.random((H_IMG, W_IMG, 3)) * 255).astype(np.uint8)
        noise = cv2.GaussianBlur(noise, (31, 31), 0)
        return np.clip(128 + (noise.astype(np.float32) - 128) * 0.12, 0, 255).astype(np.uint8)
    if mode == "repetitive":
        yy, xx = np.mgrid[0:H_IMG, 0:W_IMG]
        pat = (127 + 120 * np.sin(xx / 6.0) * np.sin(yy / 6.0)).astype(np.uint8)
        return cv2.cvtColor(pat, cv2.COLOR_GRAY2BGR)
    return _texture(rng)


def true_warp(k: int) -> np.ndarray:
    """Ground-truth camera motion: pan + oscillation + slow rotation."""
    tx = 5.0 * k
    ty = 3.0 * np.sin(k / 3.0)
    th = 0.35 * k
    M = cv2.getRotationMatrix2D((W_IMG / 2, H_IMG / 2), th, 1.0)
    M[0, 2] += tx
    M[1, 2] += ty
    return M


def compose_inverse_step(k: int) -> np.ndarray:
    """True frame-to-frame warp mapping frame k-1 -> frame k, as a 2x3."""
    A_prev = np.vstack([true_warp(k - 1), [0, 0, 1]])
    A_curr = np.vstack([true_warp(k), [0, 0, 1]])
    return (A_curr @ np.linalg.inv(A_prev))[:2]


def add_foreground(img, k, rng, n_blobs=9, frac=0.55):
    """Large independently-moving occluders covering ~frac of the frame."""
    out = img.copy()
    boxes = []
    area_target = frac * H_IMG * W_IMG
    per = area_target / n_blobs
    bw = int(np.sqrt(per * 0.6))
    bh = int(per / max(1, bw))
    for i in range(n_blobs):
        cx = int((i * 137 + 31 * k * (1 + i % 3)) % W_IMG)
        cy = int((i * 97 + 19 * k * (1 + i % 2)) % H_IMG)
        x1, y1 = max(0, cx - bw // 2), max(0, cy - bh // 2)
        x2, y2 = min(W_IMG, x1 + bw), min(H_IMG, y1 + bh)
        if x2 <= x1 or y2 <= y1:
            continue
        patch = (rng.random((y2 - y1, x2 - x1, 3)) * 255).astype(np.uint8)
        patch = cv2.GaussianBlur(patch, (5, 5), 0)
        out[y1:y2, x1:x2] = patch
        boxes.append([x1, y1, x2, y2, 0.95])
    return out, np.array(boxes, dtype=np.float64) if boxes else np.empty((0, 5))


def degrade(img, mode, k, rng):
    dets = np.empty((0, 5))
    if mode == "blur":
        ks = 21
        kern = np.zeros((ks, ks), np.float32)
        kern[ks // 2, :] = 1.0 / ks
        img = cv2.filter2D(img, -1, kern)
    elif mode == "foreground":
        img, dets = add_foreground(img, k, rng)
    elif mode == "lowlight":
        img = np.clip(img.astype(np.float32) * 0.25 + rng.normal(0, 18, img.shape), 0, 255).astype(np.uint8)
    return img, dets


def corner_error(H_est: np.ndarray, H_true: np.ndarray) -> float:
    """Mean displacement error (px) of the 4 image corners under est vs true warp."""
    pts = np.array([[0, 0], [W_IMG, 0], [0, H_IMG], [W_IMG, H_IMG]], np.float64)
    pe = (H_est[:, :2] @ pts.T).T + H_est[:, 2]
    pt = (H_true[:, :2] @ pts.T).T + H_true[:, 2]
    return float(np.linalg.norm(pe - pt, axis=1).mean())


def run_mode(mode: str) -> list[dict]:
    rng = np.random.default_rng(SEED)
    bg = make_background(mode, rng)
    gmc = InstrumentedSparseOptFlowGMC(downscale=2)
    rows = []
    for k in range(N_FRAMES):
        frame = cv2.warpAffine(bg, true_warp(k), (W_IMG, H_IMG))
        frame, dets = degrade(frame, mode, k, rng)
        H_est, st = gmc.apply(frame, dets if len(dets) else None, frame_id=k)
        if k == 0:
            continue
        H_true = compose_inverse_step(k)
        err = corner_error(np.asarray(H_est, np.float64), H_true)
        s_t, th_t, tx_t, ty_t = decompose_similarity(H_true)
        rows.append(dict(
            mode=mode, k=k, corner_err_px=err,
            true_tx=tx_t, true_ty=ty_t, est_tx=st.tx, est_ty=st.ty,
            n_used=st.n_used, n_inliers=st.n_inliers,
            rho=st.inlier_ratio, eps=st.resid_median,
            scale=st.scale, rot=st.rotation_deg,
            temporal_resid=st.temporal_resid,
            frac_inl_in_det=st.frac_inliers_in_det,
            identity_fallback=st.is_identity_fallback,
            solver_failed=st.solver_failed, too_few=st.too_few_points,
        ))
    return rows


def main():
    import pandas as pd
    modes = ["clean", "low_texture", "blur", "foreground", "repetitive", "lowlight"]
    all_rows = []
    for m in modes:
        all_rows += run_mode(m)
    df = pd.DataFrame(all_rows)
    out = p("04_experiments/synthetic_failure_study.csv")
    df.to_csv(out, index=False)

    pd.set_option("display.width", 200)
    agg = df.groupby("mode").agg(
        err_med=("corner_err_px", "median"),
        err_p90=("corner_err_px", lambda x: np.percentile(x, 90)),
        err_max=("corner_err_px", "max"),
        rho_med=("rho", "median"),
        eps_med=("eps", "median"),
        n_inl_med=("n_inliers", "median"),
        frac_fg=("frac_inl_in_det", "median"),
        fallback=("identity_fallback", "mean"),
    ).reindex(modes)
    print("\n=== GMC behaviour under injected failure modes "
          f"(N={N_FRAMES-1} frames each, ground-truth warp known) ===\n")
    print(agg.round(4).to_string())
    print(f"\nrows={len(df)}  saved -> {out}")
    return df


if __name__ == "__main__":
    main()
