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
    section("1", "The league-wide spread held up", "Not supported", "no", body("""
The most direct test of homogenisation asks whether the standard deviation of
pitch shapes shrank. Pooling all eight shape features into a single tested
number per family, with intervals from a 2,000-replicate bootstrap resampled by
pitcher:

| Family | Change in dispersion | 95% interval | p |
|---|---|---|---|
| Sinker | −7.5% | −18.0 to +8.3 | 0.32 |
| Cutter | −4.5% | −11.9 to +5.2 | 0.39 |
| Slider / Sweeper | −1.2% | −8.7 to +7.4 | 0.66 |
| Curveball | −0.9% | −8.2 to +5.9 | 0.68 |
| Changeup | +1.5% | −6.9 to +10.5 | 0.76 |
| Four-seam | +3.0% | −4.6 to +10.2 | 0.44 |

Nothing is significant. Four of six families lean toward narrowing, but every
interval comfortably contains zero, and none of the 112 individual
feature-by-family contrasts survive false-discovery correction.

The multivariate version pushes slightly harder. Measuring the *volume* of
occupied shape space, five of six families shrank, and pooling them gives
−0.46 log-units (−0.95 to +0.07, p = 0.098) — roughly −5.6% per shape axis.
Suggestive, not conclusive.
""") + readout("−5.6%", "pooled shape-space volume per axis · p = 0.098")
        + body("""
Two caveats keep this honest. Splitters could not be tested at all — too few
pitchers threw 100 of them in 2021. And with 150–500 pitchers per family-season,
this design cannot resolve a 5% change in a standard deviation. **The null is
weak evidence of absence, not evidence of absence.**
""") + fig("fig02_dispersion_contrast",
           "Change in league-wide spread by family and shape feature. "
           "Bars left of zero indicate convergence; whiskers are 95% "
           "pitcher-bootstrap intervals.")),

    section("2", "But pitchers drift toward the middle every year",
            "Supported", "yes", body("""
The population-level null hides a strong individual-level signal.

For every pitcher appearing in consecutive seasons, I measured whether his
year-over-year movement in shape space pointed toward the league centre.
Measurement noise alone manufactures fake convergence — a pitcher with a
lucky-high spin reading one year will "regress" the next — so starting position
was measured on one half of his pitches and movement on the other, then
benchmarked against a within-season null built the same way.

| Seasons | Movement toward centre | Share converging | Noise baseline |
|---|---|---|---|
| 2021 → 2022 | +0.143 | 65.7% | 54.0% |
| 2022 → 2023 | +0.162 | 66.8% | 53.8% |
| 2023 → 2024 | +0.120 | 61.2% | 53.0% |
| 2024 → 2025 | +0.121 | 62.0% | 51.7% |

Four seasons out of four. About two-thirds of pitchers drift toward the
league-average version of their own pitch, against a noise baseline near 52%.
The null sitting close to zero is what makes the signal believable.
""") + readout("62–67%", "of pitchers converge each season · baseline ≈ 52%")
        + body("""
### The new arrivals are already typical

If incumbents converge but league-wide spread holds, something must refill the
edges. The obvious candidate is turnover — rookies arriving with strange,
unpolished deliveries.

That is not what happens. Pitchers in their debut season sit **closer** to the
centre of their family than established pitchers (median −3.6%, paired
p = 0.019); 2024 debutants were 13% closer. Arrivals are *more* league-standard,
not less. The development pipeline is not merely polishing pitchers once they
reach the majors — it is delivering them pre-conformed.

### Yet arsenals grew broader

Cutting against all of the above, pitchers now throw more distinct pitch types,
more evenly — monotonically, in every season.

| | 2021 | 2025 |
|---|---|---|
| Usage entropy | 0.996 | 1.108 |
| Families thrown ≥5% | 3.15 | 3.47 |
| Share of top pitch | 49.0% | 43.3% |

So "homogenisation" is the wrong word at the arsenal level: variety *within* a
pitcher is rising even as each individual pitch converges on a template. Both
are true at once, and only the second is homogenisation.
""") + fig("fig06_convergence",
           "Crowding of the shape space and year-over-year movement toward the "
           "league centre, against the split-half noise benchmark.")),

    section("3", "Popular shapes get punished", "Supported", "yes", body("""
Pitch usage shifted substantially, and value moved against it. The two pitches
that gained the most usage both lost the most value, while the most-abandoned
pitch improved.

| Family | Usage 2021 → 2025 | Change in relative run value |
|---|---|---|
| Four-seam | 35.6% → 32.0% (−3.6pp) | +0.089 better |
| Slider / Sweeper | 19.4% → 22.6% (+3.2pp) | −0.218 worse |
| Splitter | 1.6% → 3.4% (+1.8pp) | −0.252 worse |
| Curveball | 9.6% → 8.5% (−1.1pp) | −0.247 worse |
| Changeup | 11.3% → 10.3% (−0.9pp) | +0.072 better |
| Sinker | 15.3% → 15.6% (+0.3pp) | +0.230 better |
| Cutter | 7.3% → 7.6% (+0.3pp) | −0.217 worse |

Across seven families the rank correlation is −0.32, which on its own proves
nothing. So the same question was asked at a far finer grain: divide each
family's shape space into cells of 2 mph × 4″ vertical break × 4″ horizontal
break, and ask whether **the same cell** performs worse in seasons when more
pitchers occupy it. Cell and year fixed effects absorb both "some shapes are
simply better" and league-wide run-environment drift. 240 cells, 1,200
cell-seasons.

| Outcome | Effect of doubling a shape's usage | p | Survives FDR |
|---|---|---|---|
| xwOBA on contact | +0.0073 worse | 0.0011 | yes |
| Whiff rate | −0.40pp worse | 0.114 | no |
| Run value / 100 | −0.02 worse | 0.765 | no |
| CSW rate | +0.22pp better | 0.231 | no |
""") + readout("+0.0073", "xwOBAcon penalty per doubling of a shape's usage · p = 0.0011", warm=True)
        + body("""
This is the study's cleanest result: **when a pitch shape becomes more common,
hitters square it up harder** — holding the shape itself constant. Halving a
shape's usage is worth about seven points of xwOBAcon. The other three outcomes
lean the same way without clearing significance.
""") + fig("fig13_niches",
           "Shape cells that lost usage while still outperforming league "
           "average, and the within-cell relationship between scarcity and value.")),

    section("4", "Unusual pitches really do work better", "Supported", "yes", body("""
Every arsenal was scored for how far it sits from its family's league
distribution that season, using a robust Mahalanobis distance cross-checked
against a nearest-neighbour density score. Comparing the most unusual decile
against the most typical:

| Outcome | Most typical | Most unusual | Difference |
|---|---|---|---|
| Whiff rate | 23.55% | 24.70% | +1.15pp |
| CSW rate | 27.41% | 28.19% | +0.77pp |
| Run value / 100 | 0.077 | 0.132 | +0.055 |
| xwOBA on contact | 0.313 | 0.307 | −0.005 |

All four favour the outliers. The obvious objection is selection: perhaps good
pitchers simply throw unusual pitches. To separate the two, uniqueness was split
into a between-pitcher component (a pitcher's career-average strangeness) and a
within-pitcher component (his own season-to-season deviation), with
pitcher-by-family fixed effects absorbed by demeaning.

| Outcome | Within-pitcher | Between-pitcher |
|---|---|---|
| Whiff rate | +1.762 (p<0.0001) | +1.766 (p<0.0001) |
| CSW rate | +0.831 (p=0.0001) | +0.972 (p<0.0001) |
| xwOBA on contact | −0.0055 (p=0.005) | −0.0064 (p<0.0001) |
| Run value / 100 | +0.054 (p=0.098) | +0.074 (p=0.0001) |
""") + readout("1.762 vs 1.766", "within- and between-pitcher whiff effect · not selection")
        + body("""
The within- and between-pitcher whiff coefficients are **essentially
identical**. When the same pitcher's pitch drifts from the league norm, it
misses more bats by the same margin that separates unusual pitchers from typical
ones. This is not a story about which pitchers own weird pitches.

### One important negative

A gradient-boosting model predicting whiffs from velocity, movement, location
and count was fit twice on 1.2 million swings — with and without the uniqueness
score. Adding it changed log-loss by +0.0001 and AUC by −0.0002. Nothing.

That clarifies rather than contradicts. Uniqueness is a deterministic function
of the shape features, so a flexible model given those features has already
extracted whatever it encodes. Being an outlier is not *extra* information on
top of your shape; it is a particular summary of your shape that tracks
effectiveness. The actionable claim survives. The claim that "unusual" is
independently predictive does not.
""") + fig("fig10_uniqueness_gradient",
           "Outcomes across uniqueness deciles, with pitcher-bootstrap "
           "intervals, and the fitted spline relationship.")),

    section("5", "Why it works: hitters adapt to what they see",
            "Supported", "yes", body("""
The mechanism evidence comes from the batter's side. For every pitch I counted
how many pitches of that same shape the hitter had faced in the previous 30
days, then estimated the effect **within batter** — comparing each hitter's own
well-prepared and poorly-prepared moments, with count, location and shape
controls. 3.36 million pitches, 825 hitters.

| Outcome | Effect of doubling recent exposure | p |
|---|---|---|
| Whiff per swing | −0.42pp | <0.00001 |
| CSW | −0.25pp | <0.00001 |

Familiarity blunts a pitch, and the estimate barely moves when the window
changes to 15 days (−0.41pp) or 60 days (−0.43pp).
""") + readout("−0.42pp", "whiff rate per doubling of a hitter's recent exposure", warm=True)
        + body("""
The interaction is the clincher: the exposure penalty is **larger for more
unusual pitches** (−0.0057, p = 0.0013 for whiffs; −0.0047, p = 0.0002 for CSW).
A common shape has little novelty to lose. An unusual one has a great deal, and
loses it as hitters see it.

That is precisely the proposed mechanism, and it explains the crowding-out
result: as a shape spreads, every hitter's recent exposure to it rises, and its
advantage erodes.
""") + fig("fig14_familiarity",
           "Whiff rate against recent exposure to the same shape, split by how "
           "unusual the pitch is, with the controlled within-batter estimate.")),

    section("6", "The existence proofs: two kinds of outlier", "", "", body("""
Uniqueness has two ingredients that should not be conflated: throwing from a
strange **place**, and throwing a strange **pitch**.

The overall ranking is owned by the first kind. Tyler Rogers' submarine sinker
— released at 1.2 ft with a −61° arm angle, against a league norm of 5.6 ft and
+33° — sits 20–25 standard units from the league centre and has been effective
for five straight seasons (positive run value every year; his most extreme
season, 2025, was his best at +1.42 per 100). But he is a *delivery* outlier:
that uniqueness comes bundled with the whole submarine mechanic, which is not
transferable advice.

So the ranking was recomputed on **movement only** — velocity, vertical and
horizontal break, spin — restricted to conventional arm slots between 10° and
60°. This is the actionable list: strange pitches thrown from ordinary places.

| Pitcher | Pitch | Season | Arm slot | Dist. from centre | Whiff% | RV/100 |
|---|---|---|---|---|---|---|
| Matt Andriese | Changeup | 2021 | 43.7° | 10.6 | 24.7 | −0.05 |
| Pedro Avila | Changeup | 2023 | 40.6° | 9.2 | 39.1 | +0.87 |
| David Bednar | Splitter | 2021 | 34.6° | 8.6 | 35.2 | +1.01 |
| Devin Williams | Changeup ("Airbender") | 2021 | 23.0° | 8.0 | 42.9 | −0.05 |
| Camilo Doval | Cutter | 2023 | 17.5° | 8.0 | 26.2 | +0.35 |
| Logan Allen | Changeup | 2023 | 42.0° | 7.7 | 30.5 | +0.75 |
| César Valdez | Changeup ("dead fish") | 2021 | 10.6° | 7.6 | 28.7 | −0.05 |
| Logan Webb | Changeup | 2022 | 12.5° | 7.4 | 25.0 | +0.85 |

Two patterns stand out. The league's strangest conventional-slot pitches are
overwhelmingly **changeups and splitters** — offspeed shapes that resist the
spin-based design templates. And the pitches the industry already celebrates as
unicorns (the Airbender, Webb's changeup, Bednar's splitter) fall out of the
arithmetic on their own — a sanity check that the score measures what it claims
to. The within-pitcher regression in the previous section is the systematic
version of this table; the effect depends on no single example.
""")),

    section("6b", "Two recolonizations, happening now", "Supported", "yes", body("""
The scarcity thesis predicts that neglected shapes get rediscovered, work well
early, and erode as they crowd. Two current cases let us watch it live.

### Splitters: the boom is already paying the crowding tax

| Season | Pitchers | Pitches | Whiff% | CSW% | RV/100 |
|---|---|---|---|---|---|
| 2021 | 75 | 11,448 | 35.8 | 26.1 | +0.37 |
| 2022 | 77 | 11,342 | 34.2 | 25.6 | +0.48 |
| 2023 | 105 | 16,796 | 34.0 | 25.0 | +0.45 |
| 2024 | 128 | 22,048 | 32.6 | 24.6 | +0.16 |
| 2025 | 166 | 24,017 | 33.0 | 24.4 | +0.12 |

Practitioners more than doubled; whiff rate, CSW and run value all fell as the
pitch spread. Adopters cut their changeup usage by 3–6 percentage points in the
adoption year — the boom is partly substitution inside the offspeed niche — and
splitter shape dispersion *widened* (IVB spread +29%), the signature of a niche
being colonized by newcomers trying different versions.

### The deathball: a scarce cell being deliberately farmed

The "deathball" — practitioner shorthand popularized around 2024 (Ryne Nelson,
Roki Sasaki) for a hard gyro slider with near-zero horizontal break and several
inches of depth — is invisible to family-level analysis because Statcast files
it under SL. It is precisely what this study says should exist: a scarce shape
cell being deliberately targeted. Operationalized as slider-family, ≥85 mph,
|HB| ≤ 3″, IVB ≤ −2″:

| Season | Deathballs | Pitchers | Whiff edge vs other sliders | RV edge |
|---|---|---|---|---|
| 2021 | 2,541 | 132 | +3.7pp | +0.45 |
| 2023 | 3,386 | 163 | +6.9pp | +0.22 |
| 2024 | 3,222 | 170 | +6.2pp | +0.60 |
| 2025 | 3,363 | 187 | +5.2pp | +0.11 |
""") + readout("+5 to +7pp", "deathball whiff edge over ordinary sliders — peaking 2023, eroding since")
        + body("""
The pitch out-whiffs ordinary sliders by four to seven points, practitioner
count climbs every season — and, right on schedule, the edge peaked in 2023 and
has shrunk each year since as adoption spreads. Leading 2025 practitioners:
Luke Jackson (323), Griffin Canning (215), Grant Holmes (180, 45.2% whiff),
Clay Holmes, Garrett Whitlock.
""") + fig("fig15_splitter_deathball",
           "Splitter adoption and whiff decline, and the deathball's share of "
           "slider-family pitches, 2021–2025.")),

    section("6c", "Sequencing and count", "Partial", "partial", body("""
Count entered the earlier models only as a control, and pitch-to-pitch
sequencing not at all. Both get direct treatment here — and the sequencing
result runs against conventional wisdom.

### Within-at-bat contrast does not buy whiffs

For 2.63 million pitches with a predecessor in the same at-bat, a standardized
shape gap (velocity, IVB, HB) was computed against the previous pitch and put
through the same within-batter machinery as the familiarity study — batter
fixed effects plus count, family, location and current-shape controls.

| Variable | Whiff effect | p | CSW effect | p |
|---|---|---|---|---|
| Shape gap from previous pitch | −0.32pp per unit | <0.001 | −0.22pp | <0.001 |
| Exact shape-cell repeat | +0.29pp | 0.019 | +0.51pp | <0.001 |

Bigger contrast with the previous pitch predicts slightly *fewer* whiffs, and
repeating the exact same shape twice in a row is mildly *good*. The novelty
that matters is measured in days and games — the 30-day exposure effect — not
in seconds within an at-bat. Hitters expect change; doubling up exploits the
expectation.

### The outlier advantage holds in every count — and is barely exploited

Re-running the within-batter whiff model separately by count state:

| Count state | Uniqueness whiff effect | p |
|---|---|---|
| Batter ahead | +1.83pp | <0.001 |
| Even | +2.99pp | <0.001 |
| Pitcher ahead | +2.88pp | <0.001 |
| Two strikes | +2.52pp | <0.001 |

Significant everywhere; largest in even and pitcher-ahead counts, smallest when
the batter is ahead. Deployment, though, is nearly flat: outlier-decile pitches
are thrown 19.9% of the time when the batter is ahead and 20.7% with two
strikes — less than a point of tilt toward putaway situations, against an edge
that holds in every count. Unusual pitches look underused everywhere, not just
saved for strikeouts.
""") + fig("fig16_sequencing",
           "Raw whiff rate by contrast with the previous pitch, and the "
           "within-batter uniqueness effect by count state.")),


    section("9", "2026 in-season check", "Out of sample", "yes", body("""
Everything above was produced before the 2026 season existed, which makes 2026
a genuine out-of-sample test rather than a refit. The season is two-thirds
complete, so **every season in this check is truncated to the same calendar
window** — opening day to 13 August — isolating what changed from the fact that
August is not October. Matched that way the six seasons run 499k–538k pitches
each.

**Seven of eleven claims hold.** The four that break turn out to support the
mechanism rather than undermine it.

| Claim | 2021–25 | 2026 | |
|---|---|---|---|
| Pitchers drift toward the league centre | 63.6% inward | 68.9% inward (null 56.7%) | holds |
| Arrivals more typical than incumbents | −5.1% | −2.2% | holds |
| Crowding degrades a shape (xwOBAcon) | +0.0106, p=0.001 | +0.0089, p=0.036 | holds |
| Recent exposure blunts a pitch | −0.42pp per doubling | −0.46pp, p=1.5e−28 | holds |
| Four-seam usage keeps falling | 35.2% → 31.8% | 30.7% (−1.09pp) | holds |
| Outlier advantage across counts | +1.8 to +3.0pp | 4/4 counts significant | holds |
| Sweeper usage keeps rising | 19.4% → 22.8% | 22.2% (−0.62pp) | breaks |
| Splitter usage keeps rising | 1.6% → 3.4% | 3.3% (−0.13pp) | breaks |
| Splitter keeps drawing practitioners | 72 → 151 | 136 | breaks |
| Deathball edge keeps eroding | +7.9pp peak, then +5.8 | +7.6pp | breaks |

Convergence was **stronger in 2026 than in any prior season**, and the sixth
season pushed the multivariate homogenisation test across the significance
line.
""") + readout("−8.7% per axis", "pooled shape-space volume, p = 0.017 — was −5.6%, p = 0.098")
        + body("""
### Why the failures matter

Three of the four are one event: **the sweeper and splitter booms stopped.** I
predicted their usage would keep rising. It fell. But the sweeper's relative run
value had declined *monotonically for six straight seasons* — +0.356, +0.242,
+0.214, +0.144, +0.048, −0.000 — and usage turned down in the exact season its
value reached zero. Splitter practitioners fell for the first time (151 → 136)
after its whiff rate eroded from 35.5% to 32.5%.

Crowding-out was the prediction; continued adoption was an extrapolation layered
on top of it, and only the extrapolation failed. A pitch whose value is being
competed away should eventually be abandoned, not adopted forever.

### The changeup came back

The clearest result of the check is the pitch nobody was watching. The changeup
was the most-abandoned offspeed pitch in the study — usage falling every year to
a six-season low, the worst relative run value of any family in 2025, and
actively cannibalised by splitter adopters. In 2026 it posted its best season on
every measure at once.

| | 2025 | 2026 |
|---|---|---|
| Usage | 10.15% | 11.21% (largest gain of any family) |
| Whiff% | 29.14 | 29.77 (best of six seasons) |
| xwOBAcon | 0.288 | 0.277 (best of six seasons) |
| Run value / 100 | −0.228 | +0.025 (first positive in six seasons) |

A pitch was abandoned to scarcity, became effective again, and pitchers noticed
within a season. That is the neglected-niche thesis in its most direct form.

### The one genuine miss

The deathball's edge over ordinary sliders did *not* keep eroding: +7.9pp
(2023) → +4.4 → +5.8 → +7.6pp (2026), while adoption jumped from 2,574 to 3,637
pitches. The earlier reading — "peaked in 2023 and declined each season since" —
over-fitted three noisy points. Across four seasons the edge oscillates between
+4 and +8pp with no detectable trend. The honest statement is that the deathball
carries a large and so-far *persistent* advantage. Whether it eventually erodes
like the sweeper is a question this data cannot yet answer.
""") + fig("fig17_season_check",
           "Usage by family, splitter whiff rate, and the deathball's edge "
           "over ordinary sliders. All seasons truncated to the same calendar "
           "window; the dotted line marks the in-progress 2026 season.")),

    section("7", "What this means", "", "", body("""
1. **The homogenisation is real, but local.** Pitchers converge on the template
   for their pitch and arrive already conforming. What is not shrinking is the
   number of templates.
2. **Crowding degrades a pitch.** The same shape allows harder contact as more
   pitchers throw it. Popularity is self-limiting — the sweeper's value
   decline, the splitter boom's fading whiff rate, and the deathball's
   shrinking edge are the same curve at three different scales.
3. **Novelty is a real, decaying asset — measured in days, not pitches.** Its
   value shows up in 15–60-day exposure windows and decays fastest for the
   pitches that depend on it most. Within a single at-bat the logic inverts:
   contrast with the previous pitch buys nothing and exact repetition is
   mildly good. Hitters expect change; they adapt to shapes over weeks.
4. **The opportunity is scarcity, not strangeness.** Uniqueness added no
   predictive signal beyond shape, so the edge is not "be weird" — it is
   "occupy a shape hitters are not currently seeing." The abandoned-niche table
   names specific candidates, and the conventional-slot unicorn list is
   dominated by changeups and splitters — the corner of shape space that still
   resists the design templates.
5. **Unusual pitches are underdeployed in every count.** The outlier whiff
   advantage is significant in all four count states, yet outlier-decile
   pitches are thrown barely one percentage point more often with two strikes
   than when behind. Deployment has not caught up to the edge.
""")),

    section("8", "Limitations", "", "", body("""
- **Underpowered on dispersion.** 150–500 pitchers per family-season cannot
  resolve a 5% change in spread. The first result is not "no homogenisation."
- **Five seasons is short** for a trend practitioners date to the mid-2010s; the
  2021 baseline is already deep into the pitch-design era.
- **Uniqueness is not exogenous.** It is computed from the same shape features
  used as controls, so the outlier study is associational. The scarcity panel
  (same shape, varying usage) and the familiarity model (same pitch, varying
  batter exposure) supply the identification.
- **Confounders spanning the window.** Foreign-substance enforcement in June
  2021 cut spin sharply, so spin results were re-run excluding pre-enforcement
  2021; the pitch clock and shift ban arrived in 2023 and are absorbed by year
  fixed effects; bat-tracking exists only from 2023 and is not used in the core
  models.
- **Taxonomy drift is handled but real.** Savant's classifier is applied
  retroactively, so sweeper labels reach back to 2021 — an advantage here, since
  one classifier sees every season. Primary analyses still run at family level.
""")),
]


