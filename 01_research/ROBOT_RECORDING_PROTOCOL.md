# Controlled Robot Recording Protocol

**Purpose**: produce the one thing MOT17/MOT20 cannot provide — **ground-truth camera motion,
time-synchronised with the frames** — so that compensation reliability can be validated directly
rather than only through its downstream effect.

**Division of labour** (as agreed): this document, the annotation spec, the synchronisation
procedure and the evaluation scripts are delivered by the pipeline. Physical recording and
annotation are executed by the user.

**Status**: v1, 2026-09-20. Revise after the first pilot session — do not record the full set
before the pilot passes §7.

---

## 1. Why this dataset exists (read before designing around it)

On MOT17/MOT20 the project can only measure *disagreement between two estimates* (I1 oracle
contrast). The offline reference warp is better than the online one, but it is **not truth**, so
every attribution figure from public data is a lower bound (DA-CP1 R1).

Robot odometry breaks that ceiling. With a measured camera trajectory the project can state, for
the first time in this work:

- the **actual** compensation error, not an estimate of it;
- whether the reliability estimate `r` is calibrated against real error (is `r = 0.4` really
  twice as unreliable as `r = 0.8`?);
- whether ID switches disappear when the true warp replaces the estimated one.

**Design consequence**: odometry quality and synchronisation accuracy matter more than scene
realism, scale, or visual variety. A small, rigorously measured dataset is worth far more here
than a large, loosely measured one. Do not trade §3 for §4.

---

## 2. Hardware and minimum requirements

| Item | Requirement | Why |
|---|---|---|
| Camera | Global shutter strongly preferred; ≥30 fps; fixed focus, fixed exposure, fixed white balance | Rolling shutter injects a motion-dependent warp that is *not* camera pose, and would be silently absorbed into the "compensation error" |
| Mount | Rigid to the robot; no gimbal, no image stabilisation, no EIS | Stabilisation is itself an uncontrolled compensation and destroys the ground truth |
| Odometry | Wheel odometry + IMU at ≥100 Hz, or a motion-capture system, or a well-calibrated VIO | Supplies the reference warp `A*_k` |
| Sync | Hardware trigger preferred; otherwise a measured offset (§3) | An unstated camera↔odometry offset silently destroys the "controlled" claim (DA-CP1 m3) |
| Calibration | Intrinsics + distortion (checkerboard, ≥20 views), camera↔robot extrinsics | Needed to convert robot pose into an image-plane warp |
| Targets | ≥4 people, or ≥4 mobile robots/carts with distinguishable and, separately, *deliberately similar* appearance | Appearance-similar targets are what stress the association |

**Turn OFF, and record that you did**: auto-exposure, auto-white-balance, auto-focus,
electronic/optical stabilisation, in-camera denoising, variable bitrate compression.
Record RAW or visually lossless. Compression artefacts change keypoint statistics, which is the
exact signal under study.

---

## 3. Synchronisation — the step most likely to invalidate the dataset

Do this first, and report the residual in milliseconds in the paper.

**Preferred**: hardware trigger, camera exposure pulse timestamped in the odometry clock.

