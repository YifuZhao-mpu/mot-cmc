"""
RAC-Track: reliability-aware camera-motion compensation for tracking-by-detection.

Built as a drop-in variant of BoT-SORT. Every component is individually
switchable so the ablation matrix (METHODOLOGY_BLUEPRINT §3.3) maps 1:1 onto
configuration flags rather than onto separate code paths.

Three propagation paths, all driven by a per-target reliability r_i in [0,1]:

  P1  shrink the applied warp toward identity     A_eff(i) = Interp(I, A; r_i)
  P2  admit compensation uncertainty into the KF  P += (1-r_i)^2 * Sigma_cmc(i)
  P3  condition the association on reliability    theta_iou(r), motion penalty

K3 INVARIANT (binding, DA-CP1): with r == 1 every path is the identity
transformation of BoT-SORT's behaviour --
    Interp(I, A; 1) = A,  (1-1)^2 = 0,  theta_iou(1) = theta_iou_base,  beta*(1-1) = 0
so configuration A7 must reproduce A0 exactly. `assert_k3()` checks this
numerically rather than trusting the derivation.
"""
from __future__ import annotations

from pathlib import Path as _P
import sys
from dataclasses import dataclass, field

import numpy as np
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

BOT = p("03_code/BoT-SORT")
if BOT not in sys.path:
    sys.path.insert(0, BOT)

from tracker import matching  # noqa: E402
from tracker.bot_sort import BoTSORT, STrack, joint_stracks, sub_stracks, remove_duplicate_stracks  # noqa: E402
from tracker.basetrack import TrackState  # noqa: E402

sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "03_code"))
from rac.instrumented_gmc import InstrumentedSparseOptFlowGMC, GMCStats  # noqa: E402


# ----------------------------------------------------------------------------
@dataclass
class RACConfig:
    # --- which propagation paths are active (ablation switches) ---
    p1_shrinkage: bool = False
    p2_inflation: bool = False
    p3_association: bool = False

    # --- reliability construction ---
    per_target: bool = True
    signals: tuple = ("rho", "n", "eps", "tau", "kappa", "phi")
    force_r: float | None = None          # 1.0 -> K3 invariant test; 0.0 -> no compensation
    shuffle_placebo: bool = False         # I3 placebo: reliability from shuffled stats

    # --- normalisation constants (frozen on MOT17 TRAIN half; never re-tuned) ---
    n0: float = 300.0
    eps0: float = 1.0
    tau0: float = 5.0
    s0: float = 0.05
    theta0: float = 2.0

    # --- spatial support for per-target reliability ---
    support_dilate: float = 1.5
    s_min: float = 0.3
    support_k0: float = 12.0              # inliers in the neighbourhood for full support

    # --- P3 parameters ---
    theta_iou_max: float = 0.8            # gate ceiling at r = 0
    beta: float = 0.0                     # motion-cost penalty at r = 0

    # --- P2 parameters ---
    sigma_scale: float = 1.0

    # --- N2 instrument: substitute an externally supplied warp for the online one.
    #     'online'    : BoT-SORT's own GMC (the only setting valid for a reported method)
    #     'reference' : the offline oracle warp -- ANALYSIS ONLY, non-causal, never a method
    #     'none'      : identity, i.e. compensation disabled
    warp_source: str = "online" 

    def signal_names(self) -> tuple:
        return tuple(s for s in self.signals)


