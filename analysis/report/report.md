# Is modern pitch design making MLB pitchers throw the same?

**A study of 3.13 million regular-season pitches, 2021–2026**

## The short answer

Yes — locally, and at a cost the league is already paying.

Individual pitchers move toward the league-average version of their own pitch every single season. Arriving pitchers are already more typical than the veterans they replace. The multivariate space that pitch shapes occupy has measurably contracted. And shapes that gain popularity get measurably worse as they spread, because hitters adapt to what they see.

What is *not* happening is a collapse into one pitch. Arsenals are getting broader, not narrower — pitchers carry more pitch types, more evenly, than at any point in the window. The league is converging on a handful of **local templates** while the total number of templates holds up.

The most striking evidence arrived in the newest season. The changeup — the most-abandoned offspeed pitch in the study, and one of the two worst-performing families in 2025 — came back in 2026 and immediately posted its best numbers in six years.

---

## What was measured

Every regular-season pitch from 2021 through 2026, pulled from Baseball Savant into SQLite by this repo's `statcast` CLI.

The 2026 season is still being played. Because offspeed usage, velocity and roster composition all drift late in a year, **every season here is truncated to the same calendar window** — opening day through 13 August — so cross-season comparisons isolate what changed rather than confounding it with the calendar. Matched that way the six seasons are closely comparable:

| Season | Pitches | Game dates | Pitchers |
|---|---|---|---|
| 2021 | 510,443 | 131 | 808 |
| 2022 | 499,155 | 126 | 785 |
| 2023 | 525,413 | 133 | 793 |
| 2024 | 527,381 | 137 | 775 |
| 2025 | 530,479 | 138 | 803 |
| 2026 | 538,039 | 139 | 799 |

Pitches were grouped into seven families (four-seam, sinker, cutter, slider/sweeper, curveball, changeup, splitter) and described by eight shape features: velocity, induced vertical break, arm-side horizontal break, spin rate, extension, release height, release side, and arm angle. Horizontal break and release side are sign-flipped for lefties so "arm-side" means the same thing for both hands — verified by confirming sinkers break ~15″ arm-side for both.

The primary unit is the **arsenal row**: one pitcher's version of one pitch family in one season, minimum 100 pitches. There are **9,305**. This grain stops workhorse starters from dominating a league-wide variance estimate, and it excludes position players pitching in blowouts, who never reach 100 pitches of anything.

Ten studies were run. Several found nothing, and those are reported as prominently as the rest.

---

## The league-wide spread: univariate null, multivariate signal

The most direct test asks whether the standard deviation of pitch shapes shrank. Pooling all eight features into one tested number per family, with intervals from a 2,000-replicate bootstrap resampled by pitcher:

| Family | Median change in dispersion, 2021→2026 | 95% interval | p |
|---|---|---|---|
| Sinker | −11.9% | [−23.6, +6.0] | 0.22 |
| Cutter | −4.9% | [−14.3, +4.4] | 0.30 |
| Four-seam | −2.8% | [−10.8, +4.5] | 0.38 |
| Curveball | −2.5% | [−11.5, +5.7] | 0.42 |
| Slider/Sweeper | −1.4% | [−9.4, +8.5] | 0.69 |
| Changeup | +5.5% | [−4.9, +15.4] | 0.34 |

**No family is significant.** Five of six now lean toward narrowing (sinkers by nearly 12%), but every interval contains zero. Of 112 individual feature-by-family contrasts, 4 survive false-discovery correction — up from zero on five seasons, but still a small minority.

The multivariate test is where the signal is. Measuring the *volume* of occupied shape space (log-determinant of the covariance), five of six families contracted, and pooling them gives:

**−0.73 log-units [−1.28, −0.12], p = 0.017 — about −8.7% per shape axis.**

On five seasons this same test read −5.6% at p = 0.098: suggestive but inconclusive. The sixth season pushed it past significance and increased the effect size. Cutters (−14.6%, p = 0.060) and four-seams (−9.5%, p = 0.054) contracted most.

The reconciliation between the two tests is not a contradiction: individual features can hold their spread while the *joint* distribution tightens, which is what happens when pitchers converge on particular combinations rather than on particular values.

