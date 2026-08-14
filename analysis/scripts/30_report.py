"""Assemble the final report from the committed results tables and figures.

Reads analysis/results/*.csv, writes report.md and a self-contained report.html
with figures embedded as base64 so the file can be published or emailed as one
artefact.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D


def read(name: str) -> pd.DataFrame:
    p = config.RESULTS_DIR / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def md_table(df: pd.DataFrame, cols: list[str] | None = None,
             rename: dict | None = None, floatfmt: int = 3) -> str:
    if df.empty:
        return "_no results_\n"
    d = df[cols] if cols else df
    d = d.rename(columns=rename or {})
    d = d.round(floatfmt)
    return d.to_markdown(index=False) + "\n"


def figure_block(name: str, caption: str) -> str:
    if not (config.FIGURES_DIR / f"{name}.png").exists():
        return ""
    return f"\n![{caption}](figures/{name}.png)\n\n*{caption}*\n"


def build_html(md_text: str, title: str) -> str:
    import markdown as md

    body = md.markdown(md_text, extensions=["tables", "toc", "fenced_code"])

    # inline every figure as base64 so the page is self-contained
    for png in sorted(config.FIGURES_DIR.glob("*.png")):
        b64 = base64.b64encode(png.read_bytes()).decode()
        body = body.replace(f'src="figures/{png.name}"',
                            f'src="data:image/png;base64,{b64}"')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b;
    --ink-2: #52514e; --ink-3: #898781; --rule: #e1e0d9; --accent: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff;
      --ink-2: #c3c2b7; --ink-3: #898781; --rule: #2c2c2a; --accent: #3987e5;
    }}
  }}
  :root[data-theme="dark"] {{
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff;
    --ink-2: #c3c2b7; --ink-3: #898781; --rule: #2c2c2a; --accent: #3987e5;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0; background: var(--page); color: var(--ink);
    font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  main {{ max-width: 62rem; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  h1 {{ font-size: 2.1rem; line-height: 1.2; letter-spacing: -0.02em;
        margin: 0 0 1.5rem; }}
  h2 {{ font-size: 1.4rem; margin: 3rem 0 0.75rem; letter-spacing: -0.01em;
        padding-top: 1.25rem; border-top: 1px solid var(--rule); }}
  h3 {{ font-size: 1.08rem; margin: 2rem 0 0.5rem; color: var(--ink); }}
  p, li {{ color: var(--ink-2); }}
  strong {{ color: var(--ink); font-weight: 650; }}
  a {{ color: var(--accent); }}
  code {{ background: var(--surface); padding: 0.1em 0.35em; border-radius: 4px;
          font-size: 0.88em; border: 1px solid var(--rule); }}
  img {{ max-width: 100%; height: auto; display: block; margin: 1.5rem auto 0.5rem;
         background: #fcfcfb; border: 1px solid var(--rule); border-radius: 8px;
         padding: 0.5rem; }}
  em {{ color: var(--ink-3); font-size: 0.9rem; }}
  .table-wrap, table {{ display: block; overflow-x: auto; max-width: 100%; }}
  table {{ border-collapse: collapse; margin: 1.25rem 0; font-size: 0.86rem; }}
  th, td {{ padding: 0.45rem 0.8rem; text-align: left; white-space: nowrap;
            border-bottom: 1px solid var(--rule); }}
  th {{ color: var(--ink); font-weight: 650; background: var(--surface); }}
  td {{ color: var(--ink-2); font-variant-numeric: tabular-nums; }}
  blockquote {{ margin: 1.5rem 0; padding: 0.9rem 1.2rem; background: var(--surface);
                border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0; }}
  blockquote p {{ margin: 0.3rem 0; }}
  hr {{ border: 0; border-top: 1px solid var(--rule); margin: 2.5rem 0; }}
</style>
</head>
<body><main>
{body}
</main></body>
</html>
"""


def main() -> None:
    manifest_path = config.RESULTS_DIR / "data_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    md_path = config.REPORT_DIR / "report.md"
    if not md_path.exists():
        raise SystemExit(
            "analysis/report/report.md not found. The narrative report is "
            "written by hand against the results tables; this script only "
            "renders it to HTML."
        )
    md_text = md_path.read_text()

    html = build_html(md_text, "Pitch Homogenization in MLB, 2021-2025")
    out = config.REPORT_DIR / "report.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html) / 1024:.0f} KB)")

    D.write_meta("s8_report", {
        "total_pitches": manifest.get("total_pitches"),
        "figures": sorted(p.name for p in config.FIGURES_DIR.glob("*.png")),
        "results_tables": sorted(p.name for p in config.RESULTS_DIR.glob("*.csv")),
    })


if __name__ == "__main__":
    main()
