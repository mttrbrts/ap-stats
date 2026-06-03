#!/usr/bin/env python3
"""Generate a self-contained presentation HTML from output/report.json."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"

COLORS = {
    "bg": "#0d1117",
    "surface": "#161b22",
    "blue": "#58a6ff",
    "green": "#3fb950",
    "red": "#f85149",
    "text": "#e6edf3",
    "muted": "#8b949e",
}

AGENDA = [
    "Most Active Repositories",
    "Top Repositories by Forks",
    "Top Repositories by Stars",
    "PRs Opened & Merged by Month",
    "Unique Contributors Over Time",
    "PR Author Mix",
    "Contributor Tenure",
    "Lines Changed per Month",
    "First Response Wait Time",
    "PR Merge Wait Time",
    "Releases per Month",
]

# GSoC 2026 key dates — used to contextualise spikes in the narrative
GSOC = {
    "year": 2026,
    "app_open":  "2026-03-16",
    "app_close": "2026-03-31",
    "accepted":  "2026-04-30",
    "bonding_start": "2026-05-01",
    "coding_start":  "2026-05-25",
    "midterm":   "2026-07-10",
}


def fetch_chartjs():
    try:
        import requests
        resp = requests.get(CHART_JS_CDN, timeout=10)
        resp.raise_for_status()
        print(f"  Chart.js downloaded ({len(resp.content):,} bytes)")
        return resp.text
    except Exception as e:
        print(f"  WARNING: Could not download Chart.js: {e}", file=sys.stderr)
        print(f"  WARNING: Falling back to CDN script tag (requires internet at presentation time)", file=sys.stderr)
        return None


def delta_badge(current_val, prior_val, inverted=False):
    if prior_val == 0:
        return ""
    pct = (current_val - prior_val) / prior_val * 100
    sign = "▲" if pct >= 0 else "▼"
    colour = "green" if pct >= 0 else "red"
    if inverted:
        colour = "red" if pct >= 0 else "green"
    css_colour = "#3fb950" if colour == "green" else "#f85149"
    return f'<span style="color:{css_colour};font-size:1.2rem;margin-left:0.5rem">{sign} {abs(pct):.1f}%</span>'


def fmt_hours(h):
    if h >= 24:
        days = h / 24
        return f"{days:.1f}d"
    return f"{h:.1f}h"


def slide_wrapper(index, title, subtitle, content_html):
    return f"""