![Change in league-wide spread](figures/fig02_dispersion_contrast.png)

---

## Pitchers drift toward the middle, every year

For each pitcher appearing in consecutive seasons, I measured whether his year-over-year movement in shape space pointed toward the league centre. Measurement noise alone manufactures fake convergence — a pitcher with a lucky-high spin reading one year will "regress" the next — so starting position was measured on one half of his pitches and movement on the other, then benchmarked against a within-season null built identically.

| Seasons | Movement toward centre | Share converging | Noise baseline |
|---|---|---|---|
| 2021→2022 | +0.164 | 64.0% | 53.4% |
| 2022→2023 | +0.155 | 66.9% | 53.0% |
| 2023→2024 | +0.120 | 61.3% | 49.9% |
| 2024→2025 | +0.115 | 62.4% | 53.1% |
| **2025→2026** | **+0.182** | **68.9%** | 56.7% |

**Five seasons out of five.** Roughly two-thirds of pitchers drift toward the league-average version of their own pitch against a noise baseline near 52%, and 2026 is the strongest season in the window. The null sitting near zero is what makes the signal believable.

![Convergence](figures/fig06_convergence.png)

### The new arrivals are already typical

If incumbents converge but league-wide spread only partly contracts, something must be refilling the edges. The obvious candidate is turnover — rookies arriving with strange, unpolished deliveries.

That is not what happens. Pitchers in their debut season sit **closer** to the centre of their family than established pitchers (median −5.0%, paired p = 0.0012); only a third of family-seasons show newcomers further out. Arrivals are *more* league-standard, not less.

This is the study's most direct evidence for the original hypothesis. The development pipeline is not merely polishing pitchers once they reach the majors — it is delivering them pre-conformed.

### But arsenals got broader

Cutting against all of the above, pitchers now throw more distinct pitch types, more evenly — monotonically, in every season:

| | 2021 | 2026 |
|---|---|---|
| Usage entropy | 0.972 | 1.137 |
| Families thrown ≥5% | 3.08 | 3.56 |
| Share of top pitch | 48.9% | 41.3% |

"Homogenization" is therefore the wrong word at the arsenal level. Variety *within* a pitcher is increasing even as each individual pitch converges on a template. Both are true at once, and only the second is homogenization.

---

## The ecology: what gained, what got worse

| Family | Usage 2021→2026 | Relative run value 2021→2026 |
|---|---|---|
| Four-seam | 35.2% → 30.7% (**−4.6pp**) | −0.147 → −0.002 (**+0.146**) |
| Curveball | 9.7% → 8.0% (−1.7pp) | −0.050 → −0.401 (−0.351) |
| Changeup | 11.3% → 11.2% (−0.1pp) | −0.170 → +0.011 (**+0.181**) |
| Cutter | 7.3% → 7.9% (+0.6pp) | +0.120 → −0.075 (−0.195) |
| Sinker | 15.5% → 16.7% (+1.2pp) | −0.014 → +0.232 (+0.245) |
| Splitter | 1.6% → 3.3% (+1.7pp) | +0.302 → +0.060 (−0.242) |
| Slider/Sweeper | 19.4% → 22.2% (**+2.8pp**) | +0.334 → −0.014 (**−0.348**) |

The sweeper is the cleanest case in the dataset. Its relative run value fell **monotonically for six straight seasons** — +0.334, +0.265, +0.184, +0.162, +0.035, −0.014 — as its usage climbed 2.8 points. It is now, for the first time, a below-average pitch by run value.

![Pitch ecology](figures/fig08_ecology.png)

---

## The crowding-out effect, tested properly

Seven families is too small a sample to test "popularity degrades a pitch." So the question was asked at a much finer grain: divide each family's shape space into cells (2 mph × 4″ vertical break × 4″ horizontal break), and ask whether **the same cell** performs worse in seasons when more pitchers occupy it. Cell fixed effects and year fixed effects absorb both "some shapes are simply better" and league-wide run-environment drift.

