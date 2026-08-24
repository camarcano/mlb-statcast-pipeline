# MLB team home run projections

Projects how many home runs each of the 30 clubs finishes the regular season
with, and how likely each is to lead the majors, from Statcast pitch-level data.

The projection is player-level: every hitter gets a home run rate per plate
appearance built from their own contact quality, those rates are weighted by how
much each hitter is actually playing, and the remaining schedule supplies the
parks and pitching staffs they will face. A Monte Carlo over that structure turns
the point estimate into a distribution, which is the part that matters when the
league leaders are separated by fewer home runs than a good week can produce.

Data comes from [`mlb-statcast-pipeline`](https://github.com/camarcano/mlb-statcast-pipeline),
which this project depends on and calls to keep its database current.

## Quick start on Windows

1. **Download the code.** On the [repository page](https://github.com/camarcano/mlb-statcast-pipeline/tree/claude/mlb-homer-projection-wa3in1),
   make sure the branch selector shows `claude/mlb-homer-projection-wa3in1`, then
   **Code → Download ZIP**, and unzip it somewhere like `C:\baseball\`. With git
   installed you can instead run:

   ```
   git clone -b claude/mlb-homer-projection-wa3in1 https://github.com/camarcano/mlb-statcast-pipeline.git
   ```

2. **Install Python 3.10 or newer** from [python.org/downloads](https://www.python.org/downloads/)
   if you do not have it. Tick **"Add python.exe to PATH"** in the installer.

3. **Double-click `setup.bat`** inside the `hr-projections` folder. It builds a
   virtual environment, installs everything, and downloads the season from
   Baseball Savant. This takes 15-20 minutes and happens once.

4. **Double-click `run.bat`.** It fetches whatever days are new, projects, prints
   the table, and opens the report in your browser.

From then on, step 4 is the whole routine.

To work in VS Code, open the **outer** folder (the one containing both `savant\`
and `hr-projections\`) with **File → Open Folder**. VS Code finds the `.venv`
that `setup.bat` created and offers it as the interpreter; the same
`python tools\bootstrap.py run` works in its terminal.

## Quick start on macOS and Linux

Same idea, without the batch files:

```bash
git clone -b claude/mlb-homer-projection-wa3in1 https://github.com/camarcano/mlb-statcast-pipeline.git
cd mlb-statcast-pipeline/hr-projections
python3 tools/bootstrap.py setup     # once, downloads the season
python3 tools/bootstrap.py run       # whenever you want fresh numbers
```

## Keeping up with the season

`run.bat` fetches **every day since the last one in your database**, so it does
not matter whether you last ran it yesterday or three weeks ago - it catches up
either way. It also re-fetches the most recent two days every time, because a day
first pulled while games were in progress gets recorded as complete while still
missing innings.

Each run writes `out\hr_projection_<date>.html` and a matching `.csv`, so you can
keep the files and watch the race move.

## The command line, for more control

The bootstrap script is a convenience wrapper. Once setup has run, the `hrproj`
command is available in the virtual environment
(`.venv\Scripts\hrproj.exe` on Windows, `.venv/bin/hrproj` elsewhere):

```bash
hrproj project                      # update data, then project
hrproj project --no-refresh         # skip the fetch, use the database as-is
hrproj project --format json,csv,html
hrproj players NYY                  # the hitters behind one club's number
hrproj backtest --cutoff 2026-07-01 # out-of-sample score vs simpler methods
hrproj backtest --cutoff 2026-07-01 --sweep
hrproj schedule-refresh             # re-cache the remaining schedule only
```

By default the Statcast database lives at `data\savant.db` inside the checkout and
nothing needs configuring. To keep it elsewhere, copy `.env.example` to `.env` and
set `HRPROJ_STATCAST_DB`.

### Output

```
Tm    HR  G-   Rest    Proj    p10    p90   Lead%  Top3%   Rk
WSN  183  30   40.2   223.2    210    237   28.4%  62.1%    1
```

`Rest` is expected home runs in the games that remain, `p10`/`p90` bound the
middle 80% of simulated final totals, and `Lead%` is the share of simulations in
which that club finishes with the most home runs in baseball. Team abbreviations
follow FanGraphs so the table lines up with published standings.

## How the projection works

**Home run rate per plate appearance.** Every batted ball is scored against a
league-wide empirical grid of exit velocity, launch angle and pull-relative
spray angle, giving each hitter an expected home run total - what their contact
deserved. Spray is in the grid on purpose: a 105 mph fly ball at 28 degrees
leaves the yard far more often when pulled, and an EV/LA-only model therefore
under-credits exactly the pull-heavy hitters who decide a home run race.

Each hitter's expected and actual home runs are blended (`phi`), weighted by
recency with a half-life in days (`half_life`), then regressed toward the league
rate in proportion to how little evidence there is (`k_pa`). The result is a Beta
posterior, so a 40-plate-appearance call-up carries visibly more uncertainty than
a 500-plate-appearance regular.

The default `phi` is 1.0 - contact only, actual home runs ignored - because that
is what the sweep picked at every cutoff tried. `phi=0.8` scores nearly as well
if you would rather keep some weight on results.

Two league-level corrections sit on top:

- **Normalisation.** Playing-time shares concentrate on hitters currently in the
  lineup, and those hitters out-homer the all-plate-appearance average. Left
  alone this inflates every club by about 3.5%, so all rates are scaled by one
  league-wide factor. Relative standings are untouched.
- **A flat league anchor.** Hitters regress toward the *season-to-date* league
  rate rather than a recency-weighted one. The league's home run environment
  swings with the weather - 2026 ran .0280 in April, .0343 in June, .0293 in
  August - and recency-weighting it projects the current month's weather into
  September. Anchoring flat cut the backtest bias from +2.0 home runs per club
  to -0.2.

**Playing time.** Shares of a team's plate appearances come from usage over the
last four weeks, not a depth chart. Hitters with no plate appearance in ten days
drop out, call-ups enter at the rate they are actually being used, and no one may
exceed 1.15/9 of a team's plate appearances.

**Context.** The remaining schedule comes from the MLB StatsAPI and is cached
locally. Each remaining game is adjusted by the park's home run factor and the
opposing staff's home runs allowed, both measured on air contact (10-50 degrees)
and both shrunk toward neutral, since one season of either is noisy. The
opponent adjustment divides out the park each game was played in, so a staff is
not penalised twice for its home ballpark. `--no-park` and `--no-opponent` turn
these off.

**Simulation.** Ten thousand trials draw each hitter's rate from its posterior,
each team's playing-time split from a Dirichlet, a league environment factor
shared by all 30 clubs (`league_env_sd`, default 7%, the month-to-month drift
left over once sampling noise is removed), and the home runs themselves from a
Poisson. The shared factor widens every interval without moving the odds of one
club out-homering another, which is exactly what an unforecastable warm or cold
September does.

## Checking the model, not trusting it

```bash
hrproj backtest --cutoff 2026-07-01
```

fits on data through the cutoff, projects the games that were actually played
afterwards, and scores mean absolute error against three baselines: the team's
home runs per game extrapolated forward, its expected home runs per game
extrapolated forward, and everyone regressed to the league rate. If the model
does not beat all three, it is not earning its complexity, and the output will
say so plainly.

On 2026 data, fit through July 1 and scored on the 1,338 team-games played
through August 23:

| method | MAE | RMSE | bias | worst |
| --- | --- | --- | --- | --- |
| model | 7.35 | 8.65 | -0.23 | 20.3 |
| league rate | 7.38 | 9.01 | -0.21 | 22.4 |
| team xHR/game | 8.38 | 9.89 | -1.05 | 26.6 |
| team HR/game | 9.22 | 10.65 | -0.32 | 23.1 |

Read that honestly. The model clearly beats extrapolating a team's own home run
rate, which is the thing most people would do - that baseline is 25% worse. Its
edge over simply regressing all 30 clubs to the league rate is much thinner: a
hair on MAE, a real 4% on RMSE, and three fewer home runs of worst-case error.
Over a 50-game horizon, team home run totals are mostly noise, and no amount of
modelling changes that. What the extra structure buys is a calibrated
distribution rather than a point estimate.

`--sweep` grid-searches `half_life`, `phi` and `k_pa` against the same holdout
and prints the best combination. The defaults in `hrproj/config.py`
(`half_life=75`, `phi=1.0`, `k_pa=400`) come from that search run across three
cutoffs; the top handful of settings were separated by less than the noise of a
30-team holdout, so do not read much into the exact numbers. Re-run the sweep as
the season progresses and override with `--half-life`, `--phi` and `--k-pa`.

## What the model does not know

- **Injuries and call-ups before they show up in usage.** A hitter who is hurt
  today still projects until his absence works through the four-week window.
  Nothing here reads a transactions feed.
- **September roster expansion**, which shifts playing time toward hitters with
  little or no track record.
- **Weather, and late-season park behaviour.** Cold September air suppresses home
  runs; park factors here are season-long averages. This is the single largest
  source of error at long horizons - projecting from June 1, the whole league
  then out-homered its season-to-date rate by roughly 9 home runs per club.
  `league_env_sd` puts that uncertainty into the intervals but cannot predict
  its direction.
- **Rest for clubs with nothing to play for**, which quietly removes plate
  appearances from a contender's best hitters in the final week.
- **Cancelled games that are never made up.** The schedule is taken as given.

The interval, not the point estimate, is where these live: they are part of why
p10 and p90 are as far apart as they are.

## Layout

| Module | Role |
| --- | --- |
| `config.py` | Paths, season dates, and `ModelParams` (every tunable constant) |
| `teams.py` | Team codes, FanGraphs display names, batting-team SQL |
| `refresh.py` | Brings the Statcast database current via the pipeline's own functions |
| `data.py` | Loads plate appearances and derives teams, contact flags, spray |
| `xhr.py` | The EV x LA x spray home run grid |
| `rates.py` | Per-hitter blended, regressed rate and its Beta posterior |
| `playing_time.py` | Team plate appearances per game and per-hitter shares |
| `schedule.py` | StatsAPI remaining schedule, cache, offline fallback |
| `park.py` | Park and opposing-staff home run factors |
| `model.py` | Assembles per-team projection inputs |
| `simulate.py` | Monte Carlo and finishing probabilities |
| `backtest.py` | Out-of-sample scoring and the parameter sweep |
| `report.py` | Console, CSV, JSON and HTML output |
| `cli.py` | The `hrproj` commands |

| Also | Role |
| --- | --- |
| `setup.bat` / `run.bat` | Double-clickable Windows entry points |
| `tools/bootstrap.py` | What those call: venv, install, backfill, project. Standard library only, so it runs before anything is installed |

## Tests

```bash
.venv/bin/pip install -e "hr-projections[dev]"    # .venv\Scripts\pip on Windows
.venv/bin/pytest hr-projections/tests
```

Tests build synthetic Statcast databases through the pipeline's real schema and
mock the StatsAPI, so no network access or season database is needed.

## Where this lives

Inside `mlb-statcast-pipeline`, under `hr-projections/`, on the branch
`claude/mlb-homer-projection-wa3in1`. It sits here rather than in its own
repository because it needs the pipeline anyway - one download gets you both the
data collection and the projections, and `setup.bat` wires them together.

Nothing in `savant/` or `webapp/` is modified by this project. It only reads the
database the pipeline builds, and calls the pipeline's own fetch functions to keep
that database current.