# ----------------------------------------------------------------------------
def frame_reliability(st: GMCStats, cfg: RACConfig) -> tuple[float, dict]:
    """Global frame reliability r_k from the solver's own verification statistics."""
    parts: dict[str, float] = {}
    if "rho" in cfg.signals:
        parts["rho"] = 0.0 if not np.isfinite(st.inlier_ratio) else float(st.inlier_ratio)
    if "n" in cfg.signals:
        parts["n"] = float(min(1.0, st.n_inliers / cfg.n0))
    if "eps" in cfg.signals:
        e = st.resid_median if np.isfinite(st.resid_median) else 10.0
        parts["eps"] = float(np.exp(-e / cfg.eps0))
    if "tau" in cfg.signals:
        if st.temporal_valid and np.isfinite(st.temporal_resid):
            parts["tau"] = float(np.exp(-st.temporal_resid / cfg.tau0))
        else:
            parts["tau"] = 1.0            # no history yet -> no evidence against
    if "kappa" in cfg.signals:
        s = st.scale if np.isfinite(st.scale) and st.scale > 0 else 1.0
        th = st.rotation_deg if np.isfinite(st.rotation_deg) else 0.0
        parts["kappa"] = float(np.exp(-(abs(np.log(s)) / cfg.s0 + abs(th) / cfg.theta0)))
    if "phi" in cfg.signals:
        f = st.frac_inliers_in_det
        parts["phi"] = 1.0 if not np.isfinite(f) else float(1.0 - f)

    if not parts:
        return 1.0, parts
    vals = np.clip(np.array(list(parts.values()), float), 1e-9, 1.0)
    r = float(np.power(np.prod(vals), 1.0 / len(vals)))
    return r, parts


def local_support(boxes_tlbr: np.ndarray, inlier_xy: np.ndarray | None,
                  cfg: RACConfig) -> np.ndarray:
    """s_i in [s_min, 1]: how much registered background surrounds each track.

    A track embedded in a crowd with no background inliers nearby cannot inherit
    the frame's confidence; a track surrounded by well-registered background can.
    This is the component with no counterpart in prior art.
    """
    n = len(boxes_tlbr)
    if n == 0:
        return np.zeros(0)
    if inlier_xy is None or len(inlier_xy) == 0:
        return np.full(n, cfg.s_min)
    b = np.asarray(boxes_tlbr, float)
    w = (b[:, 2] - b[:, 0]) * cfg.support_dilate
    h = (b[:, 3] - b[:, 1]) * cfg.support_dilate
    cx = (b[:, 0] + b[:, 2]) / 2.0
    cy = (b[:, 1] + b[:, 3]) / 2.0
    x = inlier_xy[:, 0][None, :]
    y = inlier_xy[:, 1][None, :]
    inside = (np.abs(x - cx[:, None]) <= (w / 2)[:, None]) & \
             (np.abs(y - cy[:, None]) <= (h / 2)[:, None])
    k = inside.sum(axis=1).astype(float)
    s = np.minimum(1.0, k / cfg.support_k0)
    return np.clip(s, cfg.s_min, 1.0)


def interp_similarity(H: np.ndarray, r: float) -> np.ndarray:
    """Geodesic interpolation between identity and a 2x3 similarity, by r.

    r=1 returns H unchanged (bit-identical); r=0 returns identity.
    """
    if r >= 1.0:
        return np.asarray(H, float).copy()
    a, b = float(H[0, 0]), float(H[0, 1])
    s = float(np.hypot(a, b))
    th = float(np.arctan2(-b, a))
    s_r = s ** r
    th_r = th * r
    c, sn = np.cos(th_r), np.sin(th_r)
    out = np.zeros((2, 3), float)
    out[0, 0] = s_r * c
    out[0, 1] = -s_r * sn
    out[1, 0] = s_r * sn
    out[1, 1] = s_r * c
    out[0, 2] = float(H[0, 2]) * r
    out[1, 2] = float(H[1, 2]) * r
    return out