| Outcome | Effect of doubling a shape's usage | p |
|---|---|---|
| **xwOBA on contact** | **+0.0089 worse** | **0.036** |
| Whiff rate | −0.47pp (worse) | 0.233 |
| CSW rate | +0.31pp (better) | 0.276 |
| Run value/100 | +0.08 (better) | 0.490 |

The contact-quality result is the study's cleanest causal-flavoured finding: **when a pitch shape becomes more common, hitters square it up harder** — holding the shape itself constant. Halving a shape's usage is worth about 6 points of xwOBAcon.

One methodological note, stated plainly. The 500-pitch cell threshold was designed for full seasons; applied to a truncated window it retains only 164 cells, which costs power. Rescaling the threshold to the window (370 pitches, the same fraction) restores 230 cells and gives **+0.0094, p = 0.0088**, which does clear FDR correction. The coefficient is essentially unchanged either way — the difference is precision, not signal. The pre-specified 500 remains the headline.

![Neglected niches](figures/fig13_niches.png)

---

## Do unusual pitches work better?

Each arsenal row was scored for how far it sits from its family's league distribution that season (robust Mahalanobis distance, cross-checked against a nearest-neighbour density score). Comparing the most unusual decile against the most typical:

| Outcome | Most typical | Most unusual | Difference |
|---|---|---|---|
| Whiff% | 23.22 | 24.38 | **+1.16pp** |
| CSW% | 27.42 | 28.22 | +0.81pp |
| Run value/100 | 0.099 | 0.169 | +0.070 |
| xwOBAcon | 0.313 | 0.307 | −0.006 |

All four favour the outliers. The obvious objection is selection: maybe good pitchers simply throw weird pitches. To separate these, uniqueness was split into a between-pitcher component (career-average strangeness) and a within-pitcher component (season-to-season deviation), with pitcher-by-family fixed effects absorbed by demeaning.

| Outcome | Within-pitcher | Between-pitcher |
|---|---|---|
| Whiff% | **+1.426** (p<0.0001) | +1.775 (p<0.0001) |
| CSW% | +0.571 (p=0.0025) | +0.912 (p<0.0001) |
| xwOBAcon | −0.0046 (p=0.009) | −0.0064 (p<0.0001) |
| Run value/100 | +0.024 (p=0.49) | +0.084 (p=0.0001) |

The within-pitcher whiff effect is 80% the size of the between-pitcher one and independently significant. When the same pitcher's pitch drifts away from the league norm, it misses more bats — which selection cannot explain, because the pitcher is held fixed by construction. Run value is the honest exception: it does not move within-pitcher, which is what noisy per-pitch run value looks like even after shrinkage.

![Uniqueness gradient](figures/fig10_uniqueness_gradient.png)

### One important negative

A gradient-boosting model predicting whiffs from velocity, movement, location and count was fit twice on 1.2 million swings — with and without the uniqueness score. Adding it changed log-loss by +0.00008 and AUC by −0.0001. **Nothing.**

This clarifies rather than contradicts. Uniqueness is a deterministic function of the shape features, so a flexible model given those features has already extracted whatever it encodes. Being an outlier is not *extra* information on top of your shape; it is a particular summary of your shape that tracks effectiveness. The actionable claim survives. The claim that "unusual" is independently predictive does not.

---

## Why it works: hitters adapt to what they see

The mechanism evidence comes from the batter's side. For every pitch I counted how many pitches of that same shape the hitter had faced in the previous 30 days, then estimated the effect **within batter** — comparing each hitter's own well-prepared and poorly-prepared moments, with count, location and shape controls. 2.90 million pitches, 830 hitters.

| Outcome | Effect of doubling recent exposure | p |
|---|---|---|
| Whiff per swing | **−0.46pp** | <10⁻²⁸ |
| CSW | −0.27pp | <10⁻¹⁵ |

Familiarity blunts a pitch, and the estimate barely moves when the window changes to 15 days (−0.46pp) or 60 days (−0.45pp).

The interaction is the clincher: the exposure penalty is **larger for more unusual pitches** (−0.0049, p = 0.012 for whiffs; −0.0043, p = 0.003 for CSW). A common shape has little novelty to lose. An unusual one has a great deal, and loses it as hitters see it.

That is precisely the proposed mechanism, and it explains crowding-out: as a shape spreads, every hitter's recent exposure to it rises, and its advantage erodes.