<div class="slide" id="slide-{index}">
  <div class="slide-inner">
    <div class="slide-header">
      <div class="slide-title">{title}</div>
      {f'<div class="slide-subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    <div class="slide-content">
      {content_html}
    </div>
  </div>
</div>
"""


def no_data_slide(index, title, subtitle=""):
    content = '<div class="no-data">No data available</div>'
    return slide_wrapper(index, title, subtitle, content)


def make_slide_0(report):
    window_start = report.get("window_start", "")
    window_end = report.get("window_end", "")
    agenda_items = "".join(
        f'<li><span class="agenda-num">{i+1}</span>{title}</li>'
        for i, title in enumerate(AGENDA)
    )
    content = f"""
<div class="title-slide-body">
  <div class="title-date">{window_start} – {window_end}</div>
  <ol class="agenda-list">{agenda_items}</ol>
</div>
"""
    return slide_wrapper(0, "Accord Project", "GitHub Statistics", content)


def make_slide_1(report):
    key = "q1_most_active"
    if key not in report or not report[key]:
        return no_data_slide(1, "Most Active Repositories", "Q1")
    data = sorted(report[key], key=lambda x: x.get("score", 0), reverse=True)
    labels = json.dumps([d["repo"] for d in data])
    prs_opened = json.dumps([d.get("prs_opened", 0) for d in data])
    prs_merged = json.dumps([d.get("prs_merged", 0) for d in data])
    authors = json.dumps([d.get("unique_authors", 0) for d in data])
    bar_h = max(40 * len(data), 300)
    content = f"""
<div class="chart-container" style="height:{bar_h}px;max-height:68vh;">
  <canvas id="chart-q1"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q1'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [
        {{
          label: 'PRs Opened',
          data: {prs_opened},
          backgroundColor: 'rgba(88,166,255,0.85)',
          borderRadius: 3,
        }},
        {{
          label: 'PRs Merged',
          data: {prs_merged},
          backgroundColor: 'rgba(63,185,80,0.85)',
          borderRadius: 3,
        }},
        {{
          label: 'Unique Authors',
          data: {authors},
          backgroundColor: 'rgba(139,148,158,0.7)',
          borderRadius: 3,
        }},
      ]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '{COLORS["text"]}', font: {{ size: 13 }} }} }},
      }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{ ticks: {{ color: '{COLORS["text"]}', font: {{ size: 13 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(1, "Most Active Repositories", "PRs opened · merged · unique authors", content)


def make_slide_2(report):
    key = "q2_top_forks"
    if key not in report or not report[key]:
        return no_data_slide(2, "Top Repositories by Forks", "Q2")
    data = sorted(report[key], key=lambda x: x.get("forks", 0), reverse=True)[:10]
    labels = json.dumps([d["repo"] for d in data])
    values = json.dumps([d.get("forks", 0) for d in data])
    bar_h = max(40 * len(data), 280)
    content = f"""
<div class="chart-container" style="height:{bar_h}px;max-height:68vh;">
  <canvas id="chart-q2"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q2'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [{{
        label: 'Forks',
        data: {values},
        backgroundColor: 'rgba(88,166,255,0.85)',
        borderRadius: 4,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{ ticks: {{ color: '{COLORS["text"]}', font: {{ size: 13 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(2, "Top Repositories by Forks", "Q2", content)


def make_slide_3(report):
    key = "q3_top_stars"
    if key not in report or not report[key]:
        return no_data_slide(3, "Top Repositories by Stars", "Q3")
    data = sorted(report[key], key=lambda x: x.get("stars", 0), reverse=True)[:10]
    labels = json.dumps([d["repo"] for d in data])
    values = json.dumps([d.get("stars", 0) for d in data])
    bar_h = max(40 * len(data), 280)
    content = f"""
<div class="chart-container" style="height:{bar_h}px;max-height:68vh;">
  <canvas id="chart-q3"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q3'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [{{
        label: 'Stars',
        data: {values},
        backgroundColor: 'rgba(248,209,18,0.82)',
        borderRadius: 4,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{ ticks: {{ color: '{COLORS["text"]}', font: {{ size: 13 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(3, "Top Repositories by Stars", "Q3", content)


def make_slide_4(report):
    key = "q4_prs_by_month"
    if key not in report or not report[key]:
        return no_data_slide(4, "PRs Opened & Merged by Month", "Q4")
    data = sorted(report[key], key=lambda x: x["month"])[-12:]
    labels = json.dumps([d["month"] for d in data])
    opened = json.dumps([d.get("opened", 0) for d in data])
    merged = json.dumps([d.get("merged", 0) for d in data])
    opened_prior = json.dumps([d.get("opened_prior", 0) for d in data])
    merged_prior = json.dumps([d.get("merged_prior", 0) for d in data])
    content = f"""
<div class="chart-container" style="height:65vh;">
  <canvas id="chart-q4"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q4'), {{
    type: 'line',
    data: {{
      labels: {labels},
      datasets: [
        {{
          label: 'Opened (current)',
          data: {opened},
          borderColor: '{COLORS["blue"]}',
          backgroundColor: 'rgba(88,166,255,0.08)',
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 4,
        }},
        {{
          label: 'Merged (current)',
          data: {merged},
          borderColor: '{COLORS["green"]}',
          backgroundColor: 'rgba(63,185,80,0.08)',
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 4,
        }},
        {{
          label: 'Opened (prior year)',
          data: {opened_prior},
          borderColor: 'rgba(88,166,255,0.45)',
          borderDash: [6,4],
          borderWidth: 1.8,
          tension: 0.3,
          pointRadius: 2,
        }},
        {{
          label: 'Merged (prior year)',
          data: {merged_prior},
          borderColor: 'rgba(63,185,80,0.45)',
          borderDash: [6,4],
          borderWidth: 1.8,
          tension: 0.3,
          pointRadius: 2,
        }},
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '{COLORS["text"]}', font: {{ size: 13 }}, boxWidth: 20 }} }},
      }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(4, "PRs Opened &amp; Merged by Month", "Current vs prior year · last 12 months", content)


def make_slide_5(report):
    key = "q5_contributors"
    if key not in report or not report[key]:
        return no_data_slide(5, "Unique Contributors", "Q5")
    q5 = report[key]
    # Support both old flat-list format and new {current, prior} dict format
    if isinstance(q5, list):
        current_rows = sorted(q5, key=lambda x: x["month"])
        prior_rows = []
    else:
        current_rows = q5.get("current", [])
        prior_rows = q5.get("prior", [])

    # Use month position labels (Jun, Jul, …) shared by both series
    labels = json.dumps([d["month"][-2:] + "/" + d["month"][:4] for d in current_rows])

    cur_new   = json.dumps([d.get("new", 0) for d in current_rows])
    cur_cum   = json.dumps([d.get("cumulative", 0) for d in current_rows])
    pri_new   = json.dumps([d.get("new", 0) for d in prior_rows]) if prior_rows else "[]"
    pri_cum   = json.dumps([d.get("cumulative", 0) for d in prior_rows]) if prior_rows else "[]"

    cur_total = report.get("current_total", current_rows[-1]["cumulative"] if current_rows else 0)
    pri_total = report.get("prior_total", prior_rows[-1]["cumulative"] if prior_rows else 0)
    window_start = report.get("window_start", "")
    prior_start  = report.get("prior_start", "")

    prior_datasets = f"""
        {{
          type: 'line',
          label: 'Cumulative {prior_start[:4]}',
          data: {pri_cum},
          borderColor: 'rgba(88,166,255,0.35)',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          borderDash: [4,3],
          tension: 0.3,
          pointRadius: 0,
          yAxisID: 'y2',
        }},
        {{
          type: 'bar',
          label: 'New/month {prior_start[:4]}',
          data: {pri_new},
          backgroundColor: 'rgba(63,185,80,0.25)',
          borderRadius: 3,
          yAxisID: 'y',
        }},""" if prior_rows else ""

    content = f"""
<div class="stat-footnote" style="text-align:right;margin-bottom:0.5rem">
  New contributors &nbsp;·&nbsp;
  <strong style="color:{COLORS["blue"]}">{cur_total}</strong> {window_start[:4]}
  &nbsp;vs&nbsp;
  <strong style="color:rgba(88,166,255,0.6)">{pri_total}</strong> {prior_start[:4]}
</div>
<div class="chart-container" style="height:62vh;">
  <canvas id="chart-q5"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q5'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [
        {{
          type: 'line',
          label: 'Cumulative {window_start[:4]}',
          data: {cur_cum},
          borderColor: '{COLORS["blue"]}',
          backgroundColor: 'transparent',
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 3,
          yAxisID: 'y2',
        }},
        {{
          type: 'bar',
          label: 'New/month {window_start[:4]}',
          data: {cur_new},
          backgroundColor: 'rgba(63,185,80,0.75)',
          borderRadius: 3,
          yAxisID: 'y',
        }},{prior_datasets}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '{COLORS["text"]}', font: {{ size: 13 }}, boxWidth: 20 }} }},
      }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 11 }}, maxRotation: 45 }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{
          type: 'linear', position: 'left',
          ticks: {{ color: '{COLORS["green"]}', font: {{ size: 12 }} }},
          grid: {{ color: 'rgba(255,255,255,0.07)' }},
          title: {{ display: true, text: 'New / month', color: '{COLORS["green"]}', font: {{ size: 12 }} }},
        }},
        y2: {{
          type: 'linear', position: 'right',
          ticks: {{ color: '{COLORS["blue"]}', font: {{ size: 12 }} }},
          grid: {{ drawOnChartArea: false }},
          title: {{ display: true, text: 'Cumulative', color: '{COLORS["blue"]}', font: {{ size: 12 }} }},
        }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(5, "Unique Contributors", "New per month (bars) · cumulative (line) · current vs prior year", content)


def make_slide_6(report):
    key = "q6_author_kind"
    if key not in report:
        return no_data_slide(6, "PR Author Mix", "Q6")
    kinds = ["Bot", "Maintainer", "First Time Contributor", "Early Contributor", "Seasoned Contributor"]
    current = report[key].get("current", {})
    prior = report[key].get("prior", {})
    cur_vals = json.dumps([current.get(k, 0) for k in kinds])
    pri_vals = json.dumps([prior.get(k, 0) for k in kinds])
    labels = json.dumps(kinds)
    content = f"""
<div class="chart-container" style="height:65vh;">
  <canvas id="chart-q6"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q6'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [
        {{
          label: 'Current period',
          data: {cur_vals},
          backgroundColor: 'rgba(88,166,255,0.85)',
          borderRadius: 3,
        }},
        {{
          label: 'Prior period',
          data: {pri_vals},
          backgroundColor: 'rgba(88,166,255,0.35)',
          borderRadius: 3,
        }},
      ]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '{COLORS["text"]}', font: {{ size: 13 }}, boxWidth: 20 }} }},
        tooltip: {{
          callbacks: {{
            label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.x.toFixed(1)}}%`
          }}
        }}
      }},
      scales: {{
        x: {{
          ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }}, callback: v => v + '%' }},
          grid: {{ color: 'rgba(255,255,255,0.07)' }},
          max: 100,
        }},
        y: {{ ticks: {{ color: '{COLORS["text"]}', font: {{ size: 13 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(6, "PR Author Mix", "Current vs prior period · % of PRs", content)


def make_slide_7(report):
    key = "q7_tenure"
    if key not in report:
        return no_data_slide(7, "Contributor Tenure", "Q7")
    cur = report[key].get("current", {})
    pri = report[key].get("prior", {})
    avg_cur = cur.get("avg_days", 0)
    avg_pri = pri.get("avg_days", 0)
    p90_cur = cur.get("p90_days", 0)
    p90_pri = pri.get("p90_days", 0)
    n_cur = cur.get("n", 0)
    n_pri = pri.get("n", 0)
    avg_badge = delta_badge(avg_cur, avg_pri, inverted=False)
    p90_badge = delta_badge(p90_cur, p90_pri, inverted=False)
    content = f"""
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">Avg Tenure (current)</div>
    <div class="stat-value">{avg_cur:.1f}<span class="stat-unit">d</span>{avg_badge}</div>
    <div class="stat-compare">Prior: {avg_pri:.1f}d</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">P90 Tenure (current)</div>
    <div class="stat-value">{p90_cur:.1f}<span class="stat-unit">d</span>{p90_badge}</div>
    <div class="stat-compare">Prior: {p90_pri:.1f}d</div>
  </div>
</div>
<div class="stat-footnote">Sample size: current n={n_cur} · prior n={n_pri} &nbsp;|&nbsp; Delta badge: <span style="color:{COLORS['green']}">▼ green = improvement</span>, <span style="color:{COLORS['red']}">▲ red = regression</span></div>
"""
    return slide_wrapper(7, "Contributor Tenure", "Days since first contribution at PR open time", content)


def make_slide_8(report):
    key = "q8_lines_changed"
    if key not in report or not report[key]:
        return no_data_slide(8, "Lines Changed per Month", "Q8")
    q8 = report[key]
    cur_data  = sorted(q8.get("current", q8) if isinstance(q8, dict) else q8, key=lambda x: x["month"])
    pri_data  = sorted(q8.get("prior", []),  key=lambda x: x["month"]) if isinstance(q8, dict) else []

    window_start = report.get("window_start", "")
    prior_start  = report.get("prior_start",  "")

    labels   = json.dumps([d["month"] for d in cur_data])
    cur_add  = json.dumps([d.get("additions", 0) for d in cur_data])
    cur_del  = json.dumps([-abs(d.get("deletions", 0)) for d in cur_data])
    cur_net  = json.dumps([d.get("net", 0) for d in cur_data])
    pri_add  = json.dumps([d.get("additions", 0) for d in pri_data])
    pri_del  = json.dumps([-abs(d.get("deletions", 0)) for d in pri_data])
    pri_net  = json.dumps([d.get("net", 0) for d in pri_data])

    prior_datasets = f"""
        {{
          type: 'bar',
          label: 'Additions {prior_start[:4]}',
          data: {pri_add},
          backgroundColor: 'rgba(63,185,80,0.2)',
          borderRadius: 0,
        }},
        {{
          type: 'bar',
          label: 'Deletions {prior_start[:4]}',
          data: {pri_del},
          backgroundColor: 'rgba(248,81,73,0.2)',
          borderRadius: 0,
        }},
        {{
          type: 'line',
          label: 'Net {prior_start[:4]}',
          data: {pri_net},
          borderColor: 'rgba(88,166,255,0.35)',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          borderDash: [4,3],
          tension: 0.3,
          pointRadius: 0,
        }},""" if pri_data else ""

    content = f"""
<div class="chart-container" style="height:65vh;">
  <canvas id="chart-q8"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q8'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [
        {{
          type: 'bar',
          label: 'Additions {window_start[:4]}',
          data: {cur_add},
          backgroundColor: 'rgba(63,185,80,0.6)',
          borderRadius: 0,
        }},
        {{
          type: 'bar',
          label: 'Deletions {window_start[:4]}',
          data: {cur_del},
          backgroundColor: 'rgba(248,81,73,0.6)',
          borderRadius: 0,
        }},
        {{
          type: 'line',
          label: 'Net {window_start[:4]}',
          data: {cur_net},
          borderColor: '{COLORS["blue"]}',
          backgroundColor: 'transparent',
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 3,
        }},{prior_datasets}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '{COLORS["text"]}', font: {{ size: 13 }}, boxWidth: 20 }} }},
      }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }}, maxRotation: 45 }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{
          ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }},
          grid: {{ color: 'rgba(255,255,255,0.07)' }},
        }},
      }}
    }}
  }});
}})();
</script>
<div class="stat-footnote" style="margin-top:0.6rem">
  <strong style="color:{COLORS['text']}">May 2026 peak — merged contributions:</strong>
  &nbsp;
  <a href="https://github.com/accordproject/cicero-template-library/pull/512" style="color:{COLORS['blue']}">cicero-template-library#512</a> (+73k/−2k @mttrbrts)
  &nbsp;·&nbsp;
  <a href="https://github.com/accordproject/cicero-template-library/pull/484" style="color:{COLORS['blue']}">#484</a> (+42k/−23k @mttrbrts)
  &nbsp;·&nbsp;
  <a href="https://github.com/accordproject/web-components/pull/449" style="color:{COLORS['blue']}">web-components#449</a> (+32k/−9k @soniaduma)
  &nbsp;·&nbsp;
  <a href="https://github.com/accordproject/markdown-transform/pull/675" style="color:{COLORS['blue']}">markdown-transform#675</a> (−31k @muhabdulkadir)
  &nbsp;·&nbsp;
  <a href="https://github.com/accordproject/concerto/pull/1230" style="color:{COLORS['blue']}">concerto#1230</a> (+14k/−11k @muhabdulkadir)
  &nbsp;·&nbsp;
  <span style="color:{COLORS['muted']}">Note: counts merged PRs only — closed dependabot lock-file PRs (~3.9M LOC in web-components) are excluded.</span>
