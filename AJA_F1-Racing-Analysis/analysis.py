"""
Runs the queries in queries.sql against f1.db, prints a findings summary
to the console, and saves 6 charts to charts/.

Run: python3 analysis.py   (after load_data.py has built f1.db)
"""

import os
import re
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "f1.db")
QUERIES_PATH = os.path.join(BASE_DIR, "queries.sql")
CHARTS_DIR = os.path.join(BASE_DIR, "charts")

try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    pass
plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.edgecolor": "#444444",
})

F1_RED = "#e10600"
NEUTRAL_COLOR = "#3a6ea5"
GOLD = "#c9a227"


def load_queries():
    text = open(QUERIES_PATH, encoding="utf-8").read()
    marker = re.compile(r"^-- QUERY:\s*(\w+)\s*$", re.MULTILINE)
    matches = list(marker.finditer(text))
    queries = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        queries[m.group(1)] = text[start:end].strip()
    return queries


def run_all(conn, queries):
    return {key: pd.read_sql(sql, conn) for key, sql in queries.items()}


def chart_constructor_dominance(results):
    df = results["constructor_dominance_by_decade"]
    leaders = df[df["rank_in_decade"] == 1].sort_values("decade")

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(leaders["decade"].astype(str), leaders["pct_share"], color=F1_RED, width=0.6)
    for bar, name in zip(bars, leaders["constructor_name"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, name,
                 ha="center", fontsize=9, rotation=0)
    ax.set_title("Leading Constructor's Points Share by Decade")
    ax.set_ylabel("Share of that decade's total points (%)")
    ax.set_xlabel("Decade (2020s = 2020-2024 only, not a full decade)")
    ax.set_ylim(0, leaders["pct_share"].max() * 1.2)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "01_constructor_dominance_by_decade.png"))
    plt.close(fig)


def chart_grid_vs_finish(results):
    df = results["grid_vs_finish_correlation"].sort_values("era")
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(df["era"], df["grid_finish_correlation"], color=[NEUTRAL_COLOR, F1_RED])
    ax.bar_label(bars, padding=4, fmt="%.3f")
    ax.set_title("Grid Position -> Finish Position Correlation")
    ax.set_ylabel("Pearson correlation (grid vs. classified finish)")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "02_grid_vs_finish_correlation.png"))
    plt.close(fig)


def chart_driver_consistency(results):
    df = results["driver_consistency_by_season"]
    reliable = df[df["dnf_pct"] <= 15]
    unreliable = df[df["dnf_pct"] > 15]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(unreliable["avg_finish"], unreliable["finish_stdev"], color="#aaaaaa", alpha=0.4,
               s=25, label="DNF rate > 15% that season")
    ax.scatter(reliable["avg_finish"], reliable["finish_stdev"], color=F1_RED, alpha=0.75,
               s=30, label="DNF rate <= 15% that season")

    # Label a handful of the most consistent *reliable* seasons for context.
    # These cluster tightly together, so stagger the label offsets rather
    # than using one fixed offset, or they overlap into an unreadable mess.
    top_reliable = reliable.sort_values("finish_stdev").head(6)
    offsets = [(8, 6), (8, -14), (-70, 10), (-70, -16), (8, 20), (-70, -30)]
    for (_, row), offset in zip(top_reliable.iterrows(), offsets):
        ax.annotate(f"{row['driver_name'].split()[-1]} '{str(row['year'])[2:]}",
                     (row["avg_finish"], row["finish_stdev"]),
                     textcoords="offset points", xytext=offset, fontsize=8,
                     arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6))

    ax.set_title("Driver-Season Consistency: Average Finish vs. Finish-Position Spread")
    ax.set_xlabel("Average finish position that season (classified races only, lower = better)")
    ax.set_ylabel("Standard deviation of finish position\n(lower = more consistent)")
    ax.invert_xaxis()
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "03_driver_consistency.png"))
    plt.close(fig)


def chart_home_advantage(results):
    df = results["home_advantage_by_nationality"].sort_values("avg_positions_gained_at_home")
    colors = [F1_RED if v > 0 else NEUTRAL_COLOR for v in df["avg_positions_gained_at_home"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(df["nationality"], df["avg_positions_gained_at_home"], color=colors)
    ax.axvline(0, color="#444444", linewidth=0.8)
    ax.set_title("Home-Race Effect by Nationality\n(positions gained vs. that driver's own season average)")
    ax.set_xlabel("Average finish-position places gained at home race\n(negative = did worse at home)")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "04_home_advantage_by_nationality.png"))
    plt.close(fig)


def chart_pit_stop_trend(results):
    all_circuits = results["pit_stop_trend_by_year"]
    monza = results["pit_stop_trend_same_circuit"]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(all_circuits["year"], all_circuits["avg_pit_stop_seconds"], marker="o",
            color=NEUTRAL_COLOR, linewidth=2, label="All circuits, that season")
    ax.plot(monza["year"], monza["avg_pit_stop_seconds"], marker="s",
            color=F1_RED, linewidth=2, label="Monza only (same circuit every year, controls for pit lane length)")
    ax.set_title("Average Pit Stop Duration, 2011-2024\n(total pit-lane time: entry to exit, not stationary time)")
    ax.set_xlabel("Season")
    ax.set_ylabel("Average pit stop duration (seconds)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "05_pit_stop_trend.png"))
    plt.close(fig)


def chart_dnf_by_decade(results):
    df = results["dnf_rate_by_decade"].sort_values("decade")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df["decade"].astype(str), df["dnf_pct"], color=F1_RED)
    ax.bar_label(bars, padding=4, fmt="%.1f%%")
    ax.set_title("DNF Rate by Decade\n(2020s = 2020-2024 only, not a full decade)")
    ax.set_ylabel("Share of race starts that did not classify (%)")
    ax.set_xlabel("Decade")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "06_dnf_rate_by_decade.png"))
    plt.close(fig)