**Fallback (measure, don't assume)**:
1. Place the robot facing a high-contrast static target.
2. Command a sharp yaw step (fast start, fast stop), repeat ≥20 times.
3. Estimate per-frame image-plane translation from the video (the project's own reference-warp
   estimator can do this).
4. Cross-correlate the image-motion signal against the odometry angular-rate signal; the lag at
   peak correlation is the offset.
5. Report: offset (ms), residual jitter (std of the per-event lag, ms), and the number of events.

**Acceptance**: residual jitter < 1/4 frame interval (< 8 ms at 30 fps). If it is larger, the
sequence is labelled `sync_uncertain` and excluded from ground-truth-warp analysis — it may still
be used for IDSW counting.

---

## 4. Experimental design (factorial)

Two factors crossed. Each cell recorded ≥3 times (different target choreography), ≥60 s each.

### Factor A — camera motion (6 levels)
| Level | Description | Targets the failure mode |
|---|---|---|
| A1 static | robot stationary | control; must show near-identity warp and `r ≈ 1` |
| A2 pan | smooth yaw, constant rate ~10–20 °/s | baseline moving-camera case |
| A3 translate | straight-line motion, constant speed | parallax; the similarity model is *wrong* here by construction — valuable |
| A4 vibrate | stationary base with induced high-frequency shake | MOT20's "vibrations or drifts caused by the wind" case, named in BoT-SORT §3.2 |
| A5 rapid turn | fast yaw step, ≥60 °/s, with start/stop | large inter-frame displacement, temporal-consistency stress |
| A6 mixed | scripted combination of A2–A5 | realism check |

### Factor B — background (4 levels)
| Level | Description | Targets |
|---|---|---|
| B1 textured | rich, static, well-lit background | control |
| B2 low-texture | blank wall / uniform floor | the mode that was catastrophic in the synthetic study (median error 105 px) |
| B3 repetitive | tiling, railings, regular façade | produced a **false alarm** in the synthetic study (`ρ`=0.77 at 0.076 px error) — must be included precisely because it is where the estimator was wrong |
| B4 foreground-dominated | targets occupy >50 % of frame area | the mode that matched MOT17-05 (median 57 % of GMC inliers land on pedestrians) |

### Factor C — target behaviour (recorded as annotation, not a separate cell)
Each take must contain, and be labelled with, the frame ranges of:
- **crossing**: two targets whose boxes overlap while moving in opposite directions;
- **occlusion**: a target fully hidden ≥15 frames then reappearing;
- **appearance collision**: ≥2 targets in visually near-identical clothing;
- **re-entry**: a target leaving and re-entering the frame.

**Minimum viable set** if time is short: A1, A4, A5 × B1, B2, B4 = 9 cells × 3 takes = 27 takes.
Record B3 even in the minimal set — it is the estimator's known weak point and omitting it would
look like avoiding a negative result.

---

## 5. Annotation specification

**Format**: MOT Challenge `gt.txt`, one row per box per frame:

```
<frame>,<id>,<bb_left>,<bb_top>,<bb_width>,<bb_height>,<conf>,<class>,<visibility>
```
- `frame`: 1-indexed, contiguous, matching the image filenames `img1/%06d.jpg`
- `id`: globally unique **within a take**, stable across full occlusion and re-entry
  (this is the entire point — an id must NOT be recycled after a gap)
- `conf`: 1 for all ground-truth rows
- `class`: 1 (pedestrian) — keep the MOT17 class numbering
- `visibility`: [0,1], estimated fraction visible. **Required**, not optional: occlusion-recovery
  analysis is stratified by it.

**Additional per-take files** (project-specific, alongside `gt/`):
- `odom/pose.txt`: `timestamp_ns, x, y, z, qx, qy, qz, qw` at native rate
- `sync/offset.json`: `{"offset_ms": ..., "jitter_ms": ..., "n_events": ..., "method": ...}`
- `calib/intrinsics.yml`, `calib/extrinsics.yml`
- `meta.json`: factor levels (A, B), lighting, camera settings, and the event ranges from §4-C

**Annotation quality control**:
- Every take double-annotated by two annotators on ≥10 % of frames; report IoU agreement and
  id-assignment agreement. Disagreement on *identity* is the metric that matters — report it.
- Do not interpolate identities through full occlusions automatically; a human must assert them.
- Annotators must not see tracker output. Ever.

---

## 6. Derived ground truth — how odometry becomes a reference warp

For a camera undergoing pure rotation, the inter-frame image warp is a homography that depends
only on rotation and intrinsics:

```
H_k = K R_k K^-1 ,   R_k = R(t_k) R(t_{k-1})^-1
```

For translation, parallax makes a single global warp **wrong by construction** — there is no exact
2D warp. That is not a flaw in the protocol; condition A3 exists precisely to quantify how large
the model error is, and to show whether the reliability estimate correctly flags a case where the
model (not the estimate) is inadequate. Report A3 separately and never pool it with A2/A4/A5.

Deliverable script (supplied by the pipeline): `odom_to_warp.py` — interpolates odometry to frame
timestamps using the measured offset, composes `H_k`, and projects it to the 4-DOF similarity the
online solver fits, so the comparison is like-for-like.

---

## 7. Pilot acceptance checklist — pass this before the full session

Record ONE take of A1/B1 and ONE of A5/B2, then verify:

1. `sync` jitter < 8 ms and the offset is stable across the take.
2. On A1/B1 (static camera): the online GMC returns near-identity and `r > 0.9` for >95 % of
   frames. If the estimator flags a stationary camera as unreliable, the pilot has found a bug —
   fix it before recording more.
3. On A5/B2 (rapid turn, blank wall): `r` drops measurably. If it does not, the synthetic
   `low_texture` finding does not transfer to this rig and the whole design needs revisiting.
4. Odometry-derived warp and the offline reference warp agree to within a few pixels on A1/B1.
   Large disagreement on a *static* take means calibration or sync is wrong, not that the method
   is interesting.
5. Annotation round-trip: one take annotated, loaded by TrackEval without error.

**Do not proceed past a failed pilot.** A full recording session built on an unmeasured sync
offset produces data that cannot be used for the claim it was collected to support.

---

## 8. Ethics and consent

- Human participants: informed written consent covering **recording, storage, analysis and
  publication of images**. Obtain institutional review (IRB/ethics committee) before recording,
  not after.
- Consent must separately cover publication of frames in a paper and public release of the dataset;
  these are different permissions and participants may grant one and not the other.
- Provide withdrawal: a participant may request deletion; the take must then be removable without
  breaking the dataset (hence per-take directories).
- Recruit only adults; no bystanders in frame — use a closed area with signage.
- Dual-use: pedestrian tracking is surveillance-adjacent. The manuscript carries a Responsible Use
  Statement; the dataset licence should restrict use to research.
- If consent for public release is not obtained, report results on the data and release only
  derived statistics — say so explicitly rather than implying a release that will not happen.

---

## 9. What the paper will do with this

| Analysis | Needs |
|---|---|
| **Direct calibration of `r`** — plot true compensation error vs `r`, per factor cell | odometry + sync |
| **True oracle contrast** — IDSW under estimated vs true warp | odometry + annotation |
| **False-alarm audit** — does `r` drop on A1 (static) or B3 (repetitive) where it should not? | A1, B3 cells |
| **Occlusion recovery** — id preserved across ≥15-frame gaps | §4-C labels + `visibility` |
| **Model-error case** — A3 translation, where no 2D warp is correct | A3 cell, reported separately |

The false-alarm audit is as important as the success case. The synthetic study already found that
`ρ` alone false-alarms on repetitive patterns; if that reproduces on real data it belongs in the
paper, not in a drawer.
