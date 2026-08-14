# Pitch homogenisation study

Tests whether modern pitch design has narrowed the range of pitch
characteristics thrown in MLB, and whether unusual pitches gain effectiveness
from their rarity. Covers the 2021-2025 regular seasons.

The written findings are in [`report/report.md`](report/report.md); prior work
is annotated in [`report/literature.md`](report/literature.md).

## Reproducing

```bash
pip install -e ".[analysis]"

# 1. ingest (several hours; resumable, safe to interrupt and restart)
statcast init
bash scripts/backfill_study.sh          # 2021-2025 regular season

# 2. analysis
python -m analysis.run_all              # or --studies 1 5 --quick
```

`run_all.py` runs the steps below in order. Each writes its results to
`analysis/results/` as CSV plus a `*_meta.json` sidecar recording the git SHA
and parameters used, so any table in the report can be traced to the code and
data that produced it.

| Step | Script | What it does |
|---|---|---|
| 0 | `00_validate_data.py` | Coverage and null-rate audit. Decides empirically whether `arm_angle` enters the feature vector and whether Savant's sweeper labels exist retroactively. Writes `data_manifest.json`. |
| x | `01_extract.py` | Copies the analysis columns from SQLite into a year-partitioned parquet snapshot. |
| f | `02_build_features.py` | Derives IVB, arm-side break and release geometry, assigns pitch families, and builds the pitcher-family-year arsenal table. Aborts if the handedness sign check fails. |
| 1 | `10_dispersion_trends.py` | S1: per-characteristic spread across pitchers, by season. |
| 2 | `11_multivariate_volume.py` | S2: log-volume and effective dimensionality of the shape cloud. |
| 3 | `12_pitcher_convergence.py` | S3: crowding, arsenal entropy, split-half directional drift. |
| 4 | `13_pitch_ecology.py` | S4: usage share and value by pitch family. |
| 5 | `20_outlier_effectiveness.py` | S5: uniqueness scoring; decile, spline, mixed-effects and gradient-boosting models. |
| 6 | `21_neglected_niches.py` | S6: within-cell scarcity panel regression. |
| 7 | `22_familiarity.py` | S7: batter exposure with batter fixed effects. |
| r | `30_report.py` | Renders `report.md` to a self-contained `report.html`. |

## Design notes

**Three grains.** Pitch grain (outcome models, familiarity); *arsenal rows* —
one row per pitcher-family-year with at least 100 pitches, the primary grain
for anything about spread, so a 3,000-pitch starter and a 300-pitch reliever
count once each; and shape cells (velocity x IVB x horizontal break) for the
scarcity panel.

**Handedness.** All horizontal quantities are sign-normalised so positive means
arm-side for both hands. `02_build_features.py` refuses to continue if sinkers
do not show strong positive arm-side break for both left- and right-handers,
because an inverted sign would silently corrupt every horizontal result.

**Taxonomy.** Savant introduced the sweeper (`ST`) and slurve (`SV`) codes in
2023 out of what had been `SL`. Primary analyses therefore run on stable
families (`config.PITCH_FAMILIES`); fine-grained types appear only in
`s4_fine_type_ecology.csv` and the stability table.

**Uncertainty.** Bootstrap intervals resample *pitchers*, not pitches, since a
pitcher contributes many correlated observations. Families of tests are
controlled with Benjamini-Hochberg at q = 0.10, and each study declares one
primary endpoint so conclusions do not rest on the best of fifty comparisons.

**What the studies can and cannot show.** S1-S4 are descriptive. S5 is
associational by construction: uniqueness is a deterministic function of the
shape features, so a model that already sees velocity and movement cannot be
"surprised" by it. The identification comes from S6, which holds the shape
fixed and varies only how often the league throws it, and from S7, which holds
the pitch fixed and varies how much the batter has recently seen it.

Configuration — thresholds, seeds, taxonomy, confounder dates — is centralised
in [`config.py`](config.py).
