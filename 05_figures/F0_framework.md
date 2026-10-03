# Figure 1, the measurement pipeline

| File | What it is |
|---|---|
| `F0_framework.pdf` | the figure the build uses; embedded photographs resampled to 600 dpi at their printed size, 0.83 MB |
| `F0_framework_source.pdf` | the original export at full photographic resolution, 5.9 MB, kept as the master |
| `F0_framework.svg` | the editable vector source; it references the photographs rather than embedding them |

Every photograph in the figure is real benchmark data, and the panels that carry numbers carry
measured ones. The frames, the inlier and outlier points, the optical flow and the depth map come
from `06_examples/`, whose README records the sequence, the frame index and the settings used.

Regenerate the 600 dpi version from the master by resampling each embedded image to its printed
width at 600 dpi; the source is otherwise unmodified.
