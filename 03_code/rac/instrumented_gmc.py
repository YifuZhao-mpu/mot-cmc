"""
Instrumented GMC — exposes the geometric-verification statistics that BoT-SORT's
GMC computes and discards.

Rationale (RQ_BRIEF §1.1c): `tracker/gmc.py` calls
    H, inliesrs = cv2.estimateAffinePartial2D(prevPoints, currPoints, cv2.RANSAC)
and throws the inlier mask away. Everything needed to judge whether the estimate
deserves trust is already computed. This module recovers it.

Design constraints:
  * The *estimate itself* must be bit-identical to the original GMC. This module
    only observes. Any divergence in H invalidates the A1 zero-delta check.
  * No extra feature detection, no extra optical flow. Same calls, same order.

Reference solver: cv2.estimateAffinePartial2D -> 4-DOF similarity
(rotation + uniform scale + translation). Singular values of the linear part are
identically equal, so any sigma1/sigma2 conditioning term is vacuous here
(DA-CP1 M1).
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field, asdict

import cv2
import numpy as np


@dataclass
class GMCStats:
    """Per-frame geometric-verification record. One row per processed frame."""
    frame_id: int = -1

    # --- correspondence pipeline ---
    n_keypoints_prev: int = 0     # keypoints detected in the previous frame
    n_tracked: int = 0            # survived optical-flow status check
    n_used: int = 0               # fed to RANSAC
    n_inliers: int = 0            # RANSAC consensus set size

    # --- reliability primitives ---
    inlier_ratio: float = float("nan")      # rho = n_inliers / n_used
    resid_median: float = float("nan")      # eps: median transfer residual of inliers (px, full-res)
    resid_p90: float = float("nan")
    resid_mean_all: float = float("nan")    # over all used points (inliers + outliers)

    # --- fitted transform, decomposed (similarity: 4 DOF) ---
    scale: float = float("nan")             # s
    rotation_deg: float = float("nan")      # theta
    tx: float = float("nan")
    ty: float = float("nan")
    displacement: float = float("nan")      # ||t|| at full resolution

    # --- temporal consistency (tau) ---
    temporal_resid: float = float("nan")    # ||t_k - t_pred|| from constant-velocity prediction
    temporal_valid: bool = False

    # --- foreground contamination (phi) ---
    # NOTE: applySparseOptFlow ignores `detections`, so keypoints are NOT masked
    # off foreground in BoT-SORT's default CMC path. This makes phi a genuine
    # varying signal there (DA-CP1 M2 resolution depends on measured variance).
    frac_inliers_in_det: float = float("nan")
    frac_used_in_det: float = float("nan")
    n_detections: int = 0

    # --- spatial support, for per-target reliability ---
    # inlier positions at FULL resolution; kept as float32 to bound memory
    inlier_xy: np.ndarray | None = field(default=None, repr=False)

    # --- failure / degeneracy flags ---
    solver_failed: bool = False       # estimateAffinePartial2D returned None
    too_few_points: bool = False      # <5 correspondences -> silent identity fallback
    is_identity_fallback: bool = False
    first_frame: bool = False

    elapsed_ms: float = float("nan")

    def to_row(self) -> dict:
        d = asdict(self)
        d.pop("inlier_xy", None)
        return d


def decompose_similarity(H: np.ndarray) -> tuple[float, float, float, float]:
    """(scale, rotation_deg, tx, ty) for a 2x3 partial-affine (similarity) matrix."""
    a, b = float(H[0, 0]), float(H[0, 1])
    s = float(np.hypot(a, b))
    theta = float(np.degrees(np.arctan2(-b, a)))
    return s, theta, float(H[0, 2]), float(H[1, 2])


def _points_in_boxes(pts: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    """Boolean mask: which points fall inside any box. boxes are tlbr, full-res."""
    if pts is None or len(pts) == 0 or boxes is None or len(boxes) == 0:
        return np.zeros(0 if pts is None else len(pts), dtype=bool)
    x = pts[:, 0][:, None]
    y = pts[:, 1][:, None]
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    inside = (x >= x1) & (x <= x2) & (y >= y1) & (y <= y2)
    return inside.any(axis=1)


class InstrumentedSparseOptFlowGMC:
    """Observation-only reimplementation of GMC.applySparseOptFlow.

    Mirrors tracker/gmc.py exactly (same OpenCV calls, same order, same
    parameters, same downscale handling) so that the returned H matches the
    original bit-for-bit, while recording the statistics it discards.
    """

    def __init__(self, downscale: int = 2, keep_inlier_xy: bool = True):
        self.downscale = max(1, int(downscale))
        self.keep_inlier_xy = keep_inlier_xy

        # identical to tracker/gmc.py sparseOptFlow branch
        self.feature_params = dict(
            maxCorners=1000, qualityLevel=0.01, minDistance=1,
            blockSize=3, useHarrisDetector=False, k=0.04,
        )

        self.prevFrame = None
        self.prevKeyPoints = None
        self.initializedFirstFrame = False

        self._prev_t = None        # translation at k-1 (full-res)
        self._prev_prev_t = None   # translation at k-2
        self.stats: list[GMCStats] = []

    # ------------------------------------------------------------------
    def apply(self, raw_frame: np.ndarray, detections: np.ndarray | None = None,
              frame_id: int = -1) -> tuple[np.ndarray, GMCStats]:
        t0 = time.time()
        st = GMCStats(frame_id=frame_id)

        height, width = raw_frame.shape[:2]
        frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
        H = np.eye(2, 3)

        if self.downscale > 1.0:
            frame = cv2.resize(frame, (width // self.downscale, height // self.downscale))

        keypoints = cv2.goodFeaturesToTrack(frame, mask=None, **self.feature_params)

        if not self.initializedFirstFrame:
            self.prevFrame = frame.copy()
            self.prevKeyPoints = copy.copy(keypoints)
            self.initializedFirstFrame = True
            st.first_frame = True
            st.is_identity_fallback = True
            st.elapsed_ms = 1000 * (time.time() - t0)
            self.stats.append(st)
            return H, st

        st.n_keypoints_prev = 0 if self.prevKeyPoints is None else len(self.prevKeyPoints)

        matchedKeypoints, status, err = cv2.calcOpticalFlowPyrLK(
            self.prevFrame, frame, self.prevKeyPoints, None)

        prevPoints, currPoints = [], []
        for i in range(len(status)):
            if status[i]:
                prevPoints.append(self.prevKeyPoints[i])
                currPoints.append(matchedKeypoints[i])
        prevPoints = np.array(prevPoints)
        currPoints = np.array(currPoints)

        st.n_tracked = int(len(prevPoints))
        st.n_used = st.n_tracked

        # ---- the original guard (note: its second clause compares prevPoints
        # to itself and is always True; preserved verbatim for fidelity) ----
        if (np.size(prevPoints, 0) > 4) and (np.size(prevPoints, 0) == np.size(prevPoints, 0)):
            H_est, inliers = cv2.estimateAffinePartial2D(prevPoints, currPoints, cv2.RANSAC)

            if H_est is None:
                st.solver_failed = True
                st.is_identity_fallback = True
            else:
                H = H_est
                self._record_geometry(st, H, prevPoints, currPoints, inliers,
                                      detections, height, width)
                if self.downscale > 1.0:
                    H[0, 2] *= self.downscale
                    H[1, 2] *= self.downscale
        else:
            st.too_few_points = True
            st.is_identity_fallback = True

        # temporal consistency uses FULL-res translation
        s, theta, tx, ty = decompose_similarity(H)
        st.scale, st.rotation_deg, st.tx, st.ty = s, theta, tx, ty
        st.displacement = float(np.hypot(tx, ty))
        self._record_temporal(st, np.array([tx, ty]))

        self.prevFrame = frame.copy()
        self.prevKeyPoints = copy.copy(keypoints)
        st.elapsed_ms = 1000 * (time.time() - t0)
        self.stats.append(st)
        return H, st

    # ------------------------------------------------------------------
    def _record_geometry(self, st, H, prevPoints, currPoints, inliers,
                         detections, height, width):
        p = prevPoints.reshape(-1, 2).astype(np.float64)
        c = currPoints.reshape(-1, 2).astype(np.float64)

        # transfer residuals at DOWNSCALED resolution, then rescale to full-res px
        proj = (H[:, :2] @ p.T).T + H[:, 2]
        resid = np.linalg.norm(proj - c, axis=1) * self.downscale

        if inliers is not None:
            mask = inliers.ravel().astype(bool)
        else:
            mask = np.zeros(len(p), dtype=bool)

        st.n_inliers = int(mask.sum())
        st.inlier_ratio = float(st.n_inliers / max(1, len(p)))
        st.resid_mean_all = float(resid.mean()) if len(resid) else float("nan")
        if st.n_inliers > 0:
            st.resid_median = float(np.median(resid[mask]))
            st.resid_p90 = float(np.percentile(resid[mask], 90))

        # full-resolution inlier coordinates (current frame)
        xy_full = c * self.downscale
        if self.keep_inlier_xy and st.n_inliers > 0:
            st.inlier_xy = xy_full[mask].astype(np.float32)

        # foreground contamination
        if detections is not None and len(detections) > 0:
            boxes = np.asarray(detections, dtype=np.float64)[:, :4]
            st.n_detections = int(len(boxes))
            in_det_all = _points_in_boxes(xy_full, boxes)
            st.frac_used_in_det = float(in_det_all.mean()) if len(in_det_all) else float("nan")
            if st.n_inliers > 0:
                st.frac_inliers_in_det = float(in_det_all[mask].mean())

    def _record_temporal(self, st, t_now: np.ndarray):
        if self._prev_t is not None and self._prev_prev_t is not None:
            t_pred = 2.0 * self._prev_t - self._prev_prev_t   # constant-velocity
            st.temporal_resid = float(np.linalg.norm(t_now - t_pred))
            st.temporal_valid = True
        self._prev_prev_t = self._prev_t
        self._prev_t = t_now.copy()

    # ------------------------------------------------------------------
    def to_dataframe(self):
        import pandas as pd
        return pd.DataFrame([s.to_row() for s in self.stats])