def apply_gmc_per_track(tracks, H, r_per_track, cfg: RACConfig, st: GMCStats):
    """P1 + P2: per-target warp shrinkage and covariance inflation.

    With r == 1 for every track and both paths disabled this is numerically
    identical to STrack.multi_gmc (verified by assert_k3).
    """
    if len(tracks) == 0:
        return
    for i, tr in enumerate(tracks):
        r = float(r_per_track[i]) if r_per_track is not None else 1.0
        H_eff = interp_similarity(H, r) if cfg.p1_shrinkage else np.asarray(H, float)

        R = H_eff[:2, :2]
        R8 = np.kron(np.eye(4, dtype=float), R)
        t = H_eff[:2, 2]

        mean = R8.dot(tr.mean)
        mean[:2] += t
        cov = R8.dot(tr.covariance).dot(R8.T)

        if cfg.p2_inflation and r < 1.0:
            disp = float(np.hypot(H_eff[0, 2], H_eff[1, 2]))
            resid = st.resid_median if np.isfinite(st.resid_median) else 0.0
            sigma = cfg.sigma_scale * ((1.0 - r) * disp + resid)
            cov[0, 0] += sigma ** 2
            cov[1, 1] += sigma ** 2

        tr.mean = mean
        tr.covariance = cov


# ----------------------------------------------------------------------------
class RACTracker(BoTSORT):
    """BoT-SORT with reliability-aware compensation. See module docstring."""

    def __init__(self, args, frame_rate=30, cfg: RACConfig | None = None):
        super().__init__(args, frame_rate)
        self.cfg = cfg or RACConfig()
        self.rac_gmc = InstrumentedSparseOptFlowGMC(
            downscale=getattr(args, "cmc_downscale", 2), keep_inlier_xy=True)
        self.log: list[dict] = []
        self._rng = np.random.default_rng(12345)
        self.warp_table: dict[int, np.ndarray] = {}   # frame_id -> 2x3, for warp_source='reference'
        self.warp_ok: dict[int, bool] = {}
        self.n_warp_fallback = 0
        self.n_warp_lowq = 0

    def load_reference_warps(self, npz_path: str, frame_offset: int = 0):
        """Load offline reference warps. `frame_offset` maps tracker frame ids
        (1..N over the val half) onto original sequence frame numbers."""
        arr = np.load(npz_path)["warp"]
        for row in arr:
            orig = int(row[0])
            self.warp_table[orig - frame_offset] = row[1:7].reshape(2, 3)
            self.warp_ok[orig - frame_offset] = bool(row[7] > 0.5)

    # -- reliability for the current frame -------------------------------
    def _reliability(self, st: GMCStats, tracks) -> tuple[np.ndarray, float, dict]:
        if self.cfg.force_r is not None:
            r = float(self.cfg.force_r)
            return np.full(len(tracks), r), r, {}
        r_frame, parts = frame_reliability(st, self.cfg)
        if self.cfg.shuffle_placebo:
            r_frame = float(self._rng.random())
        if not self.cfg.per_target or len(tracks) == 0:
            return np.full(len(tracks), r_frame), r_frame, parts
        boxes = np.array([t.tlbr for t in tracks], float)
        s = local_support(boxes, st.inlier_xy, self.cfg)
        return np.clip(r_frame * s, 0.0, 1.0), r_frame, parts

    # -- P3 association cost ---------------------------------------------
    def _cost_matrix(self, strack_pool, detections, r_tracks):
        """Reliability-conditioned version of bot_sort.py:303-314.

        Original (r == 1 everywhere):
            ious_dists_mask = ious_dists > proximity_thresh
            emb_dists[emb_dists > appearance_thresh] = 1.0
            emb_dists[ious_dists_mask] = 1.0
            dists = minimum(ious_dists, emb_dists)
        """
        ious_dists = matching.iou_distance(strack_pool, detections)

        if self.cfg.p3_association and len(r_tracks):
            # theta_iou(r) = base + (1-r)*(max-base), per track -> row-wise gate
            theta = (self.proximity_thresh
                     + (1.0 - np.asarray(r_tracks, float))
                     * (self.cfg.theta_iou_max - self.proximity_thresh))
            ious_dists_mask = ious_dists > theta[:, None]
        else:
            ious_dists_mask = ious_dists > self.proximity_thresh

        if not self.args.mot20:
            ious_dists = matching.fuse_score(ious_dists, detections)

        if self.args.with_reid:
            emb_dists = matching.embedding_distance(strack_pool, detections) / 2.0
            emb_dists[emb_dists > self.appearance_thresh] = 1.0
            emb_dists[ious_dists_mask] = 1.0
            motion = ious_dists
            if self.cfg.p3_association and self.cfg.beta > 0 and len(r_tracks):
                motion = ious_dists + self.cfg.beta * (1.0 - np.asarray(r_tracks, float))[:, None]
            dists = np.minimum(motion, emb_dists)
        else:
            dists = ious_dists
            if self.cfg.p3_association and self.cfg.beta > 0 and len(r_tracks):
                dists = dists + self.cfg.beta * (1.0 - np.asarray(r_tracks, float))[:, None]
        return dists

    # -- diagnostics ------------------------------------------------------
    def record(self, st: GMCStats, r_frame: float, r_tracks: np.ndarray, parts: dict):
        row = dict(frame_id=self.frame_id, r_frame=r_frame,
                   n_tracks=len(r_tracks),
                   r_track_min=float(r_tracks.min()) if len(r_tracks) else np.nan,
                   r_track_med=float(np.median(r_tracks)) if len(r_tracks) else np.nan,
                   inlier_ratio=st.inlier_ratio, n_inliers=st.n_inliers,
                   resid_median=st.resid_median, temporal_resid=st.temporal_resid,
                   frac_inliers_in_det=st.frac_inliers_in_det,
                   scale=st.scale, rotation_deg=st.rotation_deg,
                   displacement=st.displacement)
        row.update({f"sig_{k}": v for k, v in parts.items()})
        self.log.append(row)