![Familiarity](figures/fig14_familiarity.png)

---

## Two kinds of outlier

Uniqueness has two ingredients that should not be conflated: throwing from a strange **place**, and throwing a strange **pitch**.

The overall ranking is owned by the first kind. Tyler Rogers' submarine sinker — released at 1.2 ft with a −61° arm angle, against a league norm of 5.6 ft and +33° — sits 20–25 standard units from the league centre and has been effective every season. But he is a *delivery* outlier: that uniqueness comes bundled with the whole submarine mechanic, which is not transferable advice.

Recomputing on **movement only** — velocity, vertical and horizontal break, spin — restricted to conventional arm slots (10–60°) gives the actionable list: strange pitches thrown from ordinary places.

| Pitcher | Pitch | Season | Arm slot | Dist. from centre | Whiff% | RV/100 |
|---|---|---|---|---|---|---|
| Matt Andriese | Changeup | 2021 | 44.0° | 10.3 | 24.0 | +0.12 |
| Logan Allen | Changeup | 2023 | 42.5° | 9.1 | 30.4 | +0.96 |
| Pedro Avila | Changeup | 2024 | 45.4° | 8.9 | 31.0 | +0.01 |
| Collin Snider | Four-seam | 2025 | 15.9° | 8.0 | 17.1 | +0.26 |
| Devin Williams | Changeup ("Airbender") | 2021 | 23.4° | 7.7 | **42.1** | +0.12 |
| Trevor Richards | Changeup | 2024 | 49.5° | 7.4 | 29.3 | +0.01 |
| Camilo Doval | Cutter | 2023 | 18.2° | 7.3 | 25.6 | +0.70 |
| Logan Webb | Changeup | 2022 | 12.8° | 7.2 | 25.5 | +0.58 |

Two patterns stand out. The league's strangest conventional-slot pitches are overwhelmingly **changeups** — the offspeed shape that most resists spin-based design templates. And the pitches the industry already celebrates as unicorns (the Airbender, Webb's changeup) fall out of the arithmetic on their own, a sanity check that the score measures what it claims to. The within-pitcher regression above is the systematic version of this table; the effect depends on no single example.

---

## Two recolonizations in progress

### Splitters: the boom crested

The splitter was excluded from the dispersion endpoint (too few 100-pitch arsenals in 2021), so it gets its own profile at a relaxed 50-pitch threshold:

| Season | Pitchers | Pitches | Whiff% | CSW% | RV/100 |
|---|---|---|---|---|---|
| 2021 | 72 | 8,053 | 35.5 | 26.0 | +0.32 |
| 2022 | 70 | 8,155 | 34.0 | 25.6 | +0.51 |
| 2023 | 93 | 12,258 | 34.0 | 25.1 | +0.47 |
| 2024 | 116 | 16,410 | 32.5 | 24.4 | +0.04 |
| 2025 | 151 | 18,104 | 32.5 | 24.1 | +0.15 |
| **2026** | **136** | 17,702 | 32.7 | 24.3 | +0.07 |

Practitioners doubled through 2025 while whiff rate, CSW and run value all fell — then in 2026 the practitioner count **declined for the first time**. Adopters cut their changeup usage by 3–6 percentage points in the adoption year (2026: −5.8pp), so the boom was partly substitution inside the offspeed niche. Splitter shape dispersion also *widened* over the window, the signature of a niche colonized by newcomers trying different versions.

### The deathball: a scarce cell being farmed

The "deathball" — practitioner shorthand popularized around 2024 (Ryne Nelson, Roki Sasaki) for a hard gyro slider with near-zero horizontal break and several inches of depth — is invisible to family-level analysis because Statcast files it under SL. Operationalized as slider-family, ≥85 mph, |HB| ≤ 3″, IVB ≤ −2″:

| Season | Deathballs | Pitchers | Whiff edge vs other sliders | RV edge |
|---|---|---|---|---|
| 2023 | 2,281 | 139 | +7.9pp | +0.37 |
| 2024 | 2,275 | 135 | +4.4pp | +0.46 |
| 2025 | 2,574 | 159 | +5.8pp | +0.31 |
| **2026** | **3,637** | **168** | **+7.6pp** | **+0.65** |

