"""Build the shareable HTML report published as an Artifact.

Separate from 30_report.py, which produces the plain reading copy. This one
carries the page design and inlines every figure as a data URI so the published
page is self-contained.
"""
from __future__ import annotations

import base64
import sys

import markdown as md

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config

TITLE = "Pitch Homogeneity Study"

CSS = """
:root{
  --ground:#F0EFEA; --surface:#FCFCFB; --plate:#FCFCFB;
  --ink:#0B0B0B; --ink-2:#52514E; --ink-3:#898781;
  --rule:#E1E0D9; --rule-strong:#C3C2B7;
  --accent:#2A78D6; --warm:#D03B3B; --good:#1B7F53;
  --chip-bg:#E8EEF8; --chip-null-bg:#EDECE6;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#12120F; --surface:#1A1A17; --plate:#F4F3EE;
    --ink:#EDEDE8; --ink-2:#B0AEA6; --ink-3:#85837C;
    --rule:#2C2C27; --rule-strong:#3D3D36;
    --accent:#6BA5EA; --warm:#E57373; --good:#4FB286;
    --chip-bg:#1D2735; --chip-null-bg:#22221D;
  }
}
:root[data-theme="dark"]{
  --ground:#12120F; --surface:#1A1A17; --plate:#F4F3EE;
  --ink:#EDEDE8; --ink-2:#B0AEA6; --ink-3:#85837C;
  --rule:#2C2C27; --rule-strong:#3D3D36;
  --accent:#6BA5EA; --warm:#E57373; --good:#4FB286;
  --chip-bg:#1D2735; --chip-null-bg:#22221D;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--sans); font-size:17px; line-height:1.65;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:820px; margin:0 auto; padding:0 24px 96px}

/* masthead ------------------------------------------------------------- */
.masthead{padding:72px 0 0}
.eyebrow{
  font-family:var(--mono); font-size:11px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 20px;
}
h1{
  font-size:clamp(34px,5.2vw,52px); line-height:1.08; letter-spacing:-.025em;
  font-weight:800; margin:0 0 20px; text-wrap:balance;
}
.standfirst{font-size:20px; line-height:1.55; color:var(--ink-2); margin:0 0 36px; max-width:60ch}
.runstrip{
  display:flex; flex-wrap:wrap; gap:0; border:1px solid var(--rule);
  background:var(--surface); border-radius:2px; overflow:hidden; margin-bottom:8px;
}
.runstrip div{
  flex:1 1 140px; padding:14px 18px; border-right:1px solid var(--rule);
}
.runstrip div:last-child{border-right:0}
.runstrip dt{
  font-family:var(--mono); font-size:10px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 6px;
}
.runstrip dd{
  margin:0; font-family:var(--mono); font-size:19px; font-weight:600;
  font-variant-numeric:tabular-nums; letter-spacing:-.01em;
}

/* sections ------------------------------------------------------------- */
section{padding-top:52px}
.sechead{border-top:2px solid var(--ink); padding-top:16px; margin-bottom:8px}
h2{font-size:29px; line-height:1.2; letter-spacing:-.02em; font-weight:750; margin:10px 0 0; text-wrap:balance}
h3{font-size:19px; letter-spacing:-.01em; font-weight:700; margin:34px 0 0}
.chip{
  display:inline-block; font-family:var(--mono); font-size:10.5px;
  letter-spacing:.13em; text-transform:uppercase; padding:4px 9px;
  border-radius:2px; font-weight:600;
}
.chip.yes{background:var(--chip-bg); color:var(--accent)}
.chip.no{background:var(--chip-null-bg); color:var(--ink-3)}
.chip.partial{background:var(--chip-null-bg); color:var(--warm)}
p{margin:18px 0; max-width:68ch}
strong{font-weight:680}
em{font-style:italic; color:var(--ink-2)}
a{color:var(--accent)}

/* readout -------------------------------------------------------------- */
.readout{
  border-left:3px solid var(--accent); background:var(--surface);
  padding:18px 22px; margin:26px 0; border-radius:0 2px 2px 0;
}
.readout .n{
  font-family:var(--mono); font-size:31px; font-weight:650;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; display:block;
}
.readout .lbl{
  font-family:var(--mono); font-size:11px; letter-spacing:.13em;
  text-transform:uppercase; color:var(--ink-3); display:block; margin-top:6px;
}
.readout.warm{border-left-color:var(--warm)}

/* tables --------------------------------------------------------------- */
.tablewrap{overflow-x:auto; margin:26px 0; border:1px solid var(--rule); border-radius:2px; background:var(--surface)}
table{border-collapse:collapse; width:100%; font-size:14.5px}
th,td{padding:9px 14px; text-align:left; border-bottom:1px solid var(--rule); white-space:nowrap}
th{
  font-family:var(--mono); font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--ink-3); font-weight:600;
  border-bottom:1px solid var(--rule-strong);
}
td:not(:first-child){font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:13.5px}
tbody tr:last-child td{border-bottom:0}

/* figures -------------------------------------------------------------- */
figure{margin:32px 0}
figure img{
  display:block; width:100%; height:auto; background:var(--plate);
  border:1px solid var(--rule); border-radius:2px; padding:6px;
}
figcaption{
  font-family:var(--mono); font-size:11px; letter-spacing:.06em;
  color:var(--ink-3); margin-top:10px; line-height:1.5;
}
ul,ol{max-width:66ch; padding-left:22px}
li{margin:9px 0}
hr{border:0; border-top:1px solid var(--rule); margin:44px 0}
code{font-family:var(--mono); font-size:.88em; background:var(--surface); padding:2px 5px; border-radius:2px}
pre{
  background:var(--surface); border:1px solid var(--rule); border-radius:2px;
  padding:16px; overflow-x:auto; font-size:13px; line-height:1.6;
}
pre code{background:none; padding:0}
footer{
  margin-top:64px; padding-top:22px; border-top:1px solid var(--rule);
  font-family:var(--mono); font-size:11.5px; color:var(--ink-3); line-height:1.7;
}
@media (max-width:560px){
  body{font-size:16px}
  .masthead{padding-top:48px}
  .runstrip div{flex-basis:50%}
}
"""


