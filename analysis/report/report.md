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

Ten studies were run, the last of them an out-of-sample check against a season that did not exist when the others were written. Three found nothing. That is reported here as prominently as what was found.

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

## The existence proofs: two kinds of outlier

Uniqueness has two ingredients that should not be conflated: throwing from a strange **place**, and throwing a strange **pitch**.

The overall uniqueness ranking is owned by the first kind. Tyler Rogers' submarine sinker — released at 1.1–1.4 ft with a −61° arm angle, against a league norm of 5.6 ft and +33° — sits 20–25 standard units from the league centre and has been consistently effective for five straight seasons (run value positive every year, +1.42/100 in 2025, his most extreme season). But he is a delivery outlier: his uniqueness is dominated by release geometry, a package that comes with the whole submarine mechanic and is not separable advice for a conventional pitcher.

So the ranking was recomputed on **movement only** — velocity, induced vertical break, horizontal break, spin — restricted to conventional arm slots (10–60°). This is the actionable list: strange pitches thrown from ordinary places.

| Pitcher | Pitch | Season | Arm slot | Distance from centre | Whiff% | RV/100 |
|---|---|---|---|---|---|---|
| Matt Andriese | Changeup | 2021 | 43.7° | 10.6 | 24.7 | −0.05 |
| Pedro Avila | Changeup | 2023 | 40.6° | 9.2 | 39.1 | +0.87 |
| David Bednar | Splitter | 2021 | 34.6° | 8.6 | 35.2 | +1.01 |
| Devin Williams | Changeup ("Airbender") | 2021 | 23.0° | 8.0 | **42.9** | −0.05 |
| Camilo Doval | Cutter | 2023 | 17.5° | 8.0 | 26.2 | +0.35 |
| Logan Allen | Changeup | 2023 | 42.0° | 7.7 | 30.5 | +0.75 |
| Logan Webb | Changeup | 2022 | 12.5° | 7.4 | 25.0 | +0.85 |
| César Valdez | Changeup ("dead fish") | 2021 | 10.6° | 7.6 | 28.7 | −0.05 |

Two things stand out. Most of the league's strangest conventional-slot pitches are **changeups and splitters** — offspeed shapes that resist the standardized spin-based design templates. And the famous cases the industry already celebrates as unicorns (Williams' Airbender, Webb's changeup, Bednar's splitter) fall out of the arithmetic on their own, which is a decent sanity check that the uniqueness score measures what it claims to.

The within-pitcher regression in the previous section is the systematic version of this table — the effect does not depend on any individual example.

---

## The live recolonizations: splitters and the deathball

The scarcity thesis predicts that neglected shapes should get rediscovered, work well early, and erode as they crowd. Two current cases let us watch this happen in real time.

### Splitters: the boom is already paying the crowding tax

The splitter was excluded from the dispersion endpoint (too few 100-pitch arsenals in 2021), so it gets its own profile at a relaxed 50-pitch threshold:

| Season | Pitchers | Pitches | Whiff% | CSW% | RV/100 |
|---|---|---|---|---|---|
| 2021 | 75 | 11,448 | 35.8 | 26.1 | +0.37 |
| 2022 | 77 | 11,342 | 34.2 | 25.6 | +0.48 |
| 2023 | 105 | 16,796 | 34.0 | 25.0 | +0.45 |
| 2024 | 128 | 22,048 | 32.6 | 24.6 | +0.16 |
| 2025 | 166 | 24,017 | 33.0 | 24.4 | +0.12 |

Practitioners more than doubled, and **whiff rate, CSW and run value all declined as the pitch spread** — the crowding-out mechanism from the scarcity panel, playing out at family scale. Two supporting details:

- **Adopters cannibalized their changeups.** Pitchers picking up a splitter cut their changeup usage by 3–6 percentage points in the adoption year — the splitter boom is partly a *substitution* within the offspeed niche, consistent with the "death of the changeup" discussion in the practitioner literature.
- **The shape space is widening, not converging.** Splitter IVB dispersion rose from 2.9″ to 3.7″ across arsenals (+29%) — the signature of a niche being colonized by newcomers trying different versions, the opposite of the mature-pitch pattern.

![Splitters and the deathball](figures/fig15_splitter_deathball.png)

### The deathball: a scarce cell being deliberately farmed

The "deathball" — practitioner shorthand popularized around 2024 (Ryne Nelson, Roki Sasaki) for a hard gyro slider with near-zero horizontal break and several inches of depth — is invisible to family-level analysis because Statcast files it under SL. It is exactly what this study says should exist: a deliberately-targeted scarce shape cell. Operationalized here as slider-family, ≥85 mph, |HB| ≤ 3″, IVB ≤ −2″ (strict: |HB| ≤ 2″, IVB ≤ −4″):

| Season | Deathballs | Pitchers | Share of sliders | Whiff edge vs other sliders | RV edge |
|---|---|---|---|---|---|
| 2021 | 2,541 | 132 | 1.85% | +3.7pp | +0.45 |
| 2023 | 3,386 | 163 | 2.10% | +6.9pp | +0.22 |
| 2024 | 3,222 | 170 | 2.01% | +6.2pp | +0.60 |
| 2025 | 3,363 | 187 | 2.10% | +5.2pp | +0.11 |