</div>
"""
    return slide_wrapper(8, "Lines Changed per Month", "Merged PRs only · additions · deletions · net · current vs prior year", content)


def make_slide_9(report):
    key = "q9_first_response"
    if key not in report:
        return no_data_slide(9, "First Response Wait Time", "Q9")
    cur = report[key].get("current", {})
    pri = report[key].get("prior", {})
    avg_cur = cur.get("avg_hours", 0)
    avg_pri = pri.get("avg_hours", 0)
    p90_cur = cur.get("p90_hours", 0)
    p90_pri = pri.get("p90_hours", 0)
    n_cur = cur.get("n", 0)
    n_pri = pri.get("n", 0)
    avg_badge = delta_badge(avg_cur, avg_pri, inverted=True)
    p90_badge = delta_badge(p90_cur, p90_pri, inverted=True)
    content = f"""
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">Avg First Response (current)</div>
    <div class="stat-value">{fmt_hours(avg_cur)}{avg_badge}</div>
    <div class="stat-compare">Prior: {fmt_hours(avg_pri)}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">P90 First Response (current)</div>
    <div class="stat-value">{fmt_hours(p90_cur)}{p90_badge}</div>
    <div class="stat-compare">Prior: {fmt_hours(p90_pri)}</div>
  </div>
</div>
<div class="stat-footnote">Sample size: current n={n_cur} · prior n={n_pri} &nbsp;|&nbsp; Delta badge: <span style="color:{COLORS['green']}">▼ green = improvement</span>, <span style="color:{COLORS['red']}">▲ red = regression</span></div>
"""
    return slide_wrapper(9, "First Response Wait Time", "Time from PR open to first non-author comment", content)


def make_slide_10(report):
    key = "q10_merge_wait"
    if key not in report:
        return no_data_slide(10, "PR Merge Wait Time", "Q10")
    cur = report[key].get("current", {})
    pri = report[key].get("prior", {})
    avg_cur = cur.get("avg_hours", 0)
    avg_pri = pri.get("avg_hours", 0)
    p90_cur = cur.get("p90_hours", 0)
    p90_pri = pri.get("p90_hours", 0)
    n_cur = cur.get("n", 0)
    n_pri = pri.get("n", 0)
    avg_badge = delta_badge(avg_cur, avg_pri, inverted=True)
    p90_badge = delta_badge(p90_cur, p90_pri, inverted=True)
    content = f"""
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">Avg Merge Wait (current)</div>
    <div class="stat-value">{fmt_hours(avg_cur)}{avg_badge}</div>
    <div class="stat-compare">Prior: {fmt_hours(avg_pri)}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">P90 Merge Wait (current)</div>
    <div class="stat-value">{fmt_hours(p90_cur)}{p90_badge}</div>
    <div class="stat-compare">Prior: {fmt_hours(p90_pri)}</div>
  </div>
