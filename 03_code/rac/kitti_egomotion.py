"""
KITTI ground-truth ego-motion -> image warp.

This is qualitatively stronger than everything used on MOT17. There, no
ground-truth camera motion exists, so compensation error could only be measured
against a *better estimate* (the offline reference warp), making every figure a
lower bound. KITTI ships GPS/IMU per frame (`oxts`) plus the full calibration
chain, so the true inter-frame camera motion is known exactly.

That buys two things MOT17 could not give:

  1. **True compensation error.** The online GMC estimate can be compared against
     the actual camera motion, not against another estimate.

  2. **The part no 2D warp can fix.** KITTI is vehicle-mounted and therefore
     translation-dominated. For a purely rotating camera the induced image
     motion is exactly a homography `H = K R K^-1`, independent of depth. Under
     translation it is not: displacement scales with inverse depth, so a single
     2D warp is *wrong by construction*. KITTI's 3D object labels give per-object
     depth, so the size of that model error can be measured directly rather than
     assumed.

Point 2 is the qualitative difference from MOT17/MOT20 and the reason this
domain was chosen.

Conventions (KITTI devkit):
  oxts / IMU : x forward, y left,  z up
  velodyne   : x forward, y left,  z up
  camera rect: x right,   y down,  z forward
  chain: X_cam_rect = R_rect . Tr_velo_cam . Tr_imu_velo . X_imu
"""
from __future__ import annotations

import os

import numpy as np

ER = 6378137.0          # earth radius used by the KITTI devkit