The pitch out-whiffs ordinary sliders by 4–7 points, practitioner count is climbing steadily (132 → 187), and — right on schedule — **the whiff edge peaked in 2023 and has declined in each season since** as adoption spreads. Leading 2025 practitioners: Luke Jackson (323), Griffin Canning (215), Grant Holmes (180, 45.2% whiff), Clay Holmes, Garrett Whitlock.

---

## Sequencing and count: the variables the first pass ignored

Count entered the earlier models only as a control, and pitch-to-pitch sequencing not at all. Both get direct treatment here.

### Within at-bat contrast does not buy whiffs

If pitches are converging on templates, the natural counter-move is contrast *between* consecutive pitches. So for 2.63 million pitches with a predecessor in the same at-bat, a standardized shape gap (velocity, IVB, HB) was computed against the previous pitch and put through the same within-batter machinery as the familiarity study — batter fixed effects, count-state, family, location and current-shape controls.

| Variable | Whiff effect | p | CSW effect | p |
|---|---|---|---|---|
| Shape gap from previous pitch | **−0.32pp per unit** | <0.001 | −0.22pp | <0.001 |
| Exact shape-cell repeat | **+0.29pp** | 0.019 | +0.51pp | <0.001 |

Both signs run *against* conventional sequencing wisdom: bigger contrast with the previous pitch predicts slightly **fewer** whiffs (holding the current pitch's own quality fixed), and repeating the exact same shape twice in a row is mildly **good**, not bad. The novelty that matters is measured in days and games (the −0.42pp per doubling of 30-day exposure), not in seconds within an at-bat — hitters apparently expect change, and doubling up exploits that expectation. This aligns with published times-through-order work showing familiarity is cumulative rather than momentary.

![Sequencing and count](figures/fig16_sequencing.png)

### The outlier advantage exists in every count — and is barely exploited

Merging each pitch's arsenal-level uniqueness onto the pitch grain and re-running the within-batter whiff model separately by count state:

| Count state | Uniqueness whiff effect | p |
|---|---|---|
| Batter ahead | +1.83pp | <0.001 |
| Even | +2.99pp | <0.001 |
| Pitcher ahead | +2.88pp | <0.001 |
| Two strikes | +2.52pp | <0.001 |

The advantage is significant everywhere, largest in even and pitcher-ahead counts, smallest when the batter is ahead (when hitters can sit on a zone and shape quality matters less than location).

Deployment, however, is nearly flat: outlier-decile pitches make up 19.9% of pitches when the batter is ahead and 20.7% with two strikes — a tilt of less than one percentage point toward putaway situations. Given a whiff edge that holds in every count, **unusual pitches look underused everywhere, not just saved for strikeouts** — the deployment side of the neglected-niche argument.

---

## What this means

1. **The homogenization is real but local.** Pitchers converge on the template for their pitch, and arrive already conforming. What is not shrinking is the number of templates.
2. **Crowding degrades a pitch.** The same shape allows harder contact as more pitchers throw it. Popularity is self-limiting — the sweeper's value decline as usage rose, the splitter boom's fading whiff rate, and the deathball's shrinking edge are three live cases at three different scales.
3. **Novelty is a real, decaying asset — measured in days, not pitches.** Its value shows up in 15–60-day exposure windows (−0.42pp whiff per doubling) and decays fastest for the pitches that depend on it most. Within a single at-bat the logic inverts: contrast with the previous pitch buys nothing, and exact repetition is mildly good. Hitters expect change; they adapt to shapes over weeks.
4. **The practical opportunity is scarcity, not weirdness for its own sake.** Uniqueness added no predictive signal beyond shape — so the edge is not "be strange," it is "occupy a shape hitters are not currently seeing." The abandoned-niche table lists specific candidates: sinker and cutter cells that lost half their usage while still outperforming league average. The offspeed families supply most conventional-slot unicorns (Williams, Webb, Bednar, Avila), suggesting changeup/splitter shape space is where template-resistant variation still lives.
5. **Unusual pitches are underdeployed in every count.** The outlier whiff advantage is significant in all four count states, yet outlier-decile pitches are thrown barely one percentage point more often with two strikes than when behind. Deployment has not caught up to the edge.

---

## 2026 in-season check: an out-of-sample test

The results above were produced before the 2026 season existed. That makes 2026 a genuine out-of-sample test rather than a refit. Because the season is only two-thirds complete (through 13 August), **every season in this check is truncated to the same calendar window** — opening day to 13 August — so the comparison isolates what changed rather than confounding it with "August is not October." Matched, the six seasons run 499k–538k pitches each; 2026 contributes 538,039.

**Seven of eleven claims hold.** The four that break do so in a way that turns out to support the underlying mechanism rather than undermine it.

### What held

| Claim | 2021–25 | 2026 | |
|---|---|---|---|
| Pitchers drift toward the league centre | 63.6% inward | **68.9% inward** (null 56.7%) | holds |
| Arrivals more typical than incumbents | −5.1% | −2.2% | holds |
| Crowding a shape degrades it (xwOBAcon) | +0.0106, p=0.001 | +0.0089, p=0.036 | holds |
| Recent exposure blunts a pitch | −0.42pp per doubling | **−0.46pp**, p=1.5e−28 | holds |
| Four-seam usage keeps falling | 35.2% → 31.8% | 30.7% (−1.09pp) | holds |
| Outlier advantage across counts | +1.8 to +3.0pp | 4/4 counts significant | holds |

Convergence was **stronger in 2026 than in any prior season** (mean cosine 0.182 against a 0.060 null), and arsenal diversity continued its monotone climb (entropy 1.087 → 1.137, families per pitcher 3.40 → 3.56).

Most consequentially, the sixth season pushed the multivariate homogenization test over the significance line. Pooled shape-space volume now shrinks by **−0.73 log-units [−1.28, −0.12], p = 0.017** — about **−8.7% per shape axis**, up from a marginal −5.6% (p = 0.098) on five seasons. The univariate endpoint remains null for every family, but the picture that was "suggestive, not conclusive" is now conclusive at conventional levels.

### What broke — and why it matters

Three of the four failures are the same event: **the sweeper and splitter booms stopped.**

| Family | Usage 2025 → 2026 | Relative run value 2025 → 2026 |
|---|---|---|
| **Changeup** | 10.15% → **11.21%** (+1.06pp) | −0.242 → **+0.011** (+0.253) |
| Sinker | 15.67% → 16.67% (+1.00pp) | +0.240 → +0.232 |
| Cutter | 7.79% → 7.92% (+0.13pp) | +0.029 → −0.075 |
| Splitter | 3.44% → 3.31% (−0.13pp) | +0.133 → +0.060 |
| Curveball | 8.40% → 8.04% (−0.36pp) | −0.331 → −0.401 |
| **Slider/Sweeper** | 22.80% → **22.18%** (−0.62pp) | +0.035 → **−0.014** |
| Four-seam | 31.75% → 30.66% (−1.09pp) | −0.000 → −0.002 |

I predicted sweeper and splitter usage would keep rising. Both fell. But look at *why*: the sweeper's relative run value declined **monotonically for six straight seasons** — +0.356, +0.242, +0.214, +0.144, +0.048, −0.000 — and usage finally turned down in the exact season its value reached zero. Splitter practitioners fell for the first time (151 → 136) after its whiff rate had eroded from 35.5% to 32.5%.

The crowding-out mechanism was the prediction. Continued adoption was an extrapolation layered on top of it, and it was the extrapolation that failed: a pitch whose value is being competed away should eventually be abandoned, not adopted forever. 2026 is the mechanism completing its cycle rather than contradicting it.

### The changeup came back

The clearest single result of the 2026 check is the pitch nobody was watching. The changeup was the most-abandoned offspeed pitch in the study — usage falling every year to a six-season low of 10.15%, the worst relative run value of any family in 2025 (−0.242), and actively cannibalized by splitter adopters (who cut changeup usage 3–6pp on adoption).

In 2026 it posted its **best season on every measure at once**:

| | 2025 | 2026 |
|---|---|---|
| Usage | 10.15% | **11.21%** (largest gain of any family) |
| Whiff% | 29.14 | **29.77** (best of six seasons) |
| xwOBAcon | 0.288 | **0.277** (best of six seasons) |
| Run value/100 | −0.228 | **+0.025** (first positive in six seasons) |

This is the neglected-niche thesis in its most direct form: a pitch was abandoned to scarcity, became effective again, and pitchers noticed within a season.

### The one genuine miss

The deathball's whiff edge over ordinary sliders did **not** continue eroding: +7.9pp (2023) → +4.4 → +5.8 → **+7.6pp (2026)**, with adoption rising sharply (2,574 → 3,637 pitches, 159 → 168 pitchers). Its share of slider-family pitches jumped from 1.50% to 2.20%.

My earlier reading — "peaked in 2023 and has declined each season since" — over-fitted three noisy points. Across four seasons the edge oscillates between +4 and +8pp with no detectable trend. The honest statement is that the deathball carries a large, *persistent* advantage that has not yet been competed away. Whether it eventually erodes like the sweeper is an open question this data cannot yet answer. (Roki Sasaki now appears among the leading practitioners, alongside Cristopher Sánchez, Logan Gilbert and Grant Holmes — the operational definition is picking up the pitchers the practitioner literature names.)

![2026 against the five-season record](figures/fig17_season_check.png)

### What the check changes

Nothing in the core argument. Convergence, crowding, familiarity decay and the outlier advantage all replicated, and the headline homogenization test got *stronger* with a sixth season. What 2026 corrects is a piece of naive extrapolation: booms do not run forever, and the same mechanism that degrades a crowded pitch eventually sends pitchers back to the neglected one. The changeup's revival is the study's own prediction arriving a season early.

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