</div>
<div class="stat-footnote">Sample size: current n={n_cur} · prior n={n_pri} &nbsp;|&nbsp; Delta badge: <span style="color:{COLORS['green']}">▼ green = improvement</span>, <span style="color:{COLORS['red']}">▲ red = regression</span></div>
"""
    return slide_wrapper(10, "PR Merge Wait Time", "Time from PR open to merge (merged PRs only)", content)


def make_slide_11(report):
    key = "q11_releases"
    if key not in report or not report[key]:
        return no_data_slide(11, "Releases per Month", "Q11")
    q11 = report[key]
    current_rows = q11.get("current", [])
    prior_rows   = q11.get("prior", [])
    cur_total = report.get("current_total", sum(r["total"] for r in current_rows))
    pri_total = report.get("prior_total",   sum(r["total"] for r in prior_rows))
    window_start = report.get("window_start", "")
    prior_start  = report.get("prior_start", "")

    labels      = json.dumps([r["month"] for r in current_rows])
    cur_stable  = json.dumps([r.get("stable", 0)     for r in current_rows])
    cur_pre     = json.dumps([r.get("prerelease", 0) for r in current_rows])
    pri_stable  = json.dumps([r.get("stable", 0)     for r in prior_rows])
    pri_pre     = json.dumps([r.get("prerelease", 0) for r in prior_rows])

    total_badge = delta_badge(cur_total, pri_total, inverted=False)

    content = f"""