# --------------------------------------------------------------------- oxts
def _rot(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def load_oxts_poses(path: str) -> np.ndarray:
    """(N,4,4) IMU->world poses, Mercator-projected as in the KITTI devkit.

    The first frame's latitude fixes the Mercator scale, and the first pose is
    taken as the world origin, so poses are relative to the sequence start.
    """
    raw = np.loadtxt(path).reshape(-1, 30)
    lat, lon, alt = raw[:, 0], raw[:, 1], raw[:, 2]
    roll, pitch, yaw = raw[:, 3], raw[:, 4], raw[:, 5]

    scale = np.cos(lat[0] * np.pi / 180.0)
    tx = scale * lon * np.pi * ER / 180.0
    ty = scale * ER * np.log(np.tan((90.0 + lat) * np.pi / 360.0))
    tz = alt

    poses = np.zeros((len(raw), 4, 4))
    for i in range(len(raw)):
        T = np.eye(4)
        T[:3, :3] = _rot(roll[i], pitch[i], yaw[i])
        T[:3, 3] = [tx[i], ty[i], tz[i]]
        poses[i] = T
    T0inv = np.linalg.inv(poses[0])
    return np.einsum("ij,njk->nik", T0inv, poses)


# --------------------------------------------------------------------- calib
def load_calib(path: str) -> dict:
    vals = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        if not v:
            k, *rest = line.split()
            v = " ".join(rest)
        vals[k.strip()] = np.array([float(x) for x in v.split()])

    def to44(a):
        T = np.eye(4)
        T[:3, :4] = a.reshape(3, 4)
        return T

    P2 = vals["P2"].reshape(3, 4)
    R_rect = np.eye(4)
    R_rect[:3, :3] = vals["R_rect"].reshape(3, 3)
    Tr_velo_cam = to44(vals["Tr_velo_cam"])
    Tr_imu_velo = to44(vals["Tr_imu_velo"])

    # X_cam_rect = R_rect . Tr_velo_cam . Tr_imu_velo . X_imu
    T_cam_imu = R_rect @ Tr_velo_cam @ Tr_imu_velo
    K = P2[:3, :3].copy()
    # P2 carries a baseline offset; recover the pure projection of cam2 by
    # folding that offset into an extra translation of the camera frame.
    t_extra = np.linalg.inv(K) @ P2[:3, 3]
    T_cam2_cam0 = np.eye(4)
    T_cam2_cam0[:3, 3] = t_extra
    return dict(K=K, P2=P2, T_cam_imu=T_cam2_cam0 @ T_cam_imu)


# --------------------------------------------------- relative camera motion
def camera_poses(oxts_path: str, calib_path: str):
    """(N,4,4) world->camera transforms, plus K."""
    c = load_calib(calib_path)
    T_w_imu = load_oxts_poses(oxts_path)                # IMU -> world
    T_cam_imu = c["T_cam_imu"]
    T_w_cam = np.einsum("nij,jk->nik", T_w_imu, np.linalg.inv(T_cam_imu))
    return T_w_cam, c["K"]


def relative_motion(T_w_cam: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """(R, t) mapping a point in camera frame k-1 into camera frame k."""
    T_rel = np.linalg.inv(T_w_cam[k]) @ T_w_cam[k - 1]
    return T_rel[:3, :3], T_rel[:3, 3]


def rotation_homography(K: np.ndarray, R: np.ndarray) -> np.ndarray:
    """The image warp induced by camera rotation alone. EXACT and depth-free."""
    H = K @ R @ np.linalg.inv(K)
    return H / H[2, 2]


# ----------------------------------------------------- labels (3D -> depth)
KITTI_CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Person_sitting",
                 "Cyclist", "Tram", "Misc")


def load_labels(path: str) -> dict[int, list[dict]]:
    """KITTI tracking label_02 rows, grouped by frame.

    frame track_id type truncated occluded alpha x1 y1 x2 y2 h w l X Y Z ry
    (X,Y,Z) is the 3D box centre in **rectified camera** coordinates -> depth Z.
    """
    out: dict[int, list[dict]] = {}
    if not os.path.exists(path):
        return out
    for line in open(path):
        p = line.split()
        if len(p) < 17:
            continue
        cls = p[2]
        if cls == "DontCare":
            continue
        f = int(p[0])
        out.setdefault(f, []).append(dict(
            track_id=int(p[1]), cls=cls,
            truncated=float(p[3]), occluded=int(float(p[4])),
            tlbr=np.array([float(p[6]), float(p[7]), float(p[8]), float(p[9])]),
            dims=np.array([float(p[10]), float(p[11]), float(p[12])]),
            xyz=np.array([float(p[13]), float(p[14]), float(p[15])]),
            ry=float(p[16]),
        ))
    return out


# ------------------------------------------------------------ the measurement
def project(K: np.ndarray, X: np.ndarray) -> np.ndarray:
    """(N,3) camera-frame points -> (N,2) pixels."""
    x = (K @ X.T).T
    return x[:, :2] / x[:, 2:3]


def exact_displacement(K, R, t, X_prev: np.ndarray) -> np.ndarray:
    """Where a 3D point at X_prev (camera frame k-1) actually lands in frame k."""
    X_curr = (R @ X_prev.T).T + t
    return project(K, X_curr)


def homography_prediction(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    p = np.concatenate([pts, np.ones((len(pts), 1))], axis=1)
    q = (H @ p.T).T
    return q[:, :2] / q[:, 2:3]


def parallax_residual(K, R, t, X_prev: np.ndarray) -> dict:
    """How far a rotation-only homography is from the truth, per point.

    This is the component of apparent motion that **no** 2D warp can remove,
    because it depends on depth. It is zero for a purely rotating camera and
    grows with translation / inverse depth.
    """
    if len(X_prev) == 0:
        return dict(n=0)
    pts_prev = project(K, X_prev)
    pts_true = exact_displacement(K, R, t, X_prev)
    H_rot = rotation_homography(K, R)
    pts_rot = homography_prediction(H_rot, pts_prev)
    err = np.linalg.norm(pts_true - pts_rot, axis=1)
    return dict(n=len(err), median=float(np.median(err)),
                p90=float(np.percentile(err, 90)), max=float(err.max()),
                mean=float(err.mean()), depth_median=float(np.median(X_prev[:, 2])),
                translation_norm=float(np.linalg.norm(t)),
                rotation_deg=float(np.degrees(np.arccos(
                    np.clip((np.trace(R) - 1) / 2, -1, 1)))),
                per_point=err)


def best_similarity(src: np.ndarray, dst: np.ndarray) -> np.ndarray | None:
    """Least-squares 4-DOF similarity fitting src->dst. The best any
    BoT-SORT-style compensator could possibly do for this frame, given perfect
    correspondences on the tracked objects themselves."""
    import cv2
    if len(src) < 2:
        return None
    H, _ = cv2.estimateAffinePartial2D(
        src.astype(np.float32).reshape(-1, 1, 2),
        dst.astype(np.float32).reshape(-1, 1, 2),
        method=cv2.LMEDS)
    return H