The pitch out-whiffs ordinary sliders by four to eight points, and adoption jumped sharply in 2026 (share of slider-family pitches 1.50% → 2.20%). Unlike the sweeper, **its edge has not eroded** — across four seasons it oscillates with no detectable trend. An earlier reading of this series as "peaked in 2023, declining since" over-fitted three noisy points and does not survive the fourth. Leading 2026 practitioners: Cristopher Sánchez (278, 47.9% whiff), Logan Gilbert (244), Grant Holmes (205, 50.5%), Griffin Canning, and Roki Sasaki — the operational definition is picking up the pitchers the practitioner literature names.

![Splitters and the deathball](figures/fig15_splitter_deathball.png)

---

## Sequencing and count

### Within-at-bat contrast does not buy whiffs

If pitches converge on templates, the natural counter-move is contrast *between* consecutive pitches. For 2.31 million pitches with a predecessor in the same at-bat, a standardized shape gap was computed against the previous pitch and put through the same within-batter machinery as the familiarity study.

| Variable | Whiff effect | p | CSW effect | p |
|---|---|---|---|---|
| Shape gap from previous pitch | **−0.34pp per unit** | <0.001 | −0.24pp | <0.001 |
| Exact shape-cell repeat | +0.23pp | 0.085 | **+0.50pp** | <0.001 |

