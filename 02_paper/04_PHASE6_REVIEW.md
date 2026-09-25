# Phase 6 — In-pair peer review

**Date**: 2026-09-23 · **Manuscript under review**: `02_paper/manuscript.md` at the close of Phase 5
**Protocol**: v3.6.6 generator–evaluator contract. Phase 6a was written before re-reading the
draft; Phase 6b after. Revision loops used: **1 of 2**.

---

## Phase 6a — Pre-commitment (written paper-blind)

### Contract paraphrase

Review an IJCV measurement study whose headline claim is negative. The paper must be judged on
whether its claims are bounded by its evidence, not on whether the result is interesting. A
measurement paper that overstates a null is worse than one that overstates a positive, because
a null invites the reader to stop looking.

### Scoring plan

| Dimension | What I will look for | Blocks | Warns |
|---|---|---|---|
| D1 Evidence sufficiency | every claim traceable to a released measurement | a number with no source | a number whose source is an artefact rather than a script |
| D2 Uncertainty discipline | intervals wherever a comparison is made, on **negative** claims too | a negative claim asserted from a point estimate alone | intervals present but not interpreted |
| D3 Scope honesty | the paper's own generality limits stated where the claim is made, not only in §9 | a claim generalised past its benchmark | a limitation stated only in the limitations section |
| D4 Falsifiability of the null | does the paper say what would have changed its mind? | no stated condition under which the null would fail | condition stated but not measured |
| D5 Mechanism | positive claims accompanied by a per-frame or per-object mechanism check | metric delta + narrative only | mechanism shown for one class, asserted for another |
| D6 Submission form | figures and tables cited in text; references resolvable; numbering consistent | unresolvable reference | uncited float |

`[PRE-COMMITMENT-ACKNOWLEDGED]`

---

## Phase 6b — Review

### Dimension scores

| Dimension | Score | Note |
|---|---|---|
| D1 Evidence sufficiency | 5/5 | Every table regenerated from source during drafting; two ad-hoc measurements were turned into committed scripts rather than cited from a notebook |
| D2 Uncertainty discipline | **3/5 → 5/5 after revision** | **The asymmetry below was the review's main finding** |
| D3 Scope honesty | **3/5 → 5/5 after revision** | MOT20 was being carried by the same sentence as MOT17 despite having no downstream test |
| D4 Falsifiability of the null | 4/5 | §4.4 and §9.2 name the conditions (low texture, foreground domination with moving occluders) and state that the robot protocol targets them; not executed |
| D5 Mechanism | 5/5 | §6.7 verifies per frame and the counter is validated against TrackEval; the car class is explicitly left without one |
| D6 Submission form | **2/5 → 5/5 after revision** | Zero figure citations and seven uncited tables in the reviewed draft |

### Failure condition checks

| Condition | Result |
|---|---|
| A negative claim asserted from a point estimate alone | **TRIGGERED — fixed** (F1 below) |
| A claim generalised past its benchmark | **TRIGGERED — fixed** (F2 below) |
| Unresolvable reference | not triggered (Phase 5a resolved all 17) |
| Uncited float | **TRIGGERED — fixed** (F3 below) |
| Metric delta presented as mechanism | not triggered |
| A number with no released source | not triggered |

### Review body

**F1 (Critical). The paper demanded confidence intervals of its positive result and not of its
negative one.** Every KITTI comparison carried a sequence-level bootstrap interval; the MOT17
axis — which carries the paper's headline claim — carried point estimates against a zero
run-to-run noise floor. A zero noise floor bounds run-to-run variation and says nothing about
the seven sequences. For a null, the upper end of the interval *is* the claim, and it was
missing.

*Resolution.* The same bootstrap was applied to the MOT17 axis (new §5.5, Table 5). The
95 % upper bound on the value of perfect compensation is **+0.49 HOTA** motion-only and
**+0.13 HOTA** with the appearance channel, and its interval is almost exactly the interval for
switching between two ordinary compensator implementations. The claim is now stronger than it
was, because a bound survives resampling and a point estimate does not.

The same analysis surfaced something the authors should not have hidden and have not: with only
seven sequences, the value of *having* compensation — which is certainly real — has a HOTA
interval that crosses zero in the motion-only configuration, because four of the seven sequences
are static. §5.5 reports this and draws the right conclusion from it: the tracking experiment is
the weakest of the three bounds, and the two large-sample bounds (109,955 pairs each) are what
carry §5.

**F2 (Major). MOT20 was being carried by MOT17's evidence.** Three sentences — §1.2
contribution 2, §2.4, and the displayed claim in §5.7 — named "MOT17, MOT20 and UAVDT" together.
MOT17 has three bounds including an oracle tracking experiment; UAVDT has a tracking experiment
but no oracle; MOT20 has only the reliability scan. The scan's finding is strong in its own
right — zero frames with a transfer residual above 2 px — but it is a claim about the absence of
the error, not about its consequences, and conflating the two is the kind of move this paper
criticises in §2.3.

*Resolution.* All three sentences now distinguish the evidence class, and §5.7 states plainly
that the MOT20 argument is the weaker kind even though it is the harder number to argue with.

**F3 (Major). No figure was cited in the text and seven of ten tables were not either.** Eight
figures existed with captions and none was referred to. This is a submission defect rather than a
scientific one, but it is one a desk editor returns.

*Resolution.* All 10 tables and all 8 figures now have in-text references at the point where
their content is discussed.

**F4 (Minor). Two identical-looking numbers.** Table 10 gives the car HOTA as 66.473 both with
estimated and with ground-truth depth. A reviewer will read that as a copy-paste error.

*Resolution.* Verified from the per-sequence output — 66.47275 and 66.47348 — and a sentence
now says so.

**F5 (Minor). The abstract used "established" twice in one clause** ("not established … could not
establish"). Reworded.

### What the review did not find

- No claim in the Part 7 prohibited list appears in the draft; the list was re-checked item by
  item after the revisions.
- No number without a released source.
- No case of a positive result reported without its interval.
- The title is a general statement supported by four benchmarks. This is a deliberate choice
  and §5.7 scopes it explicitly in the body. Flagged as an editorial question rather than a
  defect: an editor may ask for a narrower title, and the authors should be prepared to say why
  the general form is the honest one.

### Evaluator decision

**ACCEPT after the revisions above, which have been applied.** One revision loop used; the
second is unspent. Remaining known gaps are declared in §9.2 and are gaps in the work, not
defects in its reporting: no controlled robot study, ego-motion read from an onboard sensor
rather than estimated visually, a domain-matched depth checkpoint, and an unexplained class
difference.