def fig(name: str, caption: str) -> str:
    path = config.FIGURES_DIR / f"{name}.png"
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode()
    return (f'<figure><img src="data:image/png;base64,{b64}" alt="{caption}">'
            f"<figcaption>{caption}</figcaption></figure>")


def readout(number: str, label: str, warm: bool = False) -> str:
    cls = "readout warm" if warm else "readout"
    return (f'<div class="{cls}"><span class="n">{number}</span>'
            f'<span class="lbl">{label}</span></div>')


def body(text: str) -> str:
    html = md.markdown(text, extensions=["tables"])
    # wide tables scroll inside their own container so the page body never does
    return html.replace("<table>", '<div class="tablewrap"><table>').replace(
        "</table>", "</table></div>")


def section(num: str, title: str, verdict: str, verdict_cls: str,
            content: str) -> str:
    chip = (f'<span class="chip {verdict_cls}">{verdict}</span>'
            if verdict else "")
    return (f'<section><div class="sechead">{chip}'
            f"<h2>{title}</h2></div>{content}</section>")


SECTIONS = [
    section("1", "The spread: univariate null, multivariate signal",
            "Supported", "yes", body("""
The most direct test asks whether the standard deviation of pitch shapes shrank.
Pooling all eight shape features into one tested number per family, with
intervals from a 2,000-replicate bootstrap resampled by pitcher:

| Family | Change in dispersion, 2021→2026 | 95% interval | p |
|---|---|---|---|
| Sinker | −11.9% | −23.6 to +6.0 | 0.22 |
| Cutter | −4.9% | −14.3 to +4.4 | 0.30 |
| Four-seam | −2.8% | −10.8 to +4.5 | 0.38 |
| Curveball | −2.5% | −11.5 to +5.7 | 0.42 |
| Slider / Sweeper | −1.4% | −9.4 to +8.5 | 0.69 |
| Changeup | +5.5% | −4.9 to +15.4 | 0.34 |

No family is individually significant. Five of six now lean toward narrowing,
but every interval contains zero.

The multivariate test is where the signal lives. Measuring the *volume* of
occupied shape space, five of six families contracted, and pooling them gives a
result that on five seasons was only suggestive (−5.6%, p = 0.098):
""") + readout("−8.7% per axis", "pooled shape-space volume, 2021→2026 · p = 0.017")
        + body("""
The sixth season pushed this past significance and increased the effect.
Cutters (−14.6%, p = 0.060) and four-seams (−9.5%, p = 0.054) contracted most.
The two tests do not contradict: individual features can hold their spread while
the *joint* distribution tightens, which is what happens when pitchers converge
on particular combinations rather than particular values.
""") + fig("fig02_dispersion_contrast",
           "Change in league-wide spread by family and shape feature. Bars left "
           "of zero indicate convergence; whiskers are 95% pitcher-bootstrap "
           "intervals. Each panel sets its own horizontal scale.")),

    section("2", "Pitchers drift toward the middle, every year",
            "Supported", "yes", body("""
For every pitcher appearing in consecutive seasons, I measured whether his
year-over-year movement in shape space pointed toward the league centre.
Measurement noise alone manufactures fake convergence, so starting position was
measured on one half of his pitches and movement on the other, then benchmarked
against a within-season null built the same way.

| Seasons | Movement toward centre | Share converging | Noise baseline |
|---|---|---|---|
| 2021 → 2022 | +0.164 | 64.0% | 53.4% |
| 2022 → 2023 | +0.155 | 66.9% | 53.0% |
| 2023 → 2024 | +0.120 | 61.3% | 49.9% |
| 2024 → 2025 | +0.115 | 62.4% | 53.1% |
| 2025 → 2026 | +0.182 | 68.9% | 56.7% |

Five seasons out of five, and the newest is the strongest in the window. The
null sitting near zero is what makes the signal believable.

### Arrivals are already typical

If incumbents converge, something must refill the edges — the obvious candidate
being rookies with strange, unpolished deliveries. That is not what happens.
Debut-season pitchers sit **closer** to the centre of their family than
established ones (median −5.0%, paired p = 0.0012). The development pipeline is
not merely polishing pitchers once they arrive; it is delivering them
pre-conformed.

### Yet arsenals got broader

| | 2021 | 2026 |
|---|---|---|
| Usage entropy | 0.972 | 1.137 |
| Families thrown ≥5% | 3.08 | 3.56 |
| Share of top pitch | 48.9% | 41.3% |

Monotone in every season. So "homogenisation" is the wrong word at the arsenal
level: variety *within* a pitcher is rising even as each individual pitch
converges on a template. Only the second is homogenisation.
""") + fig("fig06_convergence",
           "Crowding of the shape space and year-over-year movement toward the "
           "league centre, against the split-half noise benchmark.")),

    section("3", "Popular shapes get punished", "Supported", "yes", body("""
| Family | Usage 2021 → 2026 | Relative run value |
|---|---|---|
| Four-seam | 35.2% → 30.7% (−4.6pp) | −0.147 → −0.002 (better) |
| Curveball | 9.7% → 8.0% (−1.7pp) | −0.050 → −0.401 (worse) |
| Changeup | 11.3% → 11.2% (−0.1pp) | −0.170 → +0.011 (better) |
| Cutter | 7.3% → 7.9% (+0.6pp) | +0.120 → −0.075 (worse) |
| Sinker | 15.5% → 16.7% (+1.2pp) | −0.014 → +0.232 (better) |
| Splitter | 1.6% → 3.3% (+1.7pp) | +0.302 → +0.060 (worse) |
| Slider / Sweeper | 19.4% → 22.2% (+2.8pp) | +0.334 → −0.014 (worse) |

The sweeper is the cleanest case in the dataset: its relative run value fell
**monotonically for six straight seasons** — +0.334, +0.265, +0.184, +0.162,
+0.035, −0.014 — as usage climbed 2.8 points. It is now, for the first time, a
below-average pitch by run value.

Seven families is too small a sample to test this properly, so the same question
was asked at a far finer grain: divide each family's shape space into cells
(2 mph × 4″ vertical break × 4″ horizontal break) and ask whether **the same
cell** performs worse in seasons when more pitchers occupy it. Cell and year
fixed effects absorb both "some shapes are simply better" and run-environment
drift.

| Outcome | Effect of doubling a shape's usage | p |
|---|---|---|
| xwOBA on contact | +0.0089 worse | 0.036 |
| Whiff rate | −0.47pp (worse) | 0.233 |
| CSW rate | +0.31pp (better) | 0.276 |
| Run value / 100 | +0.08 (better) | 0.490 |
""") + readout("+0.0089", "xwOBAcon penalty per doubling of a shape's usage · p = 0.036", warm=True)
        + body("""
When a pitch shape becomes more common, hitters square it up harder — holding
the shape itself constant. One methodological note stated plainly: the 500-pitch
cell threshold was designed for full seasons, and on a truncated window it
retains only 164 cells. Rescaling it to the window (370 pitches, 230 cells)
gives +0.0094 at p = 0.0088, which clears FDR correction. The coefficient is
unchanged; the difference is precision, not signal. The pre-specified 500
remains the headline.
""") + fig("fig13_niches",
           "Shape cells that lost usage while still outperforming league "
           "average, and the within-cell relationship between scarcity and value.")),

    section("4", "Unusual pitches really do work better", "Supported", "yes", body("""
Each arsenal was scored for how far it sits from its family's league
distribution that season (robust Mahalanobis distance, cross-checked against a
nearest-neighbour density score).

| Outcome | Most typical decile | Most unusual decile | Difference |
|---|---|---|---|
| Whiff rate | 23.22% | 24.38% | +1.16pp |
| CSW rate | 27.42% | 28.22% | +0.81pp |
| Run value / 100 | 0.099 | 0.169 | +0.070 |
| xwOBA on contact | 0.313 | 0.307 | −0.006 |

The obvious objection is selection: perhaps good pitchers simply throw unusual
pitches. Splitting uniqueness into a between-pitcher component (career-average
strangeness) and a within-pitcher one (season-to-season deviation), with
pitcher-by-family fixed effects absorbed by demeaning:

| Outcome | Within-pitcher | Between-pitcher |
|---|---|---|
| Whiff rate | +1.426 (p<0.0001) | +1.775 (p<0.0001) |
| CSW rate | +0.571 (p=0.0025) | +0.912 (p<0.0001) |
| xwOBA on contact | −0.0046 (p=0.009) | −0.0064 (p<0.0001) |
| Run value / 100 | +0.024 (p=0.49) | +0.084 (p=0.0001) |

The within-pitcher whiff effect is 80% the size of the between-pitcher one and
independently significant. When the same pitcher's pitch drifts from the league
norm it misses more bats — which selection cannot explain, because the pitcher
is held fixed by construction. Run value is the honest exception: it does not
move within-pitcher, which is what noisy per-pitch run value looks like even
after shrinkage.

### One important negative

A gradient-boosting model predicting whiffs from velocity, movement, location
and count was fit twice on 1.2 million swings, with and without the uniqueness
score. Adding it changed log-loss by +0.00008 and AUC by −0.0001. Nothing.

That clarifies rather than contradicts. Uniqueness is a deterministic function
of the shape features, so a flexible model given those features has already
extracted whatever it encodes. Being an outlier is not *extra* information on
top of your shape; it is a particular summary of it that tracks effectiveness.
""") + fig("fig10_uniqueness_gradient",
           "Outcomes across uniqueness deciles with pitcher-bootstrap intervals, "
           "and the fitted spline relationship.")),

    section("5", "Why it works: hitters adapt to what they see",
            "Supported", "yes", body("""
For every pitch I counted how many pitches of that same shape the hitter had
faced in the previous 30 days, then estimated the effect **within batter** —
comparing each hitter's own well-prepared and poorly-prepared moments, with
count, location and shape controls. 2.90 million pitches, 830 hitters.

| Outcome | Effect of doubling recent exposure | p |
|---|---|---|
| Whiff per swing | −0.46pp | <10⁻²⁸ |
| CSW | −0.27pp | <10⁻¹⁵ |
""") + readout("−0.46pp", "whiff rate per doubling of a hitter's recent exposure", warm=True)
        + body("""
The estimate barely moves when the window changes to 15 days (−0.46pp) or 60
days (−0.45pp). And the interaction is the clincher: the exposure penalty is
**larger for more unusual pitches** (−0.0049, p = 0.012 for whiffs; −0.0043,
p = 0.003 for CSW). A common shape has little novelty to lose; an unusual one
has a great deal, and loses it as hitters see it.

That is the proposed mechanism, and it explains crowding-out: as a shape
spreads, every hitter's recent exposure to it rises and its advantage erodes.
""") + fig("fig14_familiarity",
           "Whiff rate against recent exposure to the same shape, split by how "
           "unusual the pitch is, with the controlled within-batter estimate.")),

    section("6", "Two kinds of outlier", "", "", body("""
Uniqueness has two ingredients that should not be conflated: throwing from a
strange **place**, and throwing a strange **pitch**.

The overall ranking is owned by the first kind. Tyler Rogers' submarine sinker —
released at 1.2 ft with a −61° arm angle, against a league norm of 5.6 ft and
+33° — sits 20–25 standard units from the centre and has been effective every
season. But he is a *delivery* outlier: that uniqueness comes bundled with the
whole submarine mechanic, which is not transferable advice.

Recomputing on **movement only** — velocity, vertical and horizontal break,
spin — restricted to conventional arm slots (10°–60°) gives the actionable list.

| Pitcher | Pitch | Season | Arm slot | Dist. from centre | Whiff% | RV/100 |
|---|---|---|---|---|---|---|
| Matt Andriese | Changeup | 2021 | 44.0° | 10.3 | 24.0 | +0.12 |
| Logan Allen | Changeup | 2023 | 42.5° | 9.1 | 30.4 | +0.96 |
| Pedro Avila | Changeup | 2024 | 45.4° | 8.9 | 31.0 | +0.01 |
| Collin Snider | Four-seam | 2025 | 15.9° | 8.0 | 17.1 | +0.26 |
| Devin Williams | Changeup ("Airbender") | 2021 | 23.4° | 7.7 | 42.1 | +0.12 |
| Trevor Richards | Changeup | 2024 | 49.5° | 7.4 | 29.3 | +0.01 |
| Camilo Doval | Cutter | 2023 | 18.2° | 7.3 | 25.6 | +0.70 |
| Logan Webb | Changeup | 2022 | 12.8° | 7.2 | 25.5 | +0.58 |

The league's strangest conventional-slot pitches are overwhelmingly
**changeups** — the offspeed shape that most resists spin-based design
templates. And the pitches the industry already celebrates as unicorns (the
Airbender, Webb's changeup) fall out of the arithmetic on their own, a sanity
check that the score measures what it claims to.
""")),

    section("7", "Two recolonizations in progress", "Supported", "yes", body("""
### Splitters: the boom crested

| Season | Pitchers | Whiff% | CSW% | RV/100 |
|---|---|---|---|---|
| 2021 | 72 | 35.5 | 26.0 | +0.32 |
| 2022 | 70 | 34.0 | 25.6 | +0.51 |
| 2023 | 93 | 34.0 | 25.1 | +0.47 |
| 2024 | 116 | 32.5 | 24.4 | +0.04 |
| 2025 | 151 | 32.5 | 24.1 | +0.15 |
| 2026 | 136 | 32.7 | 24.3 | +0.07 |

Practitioners doubled through 2025 while whiff rate, CSW and run value all fell
— then in 2026 the practitioner count **declined for the first time**. Adopters
cut their changeup usage by 3–6 points in the adoption year, so the boom was
partly substitution inside the offspeed niche.

### The deathball: a scarce cell being farmed

The "deathball" — practitioner shorthand popularised around 2024 (Ryne Nelson,
Roki Sasaki) for a hard gyro slider with near-zero horizontal break and several
inches of depth — is invisible to family-level analysis because Statcast files
it under SL. Operationalised as slider-family, ≥85 mph, |HB| ≤ 3″, IVB ≤ −2″:

| Season | Deathballs | Pitchers | Whiff edge vs other sliders | RV edge |
|---|---|---|---|---|
| 2023 | 2,281 | 139 | +7.9pp | +0.37 |
| 2024 | 2,275 | 135 | +4.4pp | +0.46 |
| 2025 | 2,574 | 159 | +5.8pp | +0.31 |
| 2026 | 3,637 | 168 | +7.6pp | +0.65 |

The pitch out-whiffs ordinary sliders by four to eight points and adoption
jumped sharply in 2026. Unlike the sweeper, **its edge has not eroded** — across
four seasons it oscillates with no detectable trend, and an earlier reading of
this series as "peaked in 2023, declining since" over-fitted three noisy points.
Leading 2026 practitioners: Cristopher Sánchez (278, 47.9% whiff), Logan Gilbert
(244), Grant Holmes (205, 50.5%), Griffin Canning, and Roki Sasaki — the
definition is picking up the pitchers the practitioner literature names.
""") + fig("fig15_splitter_deathball",
           "Splitter adoption and whiff decline, and the deathball's share of "
           "slider-family pitches.")),

    section("8", "Sequencing and count", "Partial", "partial", body("""
### Within-at-bat contrast does not buy whiffs

For 2.31 million pitches with a predecessor in the same at-bat, a standardised
shape gap was computed against the previous pitch and put through the same
within-batter machinery as the familiarity study.

| Variable | Whiff effect | p | CSW effect | p |
|---|---|---|---|---|
| Shape gap from previous pitch | −0.34pp per unit | <0.001 | −0.24pp | <0.001 |
| Exact shape-cell repeat | +0.23pp | 0.085 | +0.50pp | <0.001 |

Both signs run against conventional sequencing wisdom: bigger contrast with the
previous pitch predicts slightly *fewer* whiffs, and repeating the same shape is
neutral-to-good rather than punished. The novelty that matters is measured in
days and games, not seconds within an at-bat. Hitters expect change.

### The outlier advantage holds in every count — and is barely exploited

| Count state | Uniqueness whiff effect | p |
|---|---|---|
| Batter ahead | +2.08pp | <0.001 |
| Even | +3.07pp | <0.001 |
| Pitcher ahead | +3.69pp | <0.001 |
| Two strikes | +2.52pp | <0.001 |

Significant everywhere, largest when the pitcher is ahead. Deployment is nearly
flat: outlier-decile pitches are 20.0% of pitches when the batter is ahead and
20.9% with two strikes — under a point of tilt, against an edge that holds in
every count.
""") + fig("fig16_sequencing",
           "Raw whiff rate by contrast with the previous pitch, and the "
           "within-batter uniqueness effect by count state.")),

    section("9", "Does the newest season continue the trends?",
            "4 of 8 continue", "partial", body("""
Trends pooled across a window can hide a turning point in the most recent
season. Scoring the year-specific series on whether 2026 extends the prior
direction:

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

Three of the four failures are one event: **the sweeper and splitter booms
stopped.** That is the mechanism completing rather than failing. A pitch whose
value is being competed away should eventually be abandoned, not adopted
forever — and the sweeper's usage turned down in the exact season its relative
run value reached zero. What failed is the extrapolation layered on top of the
mechanism, not the mechanism. The fourth failure is genuine: the deathball's
edge did not erode, and this data cannot yet say whether it eventually will.

### The changeup came back

The clearest single result of the newest season is the pitch nobody was
watching. The changeup was the most-abandoned offspeed pitch in the study —
usage falling in each of the four seasons to 2025, reaching a six-season low,
with the second-worst relative run value of any family that year, and actively
cannibalised by splitter adopters.

| | 2025 | 2026 |
|---|---|---|
| Usage | 10.15% | 11.21% (largest gain of any family) |
| Whiff% | 29.14 | 29.77 (best of six seasons) |
| xwOBAcon | 0.288 | 0.277 (best of six seasons) |
| Run value / 100 | −0.228 | +0.025 (first positive in six seasons) |

A pitch was abandoned to scarcity, became effective again, and pitchers noticed
within a season. That is the neglected-niche thesis in its most direct form —
and it is why changeups dominate the conventional-slot outlier list above.
""") + fig("fig17_season_check",
           "Usage by family, splitter whiff rate, and the deathball's edge over "
           "ordinary sliders. All seasons truncated to the same calendar window; "
           "the dotted line marks the in-progress 2026 season.")),

    section("10", "What this means", "", "", body("""
1. **The homogenisation is real, but local.** Pitchers converge on the template
   for their pitch and arrive already conforming, and the joint shape space has
   measurably contracted (−8.7% per axis, p = 0.017). What is not shrinking is
   the number of templates — arsenals are broader than ever.
2. **Crowding degrades a pitch.** The same shape allows harder contact as more
   pitchers throw it. Popularity is self-limiting: the sweeper's six-season
   monotone value decline and the splitter's fading whiff rate are the same
   curve at two scales.
3. **Novelty is a real, decaying asset — measured in days, not pitches.** Its
   value shows up in 15–60-day exposure windows and decays fastest for the
   pitches that depend on it most. Within a single at-bat the logic inverts.
4. **The opportunity is scarcity, not strangeness.** Uniqueness added no
   predictive signal beyond shape, so the edge is not "be weird" — it is
   "occupy a shape hitters are not currently seeing." The changeup's 2026
   revival is that principle paying out in real time.
5. **Unusual pitches are underdeployed in every count.** The advantage is
   significant in all four count states, yet outlier-decile pitches get under a
   point more two-strike usage than when behind.
""")),

    section("11", "Limitations", "", "", body("""
- **Underpowered on univariate dispersion.** 115–440 pitchers per family-season
  cannot resolve a 5% change in a standard deviation. The per-family null is not
  evidence of absence; the multivariate test is where this study has power.
- **2026 is incomplete.** It is included on a matched calendar window, which
  makes it comparable but still leaves it a two-thirds season subject to
  in-season roster churn. Its trends are provisional until the season closes.
- **Date matching costs data.** Truncating all seasons to 13 August discards
  roughly a quarter of 2021–2025, which is why the scarcity panel retains 164
  cells rather than 240. The threshold sensitivity shows the conclusion holds.
- **Uniqueness is not exogenous.** It is computed from the same shape features
  used as controls, so the outlier study is associational. The scarcity panel
  and the familiarity model supply the identification.
- **Confounders spanning the window.** Foreign-substance enforcement (June 2021)
  cut spin sharply — spin results were re-run excluding pre-enforcement 2021;
  the pitch clock and shift ban (2023) are absorbed by year fixed effects;
  bat-tracking exists only from 2023 and is not used in the core models.
- **Taxonomy drift is handled but real.** Savant's classifier is applied
  retroactively, so sweeper labels reach back to 2021 — an advantage here, since
  one classifier sees every season. Primary analyses still run at family level.
"""))
]


