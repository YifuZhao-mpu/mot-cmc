# Stage 6 — Process Summary

**Project**: Multi-Object Tracking under Camera Motion Uncertainty → *Camera-Motion Compensation Is Not the Bottleneck*
**Run**: ARS academic-pipeline, `full` mode · 2026-09-20 → 2026-09-25
**Outcome**: submission package assembled; five author-action items outstanding

---

## 1. What the project set out to do, and what it produced

The brief asked for a method: assess whether background motion compensation is reliable, then let
that reliability decide how much weight motion prediction and appearance matching should carry,
rather than applying a wrong compensation to every target.

The instruments built to justify that method refuted it. Compensation on MOT17, MOT20 and UAVDT is
accurate, its error is predictable for free, and that error is too small to change association
outcomes — a perfect warp is worth −0.04 HOTA with a 95 % upper bound of +0.05 on the sequences
that actually have camera motion. There was nothing for a reliability gate to gate.

The brief's second half survived, for a different reason than it gave. "Do not apply a wrong
compensation to every target" is right on a translating camera, but not because the estimate fails:
because the warp takes no depth argument. Supplying depth to a **global** homography removes 82 % of
the within-frame residual spread and beats the compensator BoT-SORT ships on KITTI cars. The
per-target treatment the brief imagined — and that we pursued for three rounds — adds nothing on
top of that, and in the configuration that appeared to win it was reading ground-truth association.

## 2. What the pipeline's gates actually caught

| Gate | Caught |
|---|---|
| S2 baseline gate | nothing — the baseline reproduced to 0.01 HOTA, which is what a gate should mostly do |
| K5 power gate | **the original hypothesis**. It failed, the pre-committed response was honoured, and the MOT17 ablation matrix that would have tuned a method into an apparent win was never run |
| DA-CP1 / DA-CP2 (adversarial checkpoints) | the six-signal estimator's reversal; the 91.4 % homography artefact; the demand for bootstrap intervals that withdrew three claims |
| Stage 2.5 integrity | **two fabricated DOIs** resolving to unrelated papers; an unstated denominator; a prose figure that did not reproduce; two estimators used in adjacent sentences |
| Stage 3 five-seat panel | the comparator weaker than the shipped compensator; the mislabelled per-sequence rate; effective sample size 3.05 of 21; the covariance argument that does not compose; four bodies of uncited prior art including a survey the paper itself quoted |
| Stage 3′ re-review | **the two defects that mattered most** (below) |
| Stage 4.5 final integrity | one wording imprecision |

## 3. What the gates missed, and what found it

Three times this project reached a conclusion that was an artefact of how an experiment was
constructed, and **none of the three was caught by a checklist**:

| Artefact | Effect | Found by |
|---|---|---|
| A homography fitted to the displacements it was scored against | "a homography absorbs 91.4 % of the spread" | our own follow-up measurement |
| A static grid placed at a single depth, making the induced map a plane homography exactly | "a richer warp family is not the fix" (2.3 %) | a reviewer, by reading the code |
| A warp bundle left at the identity on 35.7 % of moving frames, gated on ground-truth annotation count | "geometric accuracy of a shared warp does not predict tracking" | a reviewer, by **running** the code |

The third reversed the paper's central new claim and changed its prescription. The second and third
were both found by an adversarial reader with execution access, not by verification of values —
`verify_numbers.py` passed 486/486 while the configuration it was checking was switched off on a
third of the frames it was supposed to compensate.

**The lesson, stated as a process finding.** A value-level checker verifies transcription. The
failures that actually moved this paper's conclusions were *provenance* failures: which run feeds
which table, and whether a treatment was applied at all. The verifier now carries provenance checks
— warp-bundle identity coverage, run-to-table mapping, and whether the oracle rows come from the
strict configuration — and they exist because both Critical defects would have passed without them.

## 4. Claims withdrawn over the course of the work

Seven, all recorded in §9.4 and Supplementary S2 rather than silently replaced.

| Withdrawn | Replaced by |
|---|---|
| The original reliability-gating hypothesis | the bound on what compensation accuracy is worth |
| "±0.104 across 7/7 hyperparameter settings" as headline support | sequence-level bootstrap intervals |
| "A homography absorbs 91.4 % of the within-frame spread" | 2.3 % (itself later withdrawn) |
| "+0.686 HOTA over the best global model" | interval crosses zero |
| "The car gain flips sign under leave-one-out" | artefact of mixing two estimators |
| "The value of perfecting compensation is not positive in either configuration" | +0.19 [+0.05, +0.52] on moving sequences with appearance |
| "A richer warp family is not the fix" (2.3 %) | it is: 82 %, and the remedy is a global homography with depth |
| "Per-target compensation is the prescription" | give the shared warp depth; per-target adds nothing on top |

Two further corrections were withheld rather than reported: the first KITTI oracle specification
(which double-counted object motion) and the second (which applied translation only) never had
their numbers published.

## 5. What the record supports, and what it does not

**Supported**: the bound; the two instruments; the KITTI quantification; the depth diagnosis and
its deployable remedy on cars; the placebo that rules out perturbation magnitude; the reproduction
of BoT-SORT's published compensation delta to within 0.06 HOTA.

**Not supported, and stated as such in the paper**: the homography's advantage over the shipped
compensator on pedestrians; any measurement of the shared-warp limitation outside KITTI; anything
about the method under an appearance channel on KITTI; any MOTChallenge test-set number.

**Not attempted**: the controlled robot study. The protocol was delivered in Stage 1 and the
recording was the user's to perform; it was not executed, and the two failure conditions it was
designed to create — low texture and foreground domination by moving occluders — are precisely the
ones §4.4 shows the public benchmarks lack. That remains the most informative missing experiment.

## 6. Cost and shape of the run

Six days. Four benchmarks, 61 tracker runs, 21 result CSVs, 44 scripts, ~277 released files.
Two adversarial design checkpoints, one five-seat review panel, one re-review pair, two integrity
gates. The single most productive component was not any gate but the practice of giving a critic
the code and the data and asking them to run it.

## 7. If this were run again

1. **Write the provenance checks before the value checks.** Every defect that changed a conclusion
   here was a configuration silently not doing what its label said.
2. **Assume any experiment that confirms the current hypothesis is constructed to.** Three of three
   artefacts in this project pointed the way the authors were already leaning.
3. **Ask the reviewer to execute, not to read.** Two Criticals came from `np.load` on a released
   artefact, and neither was visible in the manuscript.
4. **Run the literature check before the experiments, not after.** The 2026 survey that already
   ablates camera-motion compensation was cited in this paper for a different purpose for three
   drafts before anyone noticed it had run the experiment.
