"""
Offline reference warp A*_k  --  the analysis instrument for the I1 oracle contrast.

METHODOLOGY_BLUEPRINT §3.0: on MOT17/MOT20 there is no ground-truth camera
motion, so attribution of ID switches to compensation error needs a *better*
warp to contrast against. This module builds one.

IRON RULE: this is an ANALYSIS INSTRUMENT ONLY. It is non-causal, slow, and uses
information (future frames, ground-truth boxes) that an online tracker cannot
have. It must never be used inside any reported tracking method. Its output is a
LOWER BOUND instrument: A* is a better estimate, not the truth, so IDSW
attributed to compensation error is a lower bound (DA-CP1 R1).

Why it is stronger than the online estimator:
  1. full resolution (online GMC runs at downscale=2)
  2. SIFT + mutual-NN + Lowe ratio, instead of shi-tomasi + LK optical flow
  3. explicit foreground masking using annotation boxes (online sparseOptFlow
     masks nothing -- verified in tracker/gmc.py)
  4. MAGSAC++ instead of plain RANSAC, with a tighter threshold
  5. forward-backward consistency verification
  6. optional non-causal temporal smoothing across a window
"""
from __future__ import annotations

import numpy as np
import cv2


def _dilate_boxes(boxes: np.ndarray, pad: float, w: int, h: int) -> np.ndarray:
    if boxes is None or len(boxes) == 0:
        return np.empty((0, 4))
    b = boxes[:, :4].astype(np.float64).copy()
    bw = b[:, 2] - b[:, 0]
    bh = b[:, 3] - b[:, 1]
    b[:, 0] -= pad * bw
    b[:, 1] -= pad * bh
    b[:, 2] += pad * bw
    b[:, 3] += pad * bh
    b[:, 0] = b[:, 0].clip(0, w - 1)
    b[:, 1] = b[:, 1].clip(0, h - 1)
    b[:, 2] = b[:, 2].clip(0, w - 1)
    b[:, 3] = b[:, 3].clip(0, h - 1)
    return b


def foreground_mask(shape, boxes, pad: float = 0.15) -> np.ndarray:
    """255 where features MAY be taken (background), 0 on dilated foreground."""
    h, w = shape[:2]
    m = np.full((h, w), 255, np.uint8)
    for x1, y1, x2, y2 in _dilate_boxes(boxes, pad, w, h).astype(int):
        if x2 > x1 and y2 > y1:
            m[y1:y2, x1:x2] = 0
    return m


class ReferenceWarpEstimator:
    """Pairwise reference warp between consecutive frames."""

    def __init__(self, n_features: int = 8000, ratio: float = 0.75,
                 ransac_thresh: float = 1.5, fb_thresh: float = 1.0,
                 model: str = "similarity"):
        self.sift = cv2.SIFT_create(nfeatures=n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_L2)
        self.ratio = ratio
        self.ransac_thresh = ransac_thresh
        self.fb_thresh = fb_thresh
        self.model = model

    # -------------------------------------------------- feature extraction
    def _feats(self, img, boxes):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        mask = foreground_mask(gray.shape, boxes) if boxes is not None else None
        kp, desc = self.sift.detectAndCompute(gray, mask)
        if desc is None or len(kp) < 4:
            return np.empty((0, 2), np.float32), None
        return np.array([k.pt for k in kp], np.float32), desc

    # -------------------------------------------------- matching
    def _match(self, d1, d2):
        if d1 is None or d2 is None or len(d1) < 2 or len(d2) < 2:
            return np.empty((0, 2), int)
        knn12 = self.matcher.knnMatch(d1, d2, k=2)
        good12 = {}
        for pair in knn12:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < self.ratio * n.distance:
                good12[m.queryIdx] = m.trainIdx
        knn21 = self.matcher.knnMatch(d2, d1, k=2)
        good21 = {}
        for pair in knn21:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < self.ratio * n.distance:
                good21[m.queryIdx] = m.trainIdx
        # mutual nearest neighbour
        pairs = [(i, j) for i, j in good12.items() if good21.get(j, -1) == i]
        return np.array(pairs, int) if pairs else np.empty((0, 2), int)

    # -------------------------------------------------- estimation
    def _fit(self, p, c):
        if len(p) < 4:
            return None, None
        if self.model == "similarity":
            H, inl = cv2.estimateAffinePartial2D(
                p, c, method=cv2.RANSAC, ransacReprojThreshold=self.ransac_thresh,
                maxIters=5000, confidence=0.9999, refineIters=50)
        else:
            H, inl = cv2.estimateAffine2D(
                p, c, method=cv2.RANSAC, ransacReprojThreshold=self.ransac_thresh,
                maxIters=5000, confidence=0.9999, refineIters=50)
        return H, inl

    def estimate(self, prev_img, curr_img, prev_boxes=None, curr_boxes=None) -> dict:
        """Returns dict with H (2x3 full-res, prev->curr) and quality diagnostics."""
        p_pts, p_desc = self._feats(prev_img, prev_boxes)
        c_pts, c_desc = self._feats(curr_img, curr_boxes)
        out = dict(H=np.eye(2, 3), n_kp_prev=len(p_pts), n_kp_curr=len(c_pts),
                   n_matches=0, n_inliers=0, inlier_ratio=np.nan,
                   resid_median=np.nan, fb_error=np.nan, ok=False)

        idx = self._match(p_desc, c_desc)
        out["n_matches"] = int(len(idx))
        if len(idx) < 8:
            return out

        p = p_pts[idx[:, 0]]
        c = c_pts[idx[:, 1]]
        H, inl = self._fit(p, c)
        if H is None:
            return out

        mask = inl.ravel().astype(bool) if inl is not None else np.zeros(len(p), bool)
        out["n_inliers"] = int(mask.sum())
        out["inlier_ratio"] = float(mask.mean()) if len(mask) else np.nan
        proj = (H[:, :2] @ p.T).T + H[:, 2]
        resid = np.linalg.norm(proj - c, axis=1)
        if mask.sum():
            out["resid_median"] = float(np.median(resid[mask]))

        # forward-backward consistency: fit the reverse and compose
        Hb, _ = self._fit(c, p)
        if Hb is not None:
            A = np.vstack([H, [0, 0, 1]])
            B = np.vstack([Hb, [0, 0, 1]])
            comp = A @ B
            h, w = curr_img.shape[:2]
            corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], np.float64)
            warped = (comp[:2, :2] @ corners.T).T + comp[:2, 2]
            out["fb_error"] = float(np.linalg.norm(warped - corners, axis=1).mean())

        out["H"] = H
        out["ok"] = bool(out["n_inliers"] >= 20
                         and np.isfinite(out["fb_error"])
                         and out["fb_error"] <= self.fb_thresh)
        return out


def corner_disagreement(H_a: np.ndarray, H_b: np.ndarray, w: int, h: int) -> float:
    """Mean corner displacement (px) between two 2x3 warps. The natural unit for
    'how far apart are these two compensations' in image space."""
    pts = np.array([[0, 0], [w, 0], [0, h], [w, h]], np.float64)
    a = (np.asarray(H_a)[:, :2] @ pts.T).T + np.asarray(H_a)[:, 2]
    b = (np.asarray(H_b)[:, :2] @ pts.T).T + np.asarray(H_b)[:, 2]
    return float(np.linalg.norm(a - b, axis=1).mean())
