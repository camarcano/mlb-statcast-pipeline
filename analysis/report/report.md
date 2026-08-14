# Is modern pitch design making MLB pitchers throw the same?

**A study of 3.55 million regular-season pitches, 2021–2025**

## The short answer

Partly — and the part that is true is the part that matters.

League-wide, the *spread* of pitch shapes has not measurably shrunk. But individual pitchers move toward the league-average version of their pitch every single season, arriving pitchers are already more typical than the veterans they replace, and shapes that gain popularity get measurably worse as they spread. Meanwhile, unusual pitches outperform typical ones, and the mechanism appears to be unfamiliarity: a pitch loses its edge in proportion to how recently the hitter has seen that shape.

So the hypothesis survives, but not in its simplest form. The league is not collapsing into a single pitch. It is converging on **local templates** — a standard four-seamer, a standard sweeper — while the total variety is propped up by churn and by the periodic discovery of a neglected pitch type.

---

## What was measured

Every regular-season pitch from 2021 through 2025, pulled from Baseball Savant into SQLite by this repo's `statcast` CLI: **3,554,404 classified pitches** over 912 game-days, from **2,123 pitchers**.

Pitches were grouped into seven families (four-seam, sinker, cutter, slider/sweeper, curveball, changeup, splitter) and described by eight shape features: velocity, induced vertical break, arm-side horizontal break, spin rate, extension, release height, release side, and arm angle. Horizontal break and release side are sign-flipped for lefties so that "arm-side" means the same thing for both hands — verified by confirming sinkers break ~15″ arm-side for both.

The primary unit of analysis is the **arsenal row**: one pitcher's version of one pitch family in one season, minimum 100 pitches. There are **9,191** of them. This grain matters — it stops workhorse starters from dominating a league-wide variance estimate, and it excludes position players pitching in blowouts, who never reach 100 pitches of anything.

Seven studies were run. Three found nothing. That is reported here as prominently as what was found.

---

## What did not happen: the league-wide spread held up

The most direct test of homogenization is whether the standard deviation of pitch shapes shrank. Pooling all eight features into one tested number per family:

| Family | Median change in dispersion, 2021→2025 | 95% interval | p |
|---|---|---|---|
| Sinker | −7.5% | [−18.0, +8.3] | 0.32 |
| Cutter | −4.5% | [−11.9, +5.2] | 0.39 |
| Slider/Sweeper | −1.2% | [−8.7, +7.4] | 0.66 |
| Curveball | −0.9% | [−8.2, +5.9] | 0.68 |
| Changeup | +1.5% | [−6.9, +10.5] | 0.76 |
| Four-seam | +3.0% | [−4.6, +10.2] | 0.44 |

**Nothing is significant.** Four of six families lean toward narrowing, but every interval comfortably contains zero. Across all 112 individual feature-by-family contrasts, zero survive false-discovery correction.

The multivariate version tells the same story with slightly more force. Measuring the *volume* of occupied shape space (log-determinant of the covariance), five of six families shrank, and pooling them gives **−0.46 log-units [−0.95, +0.07], p = 0.098** — about **−5.6% per shape axis**. Suggestive, not conclusive.

Two honest caveats. Splitters could not be tested at all — too few pitchers threw 100 of them in 2021. And this study has roughly 150–500 pitchers per family-season, which is simply not enough to resolve a 5% change in a standard deviation. **The null here is weak evidence of absence, not evidence of absence.**

![Change in league-wide spread](figures/fig02_dispersion_contrast.png)

---

## What did happen: pitchers move toward the middle, every year

The population-level null hides a strong individual-level signal.

For each pitcher appearing in consecutive seasons, I measured whether his year-over-year movement in shape space pointed toward the league centre. Measurement noise alone creates fake convergence — a pitcher who got a lucky-high spin reading in year one will "regress" in year two — so position was measured on one half of his pitches and movement on the other, and the whole thing was benchmarked against a within-season null built identically.

| Seasons | Movement toward centre | Share converging | Null benchmark |
|---|---|---|---|
| 2021→2022 | +0.143 | 65.7% | 54.0% |
| 2022→2023 | +0.162 | 66.8% | 53.8% |
| 2023→2024 | +0.120 | 61.2% | 53.0% |
| 2024→2025 | +0.121 | 62.0% | 51.7% |

**Four seasons out of four.** Roughly two-thirds of pitchers drift toward the league-average version of their own pitch, against a noise baseline of ~52%. The null sits near zero, which is what makes the signal believable.

![Convergence](figures/fig06_convergence.png)

### And the new arrivals are already typical

If incumbents converge but the league-wide spread holds, something must be refilling the edges. The obvious candidate is turnover — rookies arriving with strange, unpolished deliveries.

That is not what happens. Pitchers in their debut season sit **closer** to the centre of their family than established pitchers (median −3.6%, paired p = 0.019); in 2024 debuts were 13% closer. Arriving pitchers are *more* league-standard, not less.

