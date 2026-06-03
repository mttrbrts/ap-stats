#!/usr/bin/env python3
"""Run all analyses and produce output/report.json + output/report.md."""

import json
import sys
import importlib
from datetime import datetime, timezone
from pathlib import Path

# Ensure analyze/ dir is on the path so scripts can `from common import *`
sys.path.insert(0, str(Path(__file__).parent))

from common import OUTPUT_DIR  # noqa: E402 — after path manipulation

SCRIPTS = [
    "01_most_active",
    "02_top_forks",
    "03_top_stars",
    "04_prs_by_month",
    "05_unique_contributors",
    "06_author_kind_proportion",
    "07_contributor_tenure",
    "08_lines_changed",
    "09_first_response_wait",
    "10_pr_merge_wait",
    "11_releases_per_month",
]

OUTPUT_FILES = {
    "01_most_active":            "q1_most_active.json",
    "02_top_forks":              "q2_top_forks.json",
    "03_top_stars":              "q3_top_stars.json",
    "04_prs_by_month":           "q4_prs_by_month.json",
    "05_unique_contributors":    "q5_unique_contributors.json",
    "06_author_kind_proportion": "q6_author_kind_proportion.json",
    "07_contributor_tenure":     "q7_contributor_tenure.json",
    "08_lines_changed":          "q8_lines_changed.json",
    "09_first_response_wait":    "q9_first_response_wait.json",
    "10_pr_merge_wait":          "q10_pr_merge_wait.json",
    "11_releases_per_month":     "q11_releases_per_month.json",
}

# Human-readable titles for report sections
TITLES = {
    "01_most_active":            "Most Active Repositories",
    "02_top_forks":              "Top Repositories by Forks",
    "03_top_stars":              "Top Repositories by Stars",
    "04_prs_by_month":           "Pull Requests by Month",
    "05_unique_contributors":    "Unique Contributors",
    "06_author_kind_proportion": "Author Kind Proportion",
    "07_contributor_tenure":     "Contributor Tenure",
    "08_lines_changed":          "Lines Changed per Month",
    "09_first_response_wait":    "First Response Wait Time",
    "10_pr_merge_wait":          "PR Merge Wait Time",
    "11_releases_per_month":     "Releases per Month",
}


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------