def print_summary(results):
    print("\n=== KEY FIGURES (for REPORT.md) ===\n")

    dom = results["constructor_dominance_by_decade"]
    print("Leading constructor by decade:")
    for _, row in dom[dom["rank_in_decade"] == 1].sort_values("decade").iterrows():
        print(f"  {int(row['decade'])}s: {row['constructor_name']} ({row['pct_share']}% of decade points)")

    corr = results["grid_vs_finish_correlation"]
    print("\nGrid -> finish correlation:")
    print(corr.to_string(index=False))

    dc = results["driver_consistency_by_season"]
    most_consistent_reliable = dc[dc["dnf_pct"] <= 15].sort_values("finish_stdev").iloc[0]
    most_volatile = dc.sort_values("finish_stdev", ascending=False).iloc[0]
    print(f"\nMost consistent season (DNF rate <=15%): {most_consistent_reliable['driver_name']} "
          f"{int(most_consistent_reliable['year'])} (stdev {most_consistent_reliable['finish_stdev']}, "
          f"avg finish {most_consistent_reliable['avg_finish']})")
    print(f"Most boom-or-bust season: {most_volatile['driver_name']} {int(most_volatile['year'])} "
          f"(stdev {most_volatile['finish_stdev']}, {most_volatile['dnf_pct']}% DNF rate)")

    ho = results["home_advantage_overall"].iloc[0]
    print(f"\nHome-race effect, all drivers pooled: {ho['avg_positions_gained_at_home']} positions gained "
          f"on average ({ho['home_race_instances']} home-race instances)")
    hn = results["home_advantage_by_nationality"].sort_values("avg_positions_gained_at_home", ascending=False)
    print(f"Strongest home effect: {hn.iloc[0]['nationality']} ({hn.iloc[0]['avg_positions_gained_at_home']} positions, "
          f"{hn.iloc[0]['home_race_instances']} instances)")

    ps_year = results["pit_stop_trend_by_year"]
    ps_monza = results["pit_stop_trend_same_circuit"]
    print(f"\nPit stop duration (all circuits): {ps_year.iloc[0]['avg_pit_stop_seconds']}s in "
          f"{int(ps_year.iloc[0]['year'])} -> {ps_year.iloc[-1]['avg_pit_stop_seconds']}s in {int(ps_year.iloc[-1]['year'])}")
    print(f"Pit stop duration (Monza only, same circuit): {ps_monza.iloc[0]['avg_pit_stop_seconds']}s in "
          f"{int(ps_monza.iloc[0]['year'])} -> {ps_monza.iloc[-1]['avg_pit_stop_seconds']}s in {int(ps_monza.iloc[-1]['year'])}")

    psc = results["pit_stop_by_constructor_recent"].sort_values("avg_pit_stop_seconds")
    print(f"Fastest pit crew (last 3 seasons): {psc.iloc[0]['constructor_name']} ({psc.iloc[0]['avg_pit_stop_seconds']}s avg)")

    dc_circuit = results["dnf_rate_by_circuit"].sort_values("dnf_pct", ascending=False)
    print(f"\nHighest-DNF circuit (>=200 starts): {dc_circuit.iloc[0]['circuit_name']}, "
          f"{dc_circuit.iloc[0]['country']} ({dc_circuit.iloc[0]['dnf_pct']}%)")

    dd = results["dnf_rate_by_decade"].sort_values("decade")
    print(f"DNF rate by decade: {dd.iloc[0]['dnf_pct']}% ({int(dd.iloc[0]['decade'])}s) -> "
          f"{dd.iloc[-1]['dnf_pct']}% ({int(dd.iloc[-1]['decade'])}s)")

    bc = results["best_season_nobody_remembers_constructors"].sort_values("points_behind")
    print(f"\nClosest title miss, constructor never champion: {bc.iloc[0]['constructor_name']} "
          f"{int(bc.iloc[0]['year'])}, {bc.iloc[0]['points_behind']} points behind")
    bd = results["best_season_nobody_remembers_drivers"].sort_values("points_behind")
    print("Closest title misses, driver never champion (top 5):")
    print(bd.head(5).to_string(index=False))
    print()


def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)
    queries = load_queries()
    conn = sqlite3.connect(DB_PATH)
    try:
        results = run_all(conn, queries)
    finally:
        conn.close()

    chart_constructor_dominance(results)
    chart_grid_vs_finish(results)
    chart_driver_consistency(results)
    chart_home_advantage(results)
    chart_pit_stop_trend(results)
    chart_dnf_by_decade(results)
    print(f"Saved 6 charts to {CHARTS_DIR}")

    print_summary(results)


if __name__ == "__main__":
    main()