# ----------------------------------------------------------------------------
def assert_k3(seed: int = 0, n: int = 200) -> dict:
    """Numerically verify the K3 invariant on the transformation primitives.

    Checks that at r == 1: interp_similarity is the identity operation, and the
    per-track GMC application reproduces STrack.multi_gmc bit-for-bit.
    """
    rng = np.random.default_rng(seed)
    max_interp = 0.0
    for _ in range(n):
        s = float(np.exp(rng.normal(0, 0.05)))
        th = float(rng.normal(0, 0.05))
        H = np.array([[s * np.cos(th), -s * np.sin(th), rng.normal(0, 20)],
                      [s * np.sin(th), s * np.cos(th), rng.normal(0, 20)]])
        max_interp = max(max_interp, float(np.abs(interp_similarity(H, 1.0) - H).max()))

    # per-track application vs the original multi_gmc formula
    class _T:
        pass

    max_apply = 0.0
    cfg = RACConfig(p1_shrinkage=True, p2_inflation=True)
    for _ in range(n):
        s = float(np.exp(rng.normal(0, 0.05)))
        th = float(rng.normal(0, 0.05))
        H = np.array([[s * np.cos(th), -s * np.sin(th), rng.normal(0, 20)],
                      [s * np.sin(th), s * np.cos(th), rng.normal(0, 20)]])
        mean = rng.normal(0, 50, 8)
        A = rng.normal(0, 1, (8, 8))
        cov = A @ A.T
        t1, t2 = _T(), _T()
        t1.mean, t1.covariance = mean.copy(), cov.copy()
        t2.mean, t2.covariance = mean.copy(), cov.copy()

        st = GMCStats(resid_median=0.5)
        apply_gmc_per_track([t1], H, np.array([1.0]), cfg, st)

        R = H[:2, :2]
        R8 = np.kron(np.eye(4), R)
        m = R8.dot(t2.mean)
        m[:2] += H[:2, 2]
        c = R8.dot(t2.covariance).dot(R8.T)
        max_apply = max(max_apply,
                        float(max(np.abs(t1.mean - m).max(), np.abs(t1.covariance - c).max())))

    return dict(max_interp_diff=max_interp, max_apply_diff=max_apply,
                passed=bool(max_interp == 0.0 and max_apply == 0.0))