def _md_table(headers, rows):
    """Return a GitHub-flavoured markdown table string."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells):
        return "| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines = [fmt_row(headers), sep] + [fmt_row(r) for r in rows]
    return "\n".join(lines)


def render_q1(data):
    key = "q1_most_active"
    if key not in data:
        return "_No data_"
    repos = data[key]
    if not repos:
        return "_No data_"
    headers = ["Repo", "Stars", "Forks", "Open Issues", "Last Push"]
    rows = [[r.get("name", ""), r.get("stars", ""), r.get("forks", ""),
             r.get("open_issues", ""), r.get("pushed_at", "")[:10] if r.get("pushed_at") else ""]
            for r in repos]
    return _md_table(headers, rows)


def render_q2(data):
    key = "q2_top_forks"
    if key not in data:
        return "_No data_"
    repos = data[key]
    headers = ["Repo", "Forks", "Stars"]
    rows = [[r.get("name", ""), r.get("forks", ""), r.get("stars", "")] for r in repos]
    return _md_table(headers, rows)


def render_q3(data):
    key = "q3_top_stars"
    if key not in data:
        return "_No data_"
    repos = data[key]
    headers = ["Repo", "Stars", "Forks"]
    rows = [[r.get("name", ""), r.get("stars", ""), r.get("forks", "")] for r in repos]
    return _md_table(headers, rows)


def render_q4(data):
    key = "q4_prs_by_month"
    if key not in data:
        return "_No data_"
    months = data[key]
    if not months:
        return "_No data_"
    # months is a list of {"month": "YYYY-MM", "opened": n, "merged": n, "closed": n}
    # or a dict — handle both
    if isinstance(months, list):
        headers = list(months[0].keys())
        rows = [[str(row.get(h, "")) for h in headers] for row in months]
        return _md_table(headers, rows)
    # dict-of-month-to-counts
    all_months = sorted(months.keys())
    if not all_months:
        return "_No data_"
    sample = months[all_months[0]]
    sub_keys = list(sample.keys()) if isinstance(sample, dict) else ["count"]
    headers = ["Month"] + sub_keys
    rows = []
    for m in all_months:
        val = months[m]
        if isinstance(val, dict):
            rows.append([m] + [str(val.get(k, "")) for k in sub_keys])
        else:
            rows.append([m, str(val)])
    return _md_table(headers, rows)


def render_q5(data):
    key = "q5_unique_contributors"
    if key not in data:
        return "_No data_"
    contrib = data[key]
    if isinstance(contrib, dict) and "current" in contrib:
        headers = ["Window", "Unique Contributors"]
        rows = [
            ["Current", contrib["current"]],
            ["Prior", contrib.get("prior", "")],
        ]
        return _md_table(headers, rows)
    return f"Unique contributors: {contrib}"


def render_q6(data):
    key = "q6_author_kind"
    if key not in data:
        return "_No data_"
    q = data[key]
    current = q.get("current", {})
    prior = q.get("prior", {})
    kinds = ["Bot", "Maintainer", "First Time Contributor", "Early Contributor", "Seasoned Contributor"]
    headers = ["Author Kind", "Current %", "Prior %"]
    rows = [[k, current.get(k, 0), prior.get(k, 0)] for k in kinds]
    table = _md_table(headers, rows)
    totals = f"\nTotals — current: {q.get('current_total', '?')}, prior: {q.get('prior_total', '?')}"
    return table + totals


def render_q7(data):
    key = "q7_tenure"
    if key not in data:
        return "_No data_"
    q = data[key]
    headers = ["Cohort", "Avg Days", "P90 Days", "N"]
    rows = [
        ["Current", q["current"]["avg_days"], q["current"]["p90_days"], q["current"]["n"]],
        ["Prior",   q["prior"]["avg_days"],   q["prior"]["p90_days"],   q["prior"]["n"]],
    ]
    return _md_table(headers, rows)


def render_q8(data):
    key = "q8_lines_changed"
    if key not in data:
        return "_No data_"
    rows_data = data[key]
    if not rows_data:
        return "_No data_"
    headers = ["Month", "Additions", "Deletions", "Net"]
    rows = [[r["month"], f"{r['additions']:,}", f"{r['deletions']:,}", f"{r['net']:,}"]
            for r in rows_data]
    return _md_table(headers, rows)


def render_q9(data):
    key = "q9_first_response"
    if key not in data:
        return "_No data_"
    q = data[key]
    headers = ["Cohort", "Avg Hours", "P90 Hours", "N"]
    rows = [
        ["Current", q["current"]["avg_hours"], q["current"]["p90_hours"], q["current"]["n"]],
        ["Prior",   q["prior"]["avg_hours"],   q["prior"]["p90_hours"],   q["prior"]["n"]],
    ]
    return _md_table(headers, rows)


def render_q10(data):
    key = "q10_merge_wait"
    if key not in data:
        return "_No data_"
    q = data[key]
    headers = ["Cohort", "Avg Hours", "P90 Hours", "N"]
    rows = [
        ["Current", q["current"]["avg_hours"], q["current"]["p90_hours"], q["current"]["n"]],
        ["Prior",   q["prior"]["avg_hours"],   q["prior"]["p90_hours"],   q["prior"]["n"]],
    ]
    return _md_table(headers, rows)


RENDERERS = {
    "01_most_active":            render_q1,
    "02_top_forks":              render_q2,
    "03_top_stars":              render_q3,
    "04_prs_by_month":           render_q4,
    "05_unique_contributors":    render_q5,
    "06_author_kind_proportion": render_q6,
    "07_contributor_tenure":     render_q7,
    "08_lines_changed":          render_q8,
    "09_first_response_wait":    render_q9,
    "10_pr_merge_wait":          render_q10,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_scripts():
    """Import and call main() for each analysis script."""
    for script in SCRIPTS:
        print(f"\n{'='*60}")
        print(f"Running {script} ...")
        print("=" * 60)
        try:
            mod = importlib.import_module(script)
            # Reset sys.argv so argparse picks up no extra flags
            saved_argv = sys.argv
            sys.argv = [script]
            try:
                mod.main()
            finally:
                sys.argv = saved_argv
        except Exception as exc:
            print(f"ERROR in {script}: {exc}", file=sys.stderr)
            import traceback
            traceback.print_exc()


def merge_outputs():
    """Read individual output JSON files and merge into a single dict."""
    merged = {}
    for script, filename in OUTPUT_FILES.items():
        path = OUTPUT_DIR / filename
        if path.exists():
            try:
                data = json.loads(path.read_text())
                merged.update(data)
            except Exception as exc:
                print(f"WARNING: could not read {path}: {exc}", file=sys.stderr)
        else:
            print(f"WARNING: output file not found: {path}", file=sys.stderr)
    return merged


def write_report_json(merged):
    out_path = OUTPUT_DIR / "report.json"
    out_path.write_text(json.dumps(merged, indent=2))
    print(f"\nWrote {out_path}")
    return out_path


def write_report_md(merged):
    lines = ["# Accord Project GitHub Stats Report", ""]

    for i, script in enumerate(SCRIPTS, start=1):
        title = TITLES[script]
        lines.append(f"## Q{i} — {title}")
        lines.append("")

        # Add window metadata if present in merged data
        ws = merged.get("window_start")
        we = merged.get("window_end")
        ps = merged.get("prior_start")
        pe = merged.get("prior_end")

        # Try to get per-Q window info from the individual file
        filename = OUTPUT_FILES[script]
        path = OUTPUT_DIR / filename
        if path.exists():
            try:
                q_data = json.loads(path.read_text())
                ws = q_data.get("window_start", ws)
                we = q_data.get("window_end", we)
                ps = q_data.get("prior_start", ps)
                pe = q_data.get("prior_end", pe)
            except Exception:
                pass

        if ws and we:
            lines.append(f"_Current window: {ws} → {we}_")
        if ps and pe:
            lines.append(f"_Prior window: {ps} → {pe}_")
        lines.append("")

        renderer = RENDERERS.get(script)
        if renderer:
            try:
                lines.append(renderer(merged))
            except Exception as exc:
                lines.append(f"_Error rendering table: {exc}_")
        else:
            lines.append("_No renderer defined_")

        lines.append("")

    # Footer
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append("---")
    lines.append(f"_Generated at {generated_at}_")

    out_path = OUTPUT_DIR / "report.md"
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    return out_path


def maybe_run_presentation():
    """Call generate_presentation.main() if the module exists."""
    try:
        mod = importlib.import_module("generate_presentation")
        if hasattr(mod, "main"):
            print("\nRunning generate_presentation ...")
            mod.main()
    except ModuleNotFoundError:
        pass  # Not present — that's fine
    except Exception as exc:
        print(f"WARNING: generate_presentation failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def main():
    run_scripts()

    print(f"\n{'='*60}")
    print("Merging outputs into report.json and report.md ...")
    print("=" * 60)

    merged = merge_outputs()
    write_report_json(merged)
    write_report_md(merged)

    maybe_run_presentation()

    print("\nDone.")


if __name__ == "__main__":
    main()