def main() -> None:
    parts = [
        '<div class="wrap">',
        '<header class="masthead">',
        '<p class="eyebrow">Statcast study · 2021–2026 regular seasons</p>',
        "<h1>Is modern pitch design making pitchers throw the same?</h1>",
        '<p class="standfirst">Three million pitches say yes — locally, and at a '
        "cost the league is already paying. Pitchers converge on a handful of "
        "templates, crowded shapes lose their edge, and the pitch everyone "
        "abandoned just came back.</p>",
        '<dl class="runstrip">',
        "<div><dt>Pitches analysed</dt><dd>3,130,910</dd></div>",
        "<div><dt>Seasons</dt><dd>2021–26</dd></div>",
        "<div><dt>Pitcher-seasons</dt><dd>9,305</dd></div>",
        "<div><dt>Studies run</dt><dd>10</dd></div>",
        "</dl>",
        "</header>",
    ]
    parts.extend(SECTIONS)
    parts.append(
        "<footer>Data: Baseball Savant via the mlb-statcast-pipeline CLI. All "
        "seasons truncated to a matched calendar window (opening day to 13 "
        "August) because 2026 is still being played. Bootstraps use 2,000 "
        "replicates resampled by pitcher; multiplicity controlled at FDR "
        "q = 0.10 within each study. Every result carries a meta sidecar "
        "recording the git commit, parameters and data-manifest hash behind "
        "it.</footer>"
    )
    parts.append("</div>")

    html = (f"<title>{TITLE}</title>\n<style>{CSS}</style>\n"
            + "\n".join(parts))
    out = config.REPORT_DIR / "artifact.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
