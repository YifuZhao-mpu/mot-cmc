# Representative frames

**Every image here is real benchmark data.** Nothing is a stand-in from another project's
demo assets, and no depth map is an illustrative render: the two KITTI depth maps are the
output of the same Depth-Anything-V2 Metric VKITTI checkpoint, at the same input size, that
produces the estimated-depth rows in the paper.

## KITTI — the case the paper is about

| File | What it shows |
|---|---|
| `kitti_0011_000131.png` | sequence 0011, frame 131, unmodified |
| `kitti_0011_000131_depths.png` | the same frame with its annotated objects and their true depths: **5, 9, 12, 19, 29, 30, 37 and 63 m** — thirteen objects spanning 5 to 65 m, a 13.8× range within one frame |
| `kitti_0011_000131_depth.png` | Depth-Anything-V2 Metric VKITTI output, 4.1 to 79.6 m, inferno colour map, near bright |
| `kitti_0011_000131_frame_and_depth.png` | the two stacked |
| `kitti_0011_000131_depth_metres.npy` | the same depth map as float32 metres, for anyone who wants the numbers |
| `kitti_0013_000088*` | the same set for sequence 0013, frame 88: ten objects, 3 to 41 m, 13.1×. Pedestrians (red) sit at 3, 6, 6, 13 and 20 m while the vehicles (blue) are at 29 and 41 m, so the two classes occupy different depth ranges in one frame |
| `kitti_depth_spread_pair.png` | both frames stacked with their measured numbers, 1242 × 874 |
| `kitti_depth_spread_side_by_side.png` | the same two side by side, 2496 × 437 |

These two frames were not chosen by eye. They are the frames where the compensator the
tracker ships leaves the largest within-frame residual spread and the depth-aware homography
removes it: **114.1 px → 3.27 px** on 0011/131 and **116.6 px → 8.9 px** on 0013/88, from the
per-frame measurements in `04_experiments/kitti_global_family_v2.csv`. The annotated depths
are the reason: a single 2D warp has one answer for targets that are 13× apart in depth.

## What the deployed estimator actually tracks

These are not drawn by hand. The points and vectors are the output of the paper's own
instrumented estimator, run on the real consecutive frame pair, with the parameters the tracker
ships: `goodFeaturesToTrack(maxCorners=1000, qualityLevel=0.01, minDistance=1, blockSize=3)` on
the half-resolution frame, pyramidal Lucas–Kanade, then a 4-DOF similarity by RANSAC.

| File | Measured |
|---|---|
| `mot17_13_000100_gmc.jpg` | MOT17-13, frames 99→100: **994 inliers of 1,000 tracked**, median flow 3.8 px, transfer residual 0.657 px |
| `kitti_0011_000131_gmc.png` | KITTI 0011, frames 130→131: **705 inliers of 969 tracked**, median flow 4.4 px, transfer residual 1.592 px |

Cyan arrows are the measured optical flow of the points RANSAC kept; red dots are the points it
rejected. On KITTI the rejected points are not scattered at random. They sit on the parked cars
along the right kerb and on the near road surface — the closest surfaces in the frame, where
parallax is largest. A 4-DOF similarity cannot carry points at 5 m and points at 60 m at the
same time, so it discards the near ones. That is the same limitation the within-frame spread
measures, visible directly.

## The pedestrian benchmarks — why a shared warp is enough there

| File | What it shows |
|---|---|
| `mot17_13_000100.jpg` | MOT17-13, moving camera, pedestrians at near-uniform depth |
| `mot17_04_000100.jpg` | MOT17-04, static camera — the control that validates the oracle-warp instrument |
| `mot20_02_000100.jpg` | MOT20-02, dense crowd, static camera |
| `uavdt_M0101_000100.jpg` | UAVDT M0101, aerial; high nadir-ish viewing puts the scene at nearly uniform depth, which is the condition under which one global warp is exact |

## Provenance

Frames come from the benchmark archives listed in `99_artifacts/RELEASE/DATA.md`, at the paths
shown above; they are not redistributed with the release. The depth maps were produced on this
machine with `04_experiments/weights/depth_anything_v2_metric_vkitti_vitl.pth`, encoder `vitl`,
`max_depth` 80, input size 518 — the configuration the paper uses throughout.
