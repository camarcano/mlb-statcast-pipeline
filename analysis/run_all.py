"""Run the study end to end.

    python -m analysis.run_all                 # everything
    python -m analysis.run_all --studies 1 5   # selected studies
    python -m analysis.run_all --quick         # few bootstrap reps, for smoke tests
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

STEPS = [
    ("0", "00_validate_data.py", "validate data, set feature gates"),
    ("x", "01_extract.py", "extract parquet snapshot"),
    ("f", "02_build_features.py", "build features and arsenal rows"),
    ("1", "10_dispersion_trends.py", "S1 dispersion trends"),
    ("2", "11_multivariate_volume.py", "S2 shape-space volume"),
    ("3", "12_pitcher_convergence.py", "S3 pitcher convergence"),
    ("4", "13_pitch_ecology.py", "S4 pitch ecology"),
    ("5", "20_outlier_effectiveness.py", "S5 outlier effectiveness"),
    ("6", "21_neglected_niches.py", "S6 neglected niches"),
    ("7", "22_familiarity.py", "S7 batter familiarity"),
    ("r", "30_report.py", "render report"),
]
# steps that accept a bootstrap-reps argument
TAKES_REPS = {"10_dispersion_trends.py", "11_multivariate_volume.py",
              "20_outlier_effectiveness.py"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--studies", nargs="*", default=None,
                    help="subset of step keys (0 x f 1..7 r); default all")
    ap.add_argument("--quick", action="store_true",
                    help="few bootstrap reps for a fast smoke test")
    args = ap.parse_args()

    steps = STEPS if args.studies is None else [
        s for s in STEPS if s[0] in set(args.studies)
    ]
    failures = []
    for key, script, label in steps:
        cmd = [sys.executable, str(SCRIPTS / script)]
        if args.quick and script in TAKES_REPS:
            cmd.append("50")
        print(f"\n{'=' * 72}\n[{key}] {label}\n{'=' * 72}", flush=True)
        t0 = time.time()
        rc = subprocess.call(cmd, cwd=ROOT.parent)
        print(f"--- {script} exited {rc} in {time.time() - t0:.0f}s", flush=True)
        if rc != 0:
            failures.append(script)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        return 1
    print("\nall steps completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