def main() -> None:
    parts = [
        '<div class="wrap">',
        '<header class="masthead">',
        '<p class="eyebrow">Statcast study · 2021–2026 regular seasons</p>',
        "<h1>Is modern pitch design making pitchers throw the same?</h1>",
        '<p class="standfirst">Three and a half million pitches say yes — but '
        "not in the way the question implies. The league is not collapsing "
        "into one pitch. It is converging on a handful of templates, and "
        "paying for it.</p>",
        '<dl class="runstrip">',
        "<div><dt>Pitches analysed</dt><dd>3,554,404</dd></div>",
        "<div><dt>Seasons</dt><dd>2021–26</dd></div>",
        "<div><dt>Pitcher-seasons</dt><dd>9,191</dd></div>",
        "<div><dt>Studies run</dt><dd>10</dd></div>",
        "</dl>",
        "</header>",
    ]
    parts.extend(SECTIONS)
    parts.append(
        "<footer>Data: Baseball Savant via the mlb-statcast-pipeline CLI. "
        "Bootstraps use 2,000 replicates resampled by pitcher; multiplicity "
        "controlled at FDR q = 0.10 within each study. Every result carries a "
        "meta sidecar recording the git commit, parameters and data-manifest "
        "hash behind it.</footer>"
    )
    parts.append("</div>")

    html = (f"<title>{TITLE}</title>\n<style>{CSS}</style>\n"
            + "\n".join(parts))
    out = config.REPORT_DIR / "artifact.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
