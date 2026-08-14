# Prior work bearing on the homogenisation hypothesis

Annotated sources consulted before and during the analysis. Each entry records
the claim, how it was arrived at, and which of the seven studies (S1-S7) it
speaks to. Published figures quoted here are *not* used as inputs to the
analysis; where they overlap with quantities this study measures directly, the
report compares the two and flags disagreements.

## Pitch design as an industry practice

**Driveline Baseball, "Revisiting Stuff+" (2024) and "What Is Stuff?" (2021)**
— [drivelinebaseball.com](https://www.drivelinebaseball.com/2024/05/revisiting-stuff-plus/)
Documents the modelling machinery that pitch development now runs on: velocity,
movement, release and spin are fed to a model that scores a pitch's expected
run value, and pitchers train against that score. Directly motivates the
hypothesis. If every organisation optimises the same objective over the same
feature space, the optimum is a point, and arsenals should be drawn toward it.
*Bears on: S1, S2, S3.*

**FanGraphs Sabermetrics Library, "Stuff+, Location+ and Pitching+ Primer"**
— [library.fangraphs.com](https://library.fangraphs.com/pitching/stuff-location-and-pitching-primer/)
Stuff+ grades a pitch from physical characteristics alone, deliberately
excluding location and, critically, excluding how *common* the pitch is. A
stuff model cannot represent scarcity value: two identical shapes score
identically whether one is thrown by 200 pitchers or by one. This is exactly
the gap S5-S7 test.
*Bears on: S5, S6.*

**Driveline / RPP on Stuff+ limitations**
— [rocklandpeakperformance.com](https://rocklandpeakperformance.com/what-is-stuff-and-how-can-it-help-you/)
Notes that release point carries substantial weight in stuff models and may act
as a proxy for deception, and that pitchers routinely out-perform the sum of
their individual pitch grades. Repertoire-level effects that individual-pitch
models miss are the same family of effects the familiarity study targets.
*Bears on: S5, S7.*

## Evidence that the league adjusts to what it sees a lot of

**Baseball Prospectus, "Pitch Types and the Times Through the Order Penalty";
SABR/Lichtman on the same question**
— [baseballprospectus.com](https://www.baseballprospectus.com/news/article/22235/baseball-proguestus-pitch-types-and-the-times-through-the-order-penalty/),
[sabr.org](https://sabr.org/latest/lichtman-pitch-types-and-the-times-through-the-order-penalty/)
The times-through-the-order penalty is the cleanest established evidence that
exposure degrades a pitch. Repertoire size moderates it: narrower arsenals
decay faster within a game (roughly 36 points of wOBA for one-pitch pitchers
versus 24 for four-pitch pitchers, in Lichtman's accounting). The mechanism is
familiarity within a single game; S7 asks whether the same mechanism operates
across a *season* at the level of pitch shape rather than pitcher identity.
*Bears on: S7 (direct methodological ancestor).*

**Adam Salorio, "Introducing aStuff+ v2"**
— [adamsalorio.substack.com](https://adamsalorio.substack.com/p/introducing-astuff-v2)
Reports that pitch types hitters have grown more familiar with over time —
sweepers named explicitly — receive lower quality grades as that familiarity
accumulates. A stuff-model-side observation of the effect S6 and S7 test
directly.
*Bears on: S6, S7.*

## Pitch-mix trends: the counter-evidence

**MLB.com, "MLB pitch arsenals are bigger than ever in 2025"**
— [mlb.com](https://www.mlb.com/news/mlb-pitch-arsenals-are-bigger-than-ever-in-2025)
The strongest published counter-signal to the hypothesis: arsenals are
*widening*, not narrowing. Note that this is a claim about the number of
distinct pitch types a pitcher throws, which is a different quantity from the
dispersion of pitch *shapes* across the league. Both can move at once — every
pitcher carrying five pitches, each converging on a league-standard version of
that pitch, would satisfy both. S3 measures arsenal entropy so this claim can
be checked against the same data that produces the dispersion results.
*Bears on: S3, S4 (as a falsification target).*

**FanGraphs, "A League-Wide Update on Pitch Mix" and "Let's Take a Peek at Some
Early 2025 Pitch Usage Trends"**
— [blogs.fangraphs.com](https://blogs.fangraphs.com/a-league-wide-update-on-pitch-mix/),
[blogs.fangraphs.com](https://blogs.fangraphs.com/lets-take-a-peek-at-some-early-2025-pitch-usage-trends/)
Reports the gyro slider declining, breaking-ball selection diversifying, and no
single pitch sweeping the league in 2025. Note that a widely circulated figure
of sweeper usage "falling from 10.7% in 2019 to 8.1% in 2024" cannot be taken
at face value: Savant had no sweeper classification before 2023, so any
pre-2023 sweeper share is a retro-classification and not comparable with a
contemporaneous label. This study measures usage at the stable *family* level
for that reason.
*Bears on: S4 (and the taxonomy caveat throughout).*

**FanGraphs, "The Month of the Splitter"; Lookout Landing and ESPN on the kick
change**
— [blogs.fangraphs.com](https://blogs.fangraphs.com/the-month-of-the-splitter/),
[lookoutlanding.com](https://www.lookoutlanding.com/2025/2/28/24367452/what-the-kick-change-is-pitch-of-2025-andres-munoz-brian-bannister-supination-pronation),
[espn.com](https://www.espn.com/mlb/story/_/id/45007922/mlb-2025-kick-change-changeup-new-york-mets-holmes-canning-megill)
Splitter usage reached roughly 3.3% in 2025, the highest of the tracking era,
and the "kick change" spread rapidly as a splitter substitute for pitchers who
cannot throw one. Important for interpretation: the industry does periodically
*re-colonise* an abandoned niche, which is the behaviour the hypothesis
predicts should be profitable. Splitters are a live test case in S4/S6.
*Bears on: S4, S6.*

## Physics that makes non-standard shapes available

**Barton Smith (Utah State) via Driveline, "An Introduction to Seam-Shifted
Wakes" and "The Impact of Seam-Shifted Wakes on Pitch Quality"**
— [drivelinebaseball.com](https://www.drivelinebaseball.com/2020/11/more-than-what-it-seams-an-introduction-to-seam-shifted-wakes-and-their-effect-on-sinkers/),
[drivelinebaseball.com](https://www.drivelinebaseball.com/2021/03/the-impact-of-seam-shifted-wakes-on-pitch-quality/)
Non-Magnus movement means the reachable shape space is larger than a
spin-based model implies; sinkers and splitters in particular derive much of
their movement from boundary-layer asymmetry. Relevant because it establishes
that the empty regions found in S6 are not necessarily *physically*
unreachable — some are unoccupied by choice or by training convention.
*Bears on: S6 (interpretation of empty cells).*

## Deception and outlier release

**FanGraphs, "An Attempt to Quantify Pitcher Deception"; Towards Data Science,
"Quantifying Pitcher Deception"**
— [blogs.fangraphs.com](https://blogs.fangraphs.com/an-attempt-to-quantify-pitcher-deception/),
[towardsdatascience.com](https://towardsdatascience.com/quantifying-pitcher-deception-7fb2288661c8/)
Both frame deception as *deviation from expectation* — a pitch that behaves
unlike what its release and its owner's other pitches imply. This is
conceptually adjacent to the uniqueness score in S5, with one important
difference: these measures are relative to the pitcher, whereas the uniqueness
score here is relative to the league. The distinction matters and is discussed
in the report's limitations.
*Bears on: S5.*

## Confounders to control

**2021 foreign-substance enforcement** — [MLB.com FAQ](https://www.mlb.com/news/faq-sticky-stuff-and-new-rule-enforcement),
[Wikipedia](https://en.wikipedia.org/wiki/2021_sticky_stuff_controversy),
[The Ringer](https://www.theringer.com/2021/07/22/mlb/stick-stuff-pitchers-banned-foreign-subtances-spin-rate-offense)
Umpire checks began 21 June 2021; four-seam spin fell roughly 80 rpm (about
3.5%) and around 78% of pitchers lost spin. Any spin-dispersion result anchored
on 2021 is contaminated by this. S1 therefore re-runs the spin comparison using
only post-21-June data in 2021.

**2023 rule changes** — pitch clock and shift ban. Absorbed by year fixed
effects and by expressing outcomes relative to each season's league mean, since
they shift the run environment rather than pitch shape.

**Statcast coverage changes** — bat-tracking (`bat_speed`, `swing_length`)
begins in 2023 and covers only competitive swings; `arm_angle` is a derived
field published later and back-filled. Both are gated empirically in
`00_validate_data.py` rather than assumed.

## Where this study goes beyond the above

No source found measures the dispersion of pitch characteristics across
pitchers over time, which is the hypothesis stated literally. The clustering
literature (SABR's pitch-subtype work, model-based classification papers)
partitions pitches at a point in time rather than tracking the geometry of the
cloud across seasons, and the sequence-entropy work
([arXiv 2601.11904](https://arxiv.org/html/2601.11904)) measures diversity of
pitch *ordering* rather than of pitch shape. The scarcity panel (S6) and the
batter-exposure design (S7) also appear to be new: published work relates
effectiveness to a pitch's characteristics, not to how rare those
characteristics are.