This is the study's most direct evidence for the user's original intuition. The development pipeline is not just polishing pitchers once they arrive — it is delivering them pre-conformed.

### But arsenals got broader, not narrower

Cutting against all of the above: pitchers now throw **more** distinct pitch types, more evenly.

| | 2021 | 2025 |
|---|---|---|
| Usage entropy | 0.996 | 1.108 |
| Families thrown ≥5% | 3.15 | 3.47 |
| Share of top pitch | 49.0% | 43.3% |

Monotonic in every season. So "homogenization" is the wrong word for what is happening at the arsenal level — variety *within* a pitcher is increasing even as each individual pitch converges on a template. Both can be true at once, and only the second is homogenization.

---

## The ecology: what gained, what got worse

Pitch usage shifted substantially over five seasons, and the value of each pitch moved against it.

| Family | Usage 2021→2025 | Change in relative run value |
|---|---|---|
| Four-seam | 35.6% → 32.0% (**−3.6pp**) | **+0.089** (improved) |
| Slider/Sweeper | 19.4% → 22.6% (**+3.2pp**) | −0.218 (worse) |
| Splitter | 1.6% → 3.4% (**+1.8pp**) | −0.252 (worse) |
| Cutter | 7.3% → 7.6% (+0.3pp) | −0.217 (worse) |
| Sinker | 15.3% → 15.6% (+0.3pp) | +0.230 (improved) |
| Changeup | 11.3% → 10.3% (−0.9pp) | +0.072 (improved) |
| Curveball | 9.6% → 8.5% (−1.1pp) | −0.247 (worse) |

The pattern is visible but not clean: the two pitches that gained most usage (sweepers, splitters) both lost the most value, while the pitch that was abandoned most (four-seam) got better. Across seven families the rank correlation is −0.32, which with n = 7 proves nothing on its own.

![Pitch ecology](figures/fig08_ecology.png)

---

## The crowding-out effect, tested properly

Seven families is too small a sample to test "popularity degrades a pitch." So the same question was asked at a much finer grain: divide each family's shape space into cells (2 mph × 4″ vertical break × 4″ horizontal break), and ask whether **the same cell** performs worse in seasons when more pitchers occupy it. Cell fixed effects and year fixed effects absorb both "some shapes are just better" and league-wide run-environment drift. 240 cells, 1,200 cell-seasons.

| Outcome | Effect of doubling a shape's usage | p | Survives FDR |
|---|---|---|---|
| **xwOBAcon allowed** | **+0.0073 worse** | **0.0011** | **yes** |
| Whiff% | −0.40pp (worse) | 0.114 | no |
| Run value/100 | −0.02 (worse) | 0.765 | no |
| CSW% | +0.22pp (better) | 0.231 | no |

The contact-quality result is the study's cleanest finding: **when a pitch shape becomes more common, hitters square it up harder** — holding the shape itself constant. Halving a shape's usage is worth about 7 points of xwOBAcon. The other three outcomes lean the same way but do not clear significance.

![Neglected niches](figures/fig13_niches.png)

---

## Do unusual pitches actually work better?

Each arsenal row was scored for how far it sits from its family's league distribution that season (robust Mahalanobis distance, cross-checked against a nearest-neighbour density score). Comparing the most unusual decile against the most typical:

| Outcome | Most typical decile | Most unusual decile | Difference |
|---|---|---|---|
| Whiff% | 23.55 | 24.70 | **+1.15pp** |
| CSW% | 27.41 | 28.19 | +0.77pp |
| Run value/100 | 0.077 | 0.132 | +0.055 |
| xwOBAcon | 0.313 | 0.307 | −0.005 |