<div class="stat-footnote" style="text-align:right;margin-bottom:0.5rem">
  Total releases &nbsp;·&nbsp;
  <strong style="color:{COLORS["blue"]}">{cur_total}</strong> {window_start[:4]}
  &nbsp;vs&nbsp;
  <strong style="color:rgba(88,166,255,0.6)">{pri_total}</strong> {prior_start[:4]}
  {total_badge}
</div>
<div class="chart-container" style="height:65vh;">
  <canvas id="chart-q11"></canvas>
</div>
<script>
(function(){{
  new Chart(document.getElementById('chart-q11'), {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [
        {{
          label: 'Stable {window_start[:4]}',
          data: {cur_stable},
          backgroundColor: 'rgba(63,185,80,0.8)',
          stack: 'current',
          borderRadius: 3,
        }},
        {{
          label: 'Pre-release {window_start[:4]}',
          data: {cur_pre},
          backgroundColor: 'rgba(88,166,255,0.7)',
          stack: 'current',
          borderRadius: 3,
        }},
        {{
          label: 'Stable {prior_start[:4]}',
          data: {pri_stable},
          backgroundColor: 'rgba(63,185,80,0.25)',
          stack: 'prior',
          borderRadius: 3,
        }},
        {{
          label: 'Pre-release {prior_start[:4]}',
          data: {pri_pre},
          backgroundColor: 'rgba(88,166,255,0.2)',
          stack: 'prior',
          borderRadius: 3,
        }},
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '{COLORS["text"]}', font: {{ size: 13 }}, boxWidth: 20 }} }},
      }},
      scales: {{
        x: {{ ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 11 }}, maxRotation: 45 }}, grid: {{ color: 'rgba(255,255,255,0.07)' }} }},
        y: {{
          stacked: true,
          ticks: {{ color: '{COLORS["muted"]}', font: {{ size: 12 }} }},
          grid: {{ color: 'rgba(255,255,255,0.07)' }},
          title: {{ display: true, text: 'Releases', color: '{COLORS["muted"]}', font: {{ size: 12 }} }},
        }},
      }}
    }}
  }});
}})();
</script>
"""
    return slide_wrapper(11, "Releases per Month", "Stable vs pre-release · current vs prior year", content)


def generate_narrative(report):
    """Build a list of (heading, body) narrative points from report data."""
    ws  = report.get("window_start", "")[:7]   # YYYY-MM
    we  = report.get("window_end",   "")[:7]
    ps  = report.get("prior_start",  "")[:7]
    pe  = report.get("prior_end",    "")[:7]
    wy  = report.get("window_start", "")[:4]   # current year label
    py  = report.get("prior_start",  "")[:4]   # prior year label

    q4  = report.get("q4_prs_by_month", [])
    q5  = report.get("q5_contributors", {})
    q6  = report.get("q6_author_kind", {})
    q7t = report.get("q7_tenure", {})
    q7r = report.get("q7_retention", {})
    q9  = report.get("q9_first_response", {})
    q10 = report.get("q10_merge_wait", {})
    q11 = report.get("q11_releases", {})

    cur_rows = q4
    cur5     = q5.get("current", [])
    pri5     = q5.get("prior",   [])

    # Total PRs
    cur_opened = sum(r["opened"] for r in cur_rows)
    pri_opened = sum(r["opened_prior"] for r in cur_rows)
    pr_pct     = round((cur_opened - pri_opened) / pri_opened * 100) if pri_opened else 0

    # New contributors
    cur_new_total = sum(r["new"] for r in cur5)
    pri_new_total = sum(r["new"] for r in pri5)
    contrib_pct   = round((cur_new_total - pri_new_total) / pri_new_total * 100) if pri_new_total else 0

    # Peak months by PRs opened
    peak_month = max(cur_rows, key=lambda r: r["opened"])["month"] if cur_rows else "N/A"
    peak_new_month = max(cur5, key=lambda r: r["new"])["month"] if cur5 else "N/A"

    # GSoC window: Dec–May surge
    surge_months = [r for r in cur_rows if r["month"] >= "2025-12"]
    surge_opened = sum(r["opened"] for r in surge_months)
    baseline_months = [r for r in cur_rows if r["month"] < "2025-12"]
    baseline_avg = round(sum(r["opened"] for r in baseline_months) / len(baseline_months)) if baseline_months else 0

    # New contributors Dec–Mar
    gsoc_new = sum(r["new"] for r in cur5 if "2025-12" <= r["month"] <= "2026-03")

    # Author kind
    ftc_cur = q6.get("current", {}).get("First Time Contributor", 0)
    ftc_pri = q6.get("prior",   {}).get("First Time Contributor", 0)
    bot_cur = q6.get("current", {}).get("Bot", 0)

    # Retention
    ret_pct     = q7r.get("retention_pct", 0)
    returning   = q7r.get("returning_contributors", 0)
    prior_total = q7r.get("prior_contributors", 0)

    # Response & merge
    resp_cur = q9.get("current", {}).get("avg_hours", 0)
    resp_pri = q9.get("prior",   {}).get("avg_hours", 0)
    resp_delta = round((resp_cur - resp_pri) / resp_pri * 100) if resp_pri else 0

    merge_cur = q10.get("current", {}).get("avg_hours", 0)
    merge_pri = q10.get("prior",   {}).get("avg_hours", 0)
    merge_delta = round((merge_cur - merge_pri) / merge_pri * 100) if merge_pri else 0

    # Releases
    rel_cur = sum(r["total"] for r in q11.get("current", []))
    rel_pri = sum(r["total"] for r in q11.get("prior",   []))

    def hrs(h):
        if h >= 24:
            return f"{h/24:.1f}d"
        return f"{h:.0f}h"

    sign = lambda x: ("+" if x >= 0 else "") + str(x) + "%"

    points = [
        (
            f"Activity nearly tripled year-over-year",
            f"{cur_opened:,} PRs were opened in {ws}–{we}, compared to {pri_opened:,} in the prior year "
            f"({sign(pr_pct)} YoY). The baseline rate before December 2025 was ~{baseline_avg} PRs/month; "
            f"the six months from December 2025 through May 2026 accounted for {surge_opened:,} of those — "
            f"a pattern directly tied to the GSoC {GSOC['year']} cycle."
        ),
        (
            f"The GSoC application window drove a wave of new contributors",
            f"GSoC {GSOC['year']} contributor applications opened {GSOC['app_open']} and closed {GSOC['app_close']}. "
            f"In the four months from December 2025 to March 2026 — when prospective GSoC contributors "
            f"typically submit test pull requests to demonstrate capability — {gsoc_new} first-time contributors "
            f"appeared, with the single largest intake in {peak_new_month} ({max((r['new'] for r in cur5 if r['month']==peak_new_month), default=0)} new contributors). "
            f"The prior year showed the same pattern: a spike in March 2025 of "
            f"{max((r['new'] for r in pri5 if r['month']=='2025-03'), default=0)} new contributors, "
            f"aligning with the GSoC 2025 application period."
        ),
        (
            f"Low retention ({ret_pct}%) is consistent with a program contributor cohort",
            f"Only {returning} of {prior_total} contributors from the prior year returned in the current window "
            f"({ret_pct}% retention). This is expected for an open source project whose contributor base is "
            f"substantially renewed each year through GSoC: most participants contribute intensively during "
            f"the program period then move on. The {q7r.get('current_new_contributors', 0)} new contributors "
            f"this year represent fresh intake rather than organic growth from the existing community."
        ),
        (
            f"Maintainers are absorbing a heavier review load — but response times improved",
            f"Average first-response wait fell from {hrs(resp_pri)} to {hrs(resp_cur)} ({sign(resp_delta)} YoY), "
            f"and average merge wait from {hrs(merge_pri)} to {hrs(merge_cur)} ({sign(merge_delta)} YoY), "
            f"despite the PR volume tripling. This reflects the maintainer team scaling review effort alongside "
            f"the influx. The bot share of PRs rose from {q6.get('prior',{}).get('Bot',0)}% to {bot_cur}%, "
            f"which also reduces the manual triage burden."
        ),
        (
            f"Coding activity spikes in May 2026 as GSoC coding period begins",
            f"GSoC {GSOC['year']} coding officially started {GSOC['coding_start']}. May 2026 already shows "
            f"the largest single-month code volume in the window, with additions and deletions both at multi-million "
            f"line scale — consistent with contributors landing substantial feature work in the opening weeks of "
            f"the coding period. Release cadence remained steady at {rel_cur} releases "
            f"(vs {rel_pri} prior year), indicating the core team maintained shipping discipline throughout."
        ),
    ]

    return points


def make_slide_narrative(report):
    points = generate_narrative(report)
    wy = report.get("window_start", "")[:4]
    py = report.get("prior_start",  "")[:4]

    items_html = ""
    for heading, body in points:
        items_html += f"""
  <div class="narrative-item">
    <div class="narrative-heading">{heading}</div>
    <div class="narrative-body">{body}</div>
  </div>"""

    content = f"""