Both signs run against conventional sequencing wisdom: bigger contrast with the previous pitch predicts slightly **fewer** whiffs (holding the current pitch's own quality fixed), and repeating the exact same shape is neutral-to-good rather than punished. The novelty that matters is measured in days and games — the 30-day exposure effect — not in seconds within an at-bat. Hitters expect change, and doubling up exploits that expectation.

### The outlier advantage holds in every count — and is barely exploited

| Count state | Uniqueness whiff effect | p |
|---|---|---|
| Batter ahead | +2.08pp | <0.001 |
| Even | +3.07pp | <0.001 |
| **Pitcher ahead** | **+3.69pp** | <0.001 |
| Two strikes | +2.52pp | <0.001 |

Significant in all four states, largest when the pitcher is ahead. Deployment, though, is nearly flat: outlier-decile pitches are 20.0% of pitches when the batter is ahead and 20.9% with two strikes — under a point of tilt, against an edge that holds everywhere.

![Sequencing and count](figures/fig16_sequencing.png)

---

## Does the newest season continue the trends?

Trends pooled across a window can hide a turning point in the most recent season. Scoring the year-specific series on whether 2026 extends the prior direction: **4 of 8 continue.**

| Claim | Through 2025 | 2026 | |
|---|---|---|---|
| Pitchers drift toward the centre | 63.6% inward | 68.9% inward | holds |
| Arrivals more typical than incumbents | −5.1% | −2.2% | holds |
| Four-seam usage keeps falling | 35.2% → 31.8% | 30.7% (−1.09pp) | holds |
| Splitter effectiveness erodes | whiff 35.5% → 32.5% | 32.7% | holds |
| Sweeper usage keeps rising | 19.4% → 22.8% | 22.2% (−0.62pp) | breaks |
| Splitter usage keeps rising | 1.6% → 3.4% | 3.3% (−0.12pp) | breaks |
| Splitter keeps drawing practitioners | 72 → 151 | 136 | breaks |
| Deathball edge keeps eroding | +7.9pp peak, then +5.8 | +7.6pp | breaks |

Three of the four failures are one event: **the sweeper and splitter booms stopped.** That is the mechanism completing rather than failing. A pitch whose value is being competed away should eventually be abandoned, not adopted forever — and the sweeper's usage turned down in the exact season its relative run value reached zero. What failed was the extrapolation layered on top of the mechanism, not the mechanism.

The fourth failure is genuine: the deathball's edge did not erode, and this data cannot yet say whether it eventually will.

### The changeup came back

The clearest single result of the newest season is the pitch nobody was watching. The changeup was the most-abandoned offspeed pitch in the study — usage falling in each of the four seasons to 2025, reaching a six-season low of 10.15%, with the second-worst relative run value of any family that year (−0.242, behind only the curveball), and actively cannibalized by splitter adopters.

In 2026 it posted its best season on every measure at once:

| | 2025 | 2026 |
|---|---|---|
| Usage | 10.15% | **11.21%** (largest gain of any family) |
| Whiff% | 29.14 | **29.77** (best of six seasons) |
| xwOBAcon | 0.288 | **0.277** (best of six seasons) |
| Run value/100 | −0.228 | **+0.025** (first positive in six seasons) |

A pitch was abandoned to scarcity, became effective again, and pitchers noticed within a season. That is the neglected-niche thesis in its most direct form — and it is why the changeup dominates the conventional-slot outlier list above.

![2026 against the record](figures/fig17_season_check.png)

---

## What this means

1. **The homogenization is real, but local.** Pitchers converge on the template for their pitch and arrive already conforming, and the joint shape space has measurably contracted (−8.7% per axis, p = 0.017). What is not shrinking is the number of templates — arsenals are broader than ever.
2. **Crowding degrades a pitch.** The same shape allows harder contact as more pitchers throw it. Popularity is self-limiting: the sweeper's six-season monotone value decline, and the splitter's fading whiff rate, are the same curve at two scales.
3. **Novelty is a real, decaying asset — measured in days, not pitches.** Its value shows up in 15–60-day exposure windows and decays fastest for the pitches that depend on it most. Within a single at-bat the logic inverts: contrast with the previous pitch buys nothing.
4. **The opportunity is scarcity, not strangeness.** Uniqueness added no predictive signal beyond shape, so the edge is not "be weird" — it is "occupy a shape hitters are not currently seeing." The changeup's 2026 revival is that principle paying out in real time, and the conventional-slot unicorn list is dominated by changeups.
5. **Unusual pitches are underdeployed in every count.** The advantage is significant in all four count states, yet outlier-decile pitches get under a point more two-strike usage than when behind.

---

## Limitations

- **Underpowered on univariate dispersion.** 115–440 pitchers per family-season cannot resolve a 5% change in a standard deviation. The per-family null is not evidence of absence; the multivariate test is where this study has power.
- **2026 is incomplete.** It is included on a matched calendar window, which makes it comparable but still leaves it a two-thirds season subject to in-season roster churn. Its trends should be treated as provisional until the season closes.
- **Date matching costs data.** Truncating all seasons to 13 August discards roughly a quarter of 2021–2025, which is why the scarcity panel retains 164 cells rather than 240. The threshold sensitivity above shows the conclusion is unaffected.
- **Uniqueness is not exogenous.** It is computed from the same shape features used as controls, so the outlier study is associational. The scarcity panel (same shape, varying usage) and the familiarity model (same pitch, varying batter exposure) supply the identification.
- **Confounders spanning the window.** Foreign-substance enforcement (June 2021) cut spin sharply — spin results were re-run excluding pre-enforcement 2021; the pitch clock and shift ban (2023) are absorbed by year fixed effects; bat-tracking exists only from 2023 and is not used in the core models.
- **Taxonomy drift is handled but real.** Savant's classifier is applied retroactively, so sweeper labels reach back to 2021 — an advantage here, since one classifier sees every season. Primary analyses still run at family level.
- **`player_name` in Statcast names the batter, not the pitcher.** Pitcher labels come from the repo's roster file plus a small verified supplement; a handful of pitchers appear as raw MLBAM ids.

---

## Reproducing this

```bash
pip install -e ".[analysis]"
statcast init
statcast backfill --start-date 2021-04-01 --end-date 2021-10-03 --game-types R   # repeat per season
python -m analysis.run_all
```

`analysis/config.py` holds every threshold, seed and confounder date. `SEASON_CUTOFF_MD` (default `08-13`) truncates all seasons to a matched window and should be set to `None` once the final season in `YEARS` is complete. Every script writes a `*_meta.json` sidecar recording the git commit, parameters and data-manifest hash behind its numbers. Bootstraps use 2,000 replicates resampled by pitcher; multiplicity is controlled at FDR q = 0.10 within each study.

Prior work informing the design is annotated in `analysis/report/literature.md`.
