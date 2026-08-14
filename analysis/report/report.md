# Is MLB pitching becoming homogeneous?

*Testing whether modern pitch design has narrowed the range of pitches thrown in
Major League Baseball, and whether unusual pitches gain effectiveness from being
rare. Regular seasons 2021-2025.*

> **Status:** results sections are populated by the study scripts; this draft
> carries the hypothesis, data and method sections.

## The hypothesis

Pitch development has become an engineering discipline. Every organisation now
has access to the same tracking data, the same stuff models, and broadly the
same training methods, and those models score a pitch from its physical
characteristics alone — velocity, movement, spin, release. If everyone
optimises the same objective over the same variables, the optimum is a point,
and arsenals should be drawn toward it.

The hypothesis under test has two parts:

1. **Convergence.** The distribution of pitch characteristics across MLB
   pitchers has narrowed over the past five seasons.
2. **A neglected margin.** Because hitters see mostly standard shapes, pitches
   that sit outside the norm should be disproportionately effective — and some
   pitch types or regions of the shape space may have been abandoned despite
   still working.

The second claim is the one with practical consequences, and it is the harder
of the two to establish, because unusual pitches are thrown by a non-random set
of pitchers.

## Data

Pitch-by-pitch Statcast data for every regular-season game, 2021-2025, fetched
from Baseball Savant by this repository's `statcast` CLI and analysed from a
year-partitioned parquet snapshot. Postseason and spring training are excluded
so that the population is consistent across seasons.

Each pitch carries release speed, spin rate and spin axis, the two movement
components, release position and extension, arm angle, plate location, count
state, and the outcome fields used here: the pitch description (from which
whiff, called strike and CSW are derived), the change in run expectancy, and
expected wOBA on contact.

### Pitch shape

Movement is converted to inches and expressed as induced vertical break (IVB)
and horizontal break. All horizontal quantities — break and release side — are
sign-normalised so that **positive always means arm-side**, for left- and
right-handers alike. Without this, pooling the two would manufacture
bimodality in every horizontal variable and make the league look far more
diverse than it is. The feature build refuses to run if sinkers do not show
strong arm-side break for both hands.

### Pitch families, and why not pitch types

Savant's classifier is not stable across these five seasons: the sweeper
(`ST`) and slurve (`SV`) labels were introduced for 2023 out of what had been
`SL`. A trend computed on raw pitch types would mix a real behavioural change
with a relabelling artefact. Primary analyses therefore use seven stable
families — four-seam, sinker, cutter, slider/sweeper, curveball, changeup,
splitter — with knuckleballs, eephuses and pitchouts excluded.

### The unit of analysis

Most of this report works at the **arsenal-row** grain: one row per pitcher,
pitch family and season, for combinations with at least 100 pitches. This is
the grain at which a pitch exists as a designed object — a pitcher's slider in
2024 is one thing, thrown many times. Measuring dispersion over raw pitches
instead would let a 3,000-pitch starter count ten times as much as a 300-pitch
reliever, and would confuse *usage* concentrating with *pitchers* converging.

Two other grains appear: the pitch itself, for outcome models and the
familiarity study; and shape cells (2 mph x 4 in x 4 in blocks of the
velocity-movement space) for the scarcity panel.

## Method

Seven studies, ordered from descriptive to identifying.

| | Study | Question |
|---|---|---|
| S1 | Dispersion trends | Is the spread of each characteristic shrinking? |
| S2 | Shape-space volume | Is the multivariate cloud shrinking, even where single characteristics are stable? |
| S3 | Pitcher convergence | Are individual pitchers moving toward each other and toward the league centre? |
| S4 | Pitch ecology | What is thrown, and what is it worth? |
| S5 | Outlier effectiveness | Do unusual pitches perform better? |
| S6 | Scarcity panel | Holding the shape fixed, does becoming rarer make it better? |
| S7 | Batter familiarity | Holding the pitch fixed, does recent exposure make it worse? |

**Uncertainty.** Bootstrap intervals resample *pitchers*, not pitches, because
a pitcher contributes many correlated observations and pitch-level resampling
would produce intervals several times too narrow. Families of related tests
are controlled with Benjamini-Hochberg at q = 0.10, and each study declares a
single primary endpoint so that no conclusion rests on the best of fifty
comparisons.

**Noisy rates are shrunk.** Pitcher-season outcome rates are shrunk toward the
family-season mean with empirical Bayes — beta-binomial for rates,
normal-normal for run value — so that a 100-pitch splitter with a freak run
value does not drive the uniqueness gradient.

**What each design can support.** S1-S4 are descriptive. S5 is associational
by construction: uniqueness is a deterministic function of the same shape
features any model would use, so it cannot be "extra information" in a
predictive sense, and unusual pitches are thrown by a non-random set of
pitchers. The identifying leverage sits in S6, which holds a shape fixed and
varies only how often the league throws it, and in S7, which holds the pitch
fixed and varies how much a given hitter has recently seen that shape.

## Confounders

| Event | Effect | Handling |
|---|---|---|
| Foreign-substance enforcement, 21 June 2021 | League four-seam spin fell about 80 rpm; roughly three-quarters of pitchers lost spin | Spin comparisons anchored on 2021 are re-run using only post-enforcement data |
| Pitch clock and shift ban, 2023 | Shifts the run environment, not pitch shape | Year fixed effects; outcomes expressed relative to each season's league mean |
| Ball construction drift | Same | Same |
| `arm_angle` coverage | Derived field, published later and back-filled | Coverage measured per season; enters the feature vector only if adequate everywhere |
| Bat tracking (2023+) | Only covers competitive swings from 2023 | Not used in any cross-season comparison |
| Sweeper/slurve labels (2023+) | Classifier change, not a behaviour change | Family-level primary analyses; per-type results reported separately with the caveat |

## Reproducing

```bash
pip install -e ".[analysis]"
statcast init && bash scripts/backfill_study.sh
python -m analysis.run_all
```

Every table below has a matching CSV in `analysis/results/`, and every script
writes a `*_meta.json` sidecar recording the git commit and parameters used.
Prior work is annotated in [`literature.md`](literature.md).