<div class="narrative-grid">{items_html}
</div>
<div class="stat-footnote" style="margin-top:1rem">
  Context: <a href="https://developers.google.com/open-source/gsoc/timeline" style="color:{COLORS['blue']}">
  GSoC {GSOC['year']} timeline</a> · applications {GSOC['app_open']} – {GSOC['app_close']} ·
  coding from {GSOC['coding_start']}
</div>
"""
    return slide_wrapper("∑", "Key Findings", f"{wy} vs {py} · contextualised against GSoC {GSOC['year']}", content)


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  width: 100%; height: 100%;
  background: #0d1117;
  color: #e6edf3;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
}
.slide {
  position: absolute;
  inset: 0;
  display: none;
  flex-direction: column;
}
.slide.active { display: flex; }
.slide-inner {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 3.5vh 8vw 7vh;
  overflow: hidden;
}
.slide-header {
  margin-bottom: 2.5vh;
  flex-shrink: 0;
}
.slide-title {
  font-size: 3rem;
  font-weight: 700;
  color: #e6edf3;
  line-height: 1.15;
}
.slide-subtitle {
  font-size: 1.3rem;
  color: #8b949e;
  margin-top: 0.4rem;
}
.slide-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chart-container {
  position: relative;
  width: 100%;
}
/* Title slide */
.title-slide-body { display: flex; flex-direction: column; gap: 2vh; }
.title-date { font-size: 1.4rem; color: #8b949e; }
.agenda-list {
  list-style: none;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem 3rem;
  margin-top: 0.5rem;
}
.agenda-list li {
  font-size: 1.15rem;
  color: #c9d1d9;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.agenda-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem; height: 1.7rem;
  border-radius: 50%;
  background: #161b22;
  border: 1px solid #30363d;
  color: #58a6ff;
  font-weight: 700;
  font-size: 0.9rem;
  flex-shrink: 0;
}
/* Stat cards */
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  flex: 1;
  align-items: center;
  padding: 1rem 0;
}
.stat-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 2.5rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  align-items: flex-start;
}
.stat-label {
  font-size: 1.1rem;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.stat-value {
  font-size: 4.5rem;
  font-weight: 700;
  color: #e6edf3;
  line-height: 1;
  display: flex;
  align-items: baseline;
  gap: 0;
}
.stat-unit {
  font-size: 2rem;
  font-weight: 400;
  color: #8b949e;
  margin-left: 0.2rem;
}
.stat-compare {
  font-size: 1rem;
  color: #8b949e;
}
.stat-footnote {
  font-size: 0.95rem;
  color: #8b949e;
  margin-top: 1rem;
  flex-shrink: 0;
}
.narrative-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 2rem;
  flex: 1;
  overflow-y: auto;
  align-content: start;
}
.narrative-item {
  background: #161b22;
  border-left: 3px solid #58a6ff;
  border-radius: 0 6px 6px 0;
  padding: 0.75rem 1rem;
}
.narrative-heading {
  font-size: 1.05rem;
  font-weight: 600;
  color: #e6edf3;
  margin-bottom: 0.4rem;
}
.narrative-body {
  font-size: 0.92rem;
  color: #8b949e;
  line-height: 1.55;
}
.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  font-size: 2rem;
  color: #8b949e;
  border: 2px dashed #30363d;
  border-radius: 12px;
  margin: 2rem 0;
}
/* HUD */
#hud-watermark {
  position: fixed;
  top: 1rem;
  right: 1.5rem;
  font-size: 0.85rem;
  color: #8b949e;
  pointer-events: none;
  z-index: 100;
}
#hud-counter {
  position: fixed;
  bottom: 1.6rem;
  right: 1.5rem;
  font-size: 1rem;
  color: #8b949e;
  pointer-events: none;
  z-index: 100;
}
#hud-progress {
  position: fixed;
  bottom: 0;
  left: 0;
  height: 3px;
  background: #58a6ff;
  transition: width 0.3s ease;
  z-index: 100;
}
/* Click zones */
#zone-back {
  position: fixed;
  top: 0; left: 0;
  width: 33.3%;
  height: 100%;
  z-index: 50;
  cursor: w-resize;
}
#zone-fwd {
  position: fixed;
  top: 0; right: 0;
  width: 33.3%;
  height: 100%;
  z-index: 50;
  cursor: e-resize;
}
"""