All four favour the outliers. But the obvious objection is selection: maybe good pitchers simply throw weird pitches. To separate these, uniqueness was split into a between-pitcher part (a pitcher's career-average strangeness) and a within-pitcher part (his own season-to-season deviation), with pitcher-by-family fixed effects absorbed.

| Outcome | Within-pitcher | Between-pitcher |
|---|---|---|
| Whiff% | **+1.762** (p<0.0001) | +1.766 (p<0.0001) |
| CSW% | +0.831 (p=0.0001) | +0.972 (p<0.0001) |
| xwOBAcon | −0.0055 (p=0.005) | −0.0064 (p<0.0001) |
| Run value/100 | +0.054 (p=0.098) | +0.074 (p=0.0001) |

The within- and between-pitcher whiff coefficients are **essentially identical** (1.762 vs 1.766). When the same pitcher's pitch drifts away from the league norm, it misses more bats by the same margin that separates unusual pitchers from typical ones. This is not selection.

![Uniqueness gradient](figures/fig10_uniqueness_gradient.png)

### One important negative

A gradient-boosting model predicting whiffs from velocity, movement, location and count was fit twice — with and without the uniqueness score — on 1.2 million swings. Adding uniqueness changed log-loss by +0.0001 and AUC by −0.0002. **Nothing.**

This does not contradict the results above; it clarifies them. Uniqueness is a deterministic function of the shape features, so a flexible model given those features has already extracted whatever uniqueness encodes. Being an outlier is not *extra* information on top of your shape — it is a particular summary of your shape that happens to track effectiveness. The actionable claim survives (moving away from the norm improves outcomes); the claim that "unusual" is independently predictive does not.

---

## Why it works: hitters adapt to what they see

The strongest evidence for the mechanism comes from the batter's side. For every pitch, I counted how many pitches of that same shape the hitter had faced in the previous 30 days, then estimated the effect of that exposure **within batter** — comparing each hitter's own well-prepared and poorly-prepared moments, with count, location and shape controls. 3.36 million pitches, 825 hitters.

| Outcome | Effect of doubling recent exposure | p |
|---|---|---|
| Whiff per swing | **−0.42pp** | <0.00001 |
| CSW | −0.25pp | <0.00001 |

Familiarity blunts a pitch, and the result barely moves when the window is changed to 15 days (−0.41pp) or 60 days (−0.43pp).

The interaction is the clincher: the exposure penalty is **larger for more unusual pitches** (interaction −0.0057, p = 0.0013 for whiffs; −0.0047, p = 0.0002 for CSW). A common shape has little novelty advantage to lose. An unusual one does, and loses it as hitters see it.

That is precisely the mechanism the hypothesis proposes — and it explains the crowding-out result: as a shape spreads, every hitter's recent exposure to it rises, and its advantage erodes.

![Familiarity](figures/fig14_familiarity.png)

---

## The existence proof: Tyler Rogers

The ten most unusual pitches in baseball over these five seasons all belong to one man. Rogers' submarine sinker sits 20–25 standard units from the league centre; a typical pitch sits 2–3.

| Season | Pitches | Distance from league centre | Whiff% | Run value/100 |
|---|---|---|---|---|
| 2021 | 604 | 20.5 | 11.2 | +0.63 |
| 2022 | 596 | 21.3 | 13.0 | +0.13 |
| 2023 | 564 | 22.4 | 10.8 | +0.36 |
| 2024 | 640 | 24.9 | 13.1 | +0.45 |
| 2025 | 729 | 24.6 | 11.5 | **+1.42** |

He gets fewer whiffs than almost any reliever alive and is consistently effective anyway — and after five years of public data, essentially nobody has copied him. If unusual pitches were merely a statistical artifact, Rogers would have regressed. Instead his most extreme season was his best.

---

## What this means

1. **The homogenization is real but local.** Pitchers converge on the template for their pitch, and arrive already conforming. What is not shrinking is the number of templates.
2. **Crowding degrades a pitch.** The same shape allows harder contact as more pitchers throw it. Popularity is self-limiting, and the sweeper's value decline as usage rose is the visible case.
3. **Novelty is a real, decaying asset.** Its value is measurable (−0.42pp whiff per doubling of exposure) and it decays fastest for the pitches that depend on it most.
4. **The practical opportunity is scarcity, not weirdness for its own sake.** Uniqueness added no predictive signal beyond shape — so the edge is not "be strange," it is "occupy a shape hitters are not currently seeing." The abandoned-niche table lists specific candidates: sinker and cutter cells that lost half their usage while still outperforming league average.

---

## Limitations

- **Underpowered on dispersion.** 150–500 pitchers per family-season cannot resolve a 5% change in spread. The S1 null should not be read as "no homogenization."
- **Five seasons is short** for a trend that practitioners date to the mid-2010s. The 2021 baseline is already deep into the pitch-design era.
- **Uniqueness is not exogenous.** It is computed from the same shape features used as controls, so S5 is associational. S6 (same shape, varying scarcity) and S7 (same pitch, varying batter exposure) supply the identification.
- **Confounders spanning the window:** foreign-substance enforcement (June 2021) cut spin sharply — spin results were re-run excluding pre-enforcement 2021; the pitch clock and shift ban (2023) are absorbed by year fixed effects; bat-tracking data exists only from 2023 and was not used in the core models.
- **Taxonomy drift is handled but real.** Savant's classifier is applied retroactively, so sweeper labels exist back to 2021 — an advantage here, since the same classifier sees every season. Primary analyses still run at the family level for safety.
- **`player_name` in Statcast names the batter, not the pitcher.** Pitcher labels come from the repo's roster file; a handful of pitchers appear as raw MLBAM ids.

---

## Reproducing this

```bash
pip install -e ".[analysis]"
statcast init
statcast backfill --start-date 2021-04-01 --end-date 2021-10-03 --game-types R   # repeat per season
python -m analysis.run_all
```

Every script writes a `*_meta.json` sidecar recording the git commit, parameters and data-manifest hash behind its numbers. Bootstraps use 2,000 replicates, resampled by pitcher; multiplicity is controlled at FDR q = 0.10 within each study. Results land in `analysis/results/`, figures in `analysis/figures/`.

Prior work informing the design is annotated in `analysis/report/literature.md`.
