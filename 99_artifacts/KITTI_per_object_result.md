# KITTI — the regime MOT17 and MOT20 do not contain

**Date**: 2026-09-21 · **Data**: KITTI tracking, 21 training sequences
**Instrument**: ground-truth ego-motion (oxts GPS/IMU) + full calibration chain + 3D object
labels. **No images, no detector, no tracker.** The measurement is a property of the scene
geometry and the compensation *model*, not of any implementation.

This is the first measurement in the project against **true** camera motion rather than
against a better estimate. Everything reported on MOT17 was a lower bound for that reason.

---

## 1. What is compared

For every object present in consecutive frames, its exact image displacement is computed
from its annotated 3D position and the true inter-frame camera motion. Three compensation
models are then asked to predict that displacement:

| model | what it is |
|---|---|
| identity | no compensation |
| rotation homography `K R K⁻¹` | the exact warp for the rotational component, **given the true rotation** |
| **best-fit similarity** | the 4-DOF transform BoT-SORT's GMC estimates, fitted by least squares **to the objects' own true displacements** |

The third is an **oracle**: a real GMC fits to background keypoints and never sees these
correspondences. No online 4-DOF compensator can beat it. Its residual is therefore the
floor — the part of the apparent motion the compensation *model* cannot express, however
well it is estimated.

## 2. Median residual, 6,416 frames

| model | median | p90 | max |
|---|---|---|---|
| no compensation | 4.196 px | 15.367 | 127.8 |
| rotation homography (true R) | 3.621 px | 12.917 | 128.6 |
| **best-fit similarity (oracle)** | **0.101 px** | **2.146** | **48.6** |

**A 4-DOF similarity fits KITTI better than expected.** Forward translation produces
approximately radial expansion, and a similarity's uniform-scale term absorbs most of it.
An earlier single-sequence reading compared against the rotation-only homography and
overstated the model error; the corrected figure is the one above.

The information is not in the median. It is in the spread.

## 3. The finding: the residual is per-OBJECT, not per-frame

Within-frame spread of the residual **after oracle compensation**, moving frames only:

| | median | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| spread across objects (px) | **5.878** | 14.868 | 30.404 | 43.765 | 73.005 | **473.5** |

| objects in the same frame disagree by more than | share of moving frames |
|---|---|
| 1 px | **85.92 %** |
| 2 px | **73.65 %** |
| 5 px | **54.31 %** |
| 10 px | **36.22 %** |

**In over half of all moving frames, objects in the same image require corrections that
differ by more than five pixels.** One global warp cannot serve them, no matter how it is
estimated.

**The spread is depth-driven, as parallax predicts.** Per-frame Spearman correlation between
object depth and residual: median **−0.400**, negative in **75.3 %** of frames. Nearer
objects carry the larger residual.

## 4. Does it reach the association gate?

Using each object's true box size and BoT-SORT's `theta_iou = 0.5`:

| | KITTI (irreducible residual) | MOT17 (compensation error) |
|---|---|---|
| moving frames with ≥1 object pushed below the gate | **10.00 %** | — |
| object-frames gated out | **488 / 23,443 = 2.082 %** | **34 / 109,955 = 0.031 %** |

**67× higher than MOT17 — and on KITTI this is what remains after *perfect* global
compensation**, whereas the MOT17 figure is the total effect of imperfect compensation.

It concentrates where the geometry says it must: the worst-affected object has a median
depth of 6–47 m and a median box width of 27–281 px, across 16 of 21 sequences.

## 5. What this establishes

1. **The failure regime is real and it is not in the pedestrian benchmarks.** MOT17 and
   MOT20 contain neither the texture collapse the literature describes nor a material
   translation component. KITTI contains the latter in abundance.

2. **The failure is structural, not estimation noise.** On MOT17 the question was whether
   the compensator is accurate enough. On KITTI a perfect 4-DOF compensator is still wrong
   for 2.08 % of object-frames, because a single 2D warp cannot represent depth-dependent
   motion. Improving the estimator cannot fix this.

3. **Per-target compensation is a necessity here, not a refinement.** The original project
   proposal — *"when compensation fails, reduce its influence rather than applying a wrong
   compensation to every target"* — is not measurable on MOT17, where the within-frame
   spread is negligible. On KITTI it is the dominant effect.

## 6. What this does NOT yet establish

- That a tracker built on this observation improves tracking metrics on KITTI. The
  geometry says there is room; that is a bound, not a result. The tracking experiment is
  the next step and is subject to its own power gate.
- That monocular depth (which a real tracker would have to estimate, not read from labels)
  is accurate enough to exploit the room. The 3D labels used here are ground truth.
- Anything about UAV footage; UAVDT is downloading and is rotation-dominated, so it may
  behave more like MOT17 than like KITTI. That is an open question, not a prediction.