if __name__ == "__main__":
    print("K3 invariant check:", assert_k3())


# ----------------------------------------------------------------------------
def _rac_update(self, output_results, img):
    """Faithful copy of BoTSORT.update with exactly three substitutions:
       (1) instrumented GMC instead of self.gmc.apply
       (2) apply_gmc_per_track (P1+P2) instead of STrack.multi_gmc
       (3) self._cost_matrix (P3) instead of the inline first-association block
    Every other line mirrors tracker/bot_sort.py:230-430.
    """
    self.frame_id += 1
    activated_starcks, refind_stracks, lost_stracks, removed_stracks = [], [], [], []

    if len(output_results):
        if output_results.shape[1] == 5:
            scores = output_results[:, 4]
            bboxes = output_results[:, :4]
            classes = output_results[:, -1]
        else:
            scores = output_results[:, 4] * output_results[:, 5]
            bboxes = output_results[:, :4]
            classes = output_results[:, -1]

        lowest_inds = scores > self.args.track_low_thresh
        bboxes = bboxes[lowest_inds]
        scores = scores[lowest_inds]
        classes = classes[lowest_inds]

        remain_inds = scores > self.args.track_high_thresh
        dets = bboxes[remain_inds]
        scores_keep = scores[remain_inds]
        classes_keep = classes[remain_inds]
    else:
        bboxes = scores = classes = dets = scores_keep = classes_keep = []

    if self.args.with_reid and len(dets):
        features_keep = self.encoder.inference(img, dets)

    if len(dets) > 0:
        if self.args.with_reid:
            detections = [STrack(STrack.tlbr_to_tlwh(tlbr), s, f)
                          for (tlbr, s, f) in zip(dets, scores_keep, features_keep)]
        else:
            detections = [STrack(STrack.tlbr_to_tlwh(tlbr), s)
                          for (tlbr, s) in zip(dets, scores_keep)]
    else:
        detections = []

    unconfirmed, tracked_stracks = [], []
    for track in self.tracked_stracks:
        (tracked_stracks if track.is_activated else unconfirmed).append(track)

    strack_pool = joint_stracks(tracked_stracks, self.lost_stracks)
    STrack.multi_predict(strack_pool)

    # ---- (1) instrumented CMC -------------------------------------------
    warp, st = self.rac_gmc.apply(img, dets if len(dets) else None, frame_id=self.frame_id)
    if self.cfg.warp_source == "none":
        warp = np.eye(2, 3)
    elif self.cfg.warp_source == "reference":
        # Review finding: this fell back to the ONLINE estimate whenever the
        # reference failed its quality gate -- 76 of 418 frames on MOT17-05,
        # the sequence where the two warps differ most. That makes the
        # configuration a hybrid and dilutes the contrast toward zero exactly
        # where it would be largest. `reference_strict` uses the reference
        # wherever it was computed at all, so the substitution is total.
        w = self.warp_table.get(self.frame_id)
        if w is not None and self.warp_ok.get(self.frame_id, False):
            warp = w.copy()
        else:
            self.n_warp_fallback += 1     # reference unavailable -> keep the online estimate
    elif self.cfg.warp_source == "reference_strict":
        w = self.warp_table.get(self.frame_id)
        if w is not None:
            warp = w.copy()
            if not self.warp_ok.get(self.frame_id, False):
                self.n_warp_lowq += 1
        else:
            self.n_warp_fallback += 1

    # ---- reliability ------------------------------------------------------
    r_pool, r_frame, parts = self._reliability(st, strack_pool)
    r_unconf, _, _ = self._reliability(st, unconfirmed)
    self.record(st, r_frame, r_pool, parts)

    # ---- (2) P1 + P2 -------------------------------------------------------
    apply_gmc_per_track(strack_pool, warp, r_pool, self.cfg, st)
    apply_gmc_per_track(unconfirmed, warp, r_unconf, self.cfg, st)

    # ---- (3) P3 ------------------------------------------------------------
    dists = self._cost_matrix(strack_pool, detections, r_pool)

    matches, u_track, u_detection = matching.linear_assignment(
        dists, thresh=self.args.match_thresh)
    for itracked, idet in matches:
        track, det = strack_pool[itracked], detections[idet]
        if track.state == TrackState.Tracked:
            track.update(detections[idet], self.frame_id); activated_starcks.append(track)
        else:
            track.re_activate(det, self.frame_id, new_id=False); refind_stracks.append(track)

    # ---- second association (unchanged) ------------------------------------
    if len(scores):
        inds_second = np.logical_and(scores > self.args.track_low_thresh,
                                     scores < self.args.track_high_thresh)
        dets_second = bboxes[inds_second]; scores_second = scores[inds_second]
    else:
        dets_second = []; scores_second = []

    detections_second = [STrack(STrack.tlbr_to_tlwh(tlbr), s)
                         for (tlbr, s) in zip(dets_second, scores_second)] if len(dets_second) else []

    r_tracked_stracks = [strack_pool[i] for i in u_track
                         if strack_pool[i].state == TrackState.Tracked]
    dists = matching.iou_distance(r_tracked_stracks, detections_second)
    matches, u_track, _ = matching.linear_assignment(dists, thresh=0.5)
    for itracked, idet in matches:
        track, det = r_tracked_stracks[itracked], detections_second[idet]
        if track.state == TrackState.Tracked:
            track.update(det, self.frame_id); activated_starcks.append(track)
        else:
            track.re_activate(det, self.frame_id, new_id=False); refind_stracks.append(track)
    for it in u_track:
        track = r_tracked_stracks[it]
        if track.state != TrackState.Lost:
            track.mark_lost(); lost_stracks.append(track)

    # ---- unconfirmed (unchanged) -------------------------------------------
    detections = [detections[i] for i in u_detection]
    ious_dists = matching.iou_distance(unconfirmed, detections)
    ious_dists_mask = (ious_dists > self.proximity_thresh)
    if not self.args.mot20:
        ious_dists = matching.fuse_score(ious_dists, detections)
    if self.args.with_reid:
        emb_dists = matching.embedding_distance(unconfirmed, detections) / 2.0
        emb_dists[emb_dists > self.appearance_thresh] = 1.0
        emb_dists[ious_dists_mask] = 1.0
        dists = np.minimum(ious_dists, emb_dists)
    else:
        dists = ious_dists
    matches, u_unconfirmed, u_detection = matching.linear_assignment(dists, thresh=0.7)
    for itracked, idet in matches:
        unconfirmed[itracked].update(detections[idet], self.frame_id)
        activated_starcks.append(unconfirmed[itracked])
    for it in u_unconfirmed:
        unconfirmed[it].mark_removed(); removed_stracks.append(unconfirmed[it])

    for inew in u_detection:
        track = detections[inew]
        if track.score < self.new_track_thresh:
            continue
        track.activate(self.kalman_filter, self.frame_id); activated_starcks.append(track)

    for track in self.lost_stracks:
        if self.frame_id - track.end_frame > self.max_time_lost:
            track.mark_removed(); removed_stracks.append(track)

    self.tracked_stracks = [t for t in self.tracked_stracks if t.state == TrackState.Tracked]
    self.tracked_stracks = joint_stracks(self.tracked_stracks, activated_starcks)
    self.tracked_stracks = joint_stracks(self.tracked_stracks, refind_stracks)
    self.lost_stracks = sub_stracks(self.lost_stracks, self.tracked_stracks)
    self.lost_stracks.extend(lost_stracks)
    self.lost_stracks = sub_stracks(self.lost_stracks, self.removed_stracks)
    self.removed_stracks.extend(removed_stracks)
    self.tracked_stracks, self.lost_stracks = remove_duplicate_stracks(
        self.tracked_stracks, self.lost_stracks)
    return [track for track in self.tracked_stracks]


RACTracker.update = _rac_update