NAV_JS = """
const slides = document.querySelectorAll('.slide');
const TOTAL = slides.length;
let cur = 0;

function goTo(n) {
  if (n < 0 || n >= TOTAL) return;
  slides[cur].classList.remove('active');
  cur = n;
  slides[cur].classList.add('active');
  document.getElementById('hud-counter').textContent = (cur + 1) + ' / ' + TOTAL;
  document.getElementById('hud-progress').style.width = ((cur + 1) / TOTAL * 100) + '%';
}

goTo(0);

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); goTo(cur + 1); }
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); goTo(cur - 1); }
  else if (e.key === 'Home') goTo(0);
  else if (e.key === 'End') goTo(TOTAL - 1);
  else if (e.key === 'f' || e.key === 'F') {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  } else if (e.key === 'Escape') {
    if (document.fullscreenElement) document.exitFullscreen();
  } else if (e.key >= '1' && e.key <= '9') goTo(parseInt(e.key));
  else if (e.key === '0') goTo(10);
});

document.getElementById('zone-back').addEventListener('click', () => goTo(cur - 1));
document.getElementById('zone-fwd').addEventListener('click', () => goTo(cur + 1));
"""


def build_html(report, chartjs_inline):
    window_end = report.get("window_end", "")
    generated_at = report.get("generated_at", datetime.now(timezone.utc).isoformat())

    if chartjs_inline:
        chartjs_tag = f"<script>{chartjs_inline}</script>"
    else:
        chartjs_tag = f'<script src="{CHART_JS_CDN}"></script>'

    slides_html = "".join([
        make_slide_0(report),
        make_slide_1(report),
        make_slide_2(report),
        make_slide_3(report),
        make_slide_4(report),
        make_slide_5(report),
        make_slide_6(report),
        make_slide_7(report),
        make_slide_8(report),
        make_slide_9(report),
        make_slide_10(report),
        make_slide_11(report),
        make_slide_narrative(report),
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Accord Project · GitHub Statistics · {window_end}</title>
<style>
{CSS}
</style>
{chartjs_tag}
</head>
<body>

<!-- HUD elements -->
<div id="hud-watermark">Accord Project &middot; {window_end}</div>
<div id="hud-counter">1 / 11</div>
<div id="hud-progress" style="width:0%"></div>

<!-- Click zones -->
<div id="zone-back"></div>
<div id="zone-fwd"></div>

<!-- Slides -->
{slides_html}

<script>
{NAV_JS}
</script>
<!-- Generated: {generated_at} -->
</body>
</html>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--open", action="store_true", help="Open in default browser after generation")
    p.add_argument("--report", default=None, help="Path to report.json (default: output/report.json relative to script)")
    args = p.parse_args()

    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "output"

    if args.report:
        report_path = Path(args.report)
    else:
        report_path = output_dir / "report.json"

    output_path = output_dir / "presentation.html"

    if not report_path.exists():
        print(f"ERROR: report.json not found at {report_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {report_path} ...")
    with open(report_path) as f:
        report = json.load(f)

    print("Downloading Chart.js ...")
    chartjs_inline = fetch_chartjs()

    print("Building HTML ...")
    output_dir.mkdir(parents=True, exist_ok=True)
    html = build_html(report, chartjs_inline)

    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"Written: {output_path} ({size_kb:.1f} KB)")

    if args.open:
        import platform
        if platform.system() == "Darwin":
            subprocess.run(["open", str(output_path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(output_path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(output_path)])


if __name__ == "__main__":
    main()
