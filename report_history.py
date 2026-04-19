#!/usr/bin/env python3

import json
import os
import sys
from collections import defaultdict

import yaml

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def load_config(path=None):
    if path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "config.yml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_history_entries(path):
    history_path = os.path.expanduser(path)
    if not os.path.exists(history_path):
        return []

    entries = []
    with open(history_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def safe_pct(numerator, denominator):
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


def summarize_entries(entries):
    summary = {
        "total_commits": len(entries),
        "selection_by_provider": defaultdict(int),
        "displayed_by_provider": defaultdict(int),
        "judge_usage": defaultdict(int),
        "refiner_usage": defaultdict(int),
        "generator_usage": defaultdict(int),
        "avg_selected_elapsed": defaultdict(list),
        "avg_displayed_elapsed": defaultdict(list),
        "selected_indexes": defaultdict(int),
    }

    for entry in entries:
        selected_candidate = entry.get("selected_candidate") or {}
        selected_provider = selected_candidate.get("provider")
        selected_elapsed = selected_candidate.get("elapsed")

        if selected_provider:
            summary["selection_by_provider"][selected_provider] += 1
            if isinstance(selected_elapsed, (int, float)):
                summary["avg_selected_elapsed"][selected_provider].append(
                    selected_elapsed
                )

        selected_index = entry.get("selected_index")
        if selected_index is not None:
            summary["selected_indexes"][str(selected_index)] += 1

        plan = entry.get("plan") or {}
        for provider in plan.get("generators") or []:
            summary["generator_usage"][provider] += 1

        judge = plan.get("judge")
        if judge:
            summary["judge_usage"][judge] += 1

        refiner = plan.get("refiner")
        if refiner:
            summary["refiner_usage"][refiner] += 1

        for displayed in entry.get("displayed_messages") or []:
            provider = displayed.get("provider")
            elapsed = displayed.get("elapsed")
            if not provider:
                continue
            summary["displayed_by_provider"][provider] += 1
            if isinstance(elapsed, (int, float)):
                summary["avg_displayed_elapsed"][provider].append(elapsed)

    return summary


def compute_provider_rows(summary):
    providers = sorted({
        *summary["selection_by_provider"].keys(),
        *summary["displayed_by_provider"].keys(),
        *summary["judge_usage"].keys(),
        *summary["refiner_usage"].keys(),
        *summary["generator_usage"].keys(),
    })

    rows = []
    total_commits = summary["total_commits"]
    total_displayed = sum(summary["displayed_by_provider"].values())

    for provider in providers:
        selected = summary["selection_by_provider"].get(provider, 0)
        displayed = summary["displayed_by_provider"].get(provider, 0)
        acceptance_vs_commits = safe_pct(selected, total_commits)
        acceptance_vs_shown = safe_pct(selected, displayed)
        avg_selected = _avg(summary["avg_selected_elapsed"].get(provider, []))
        avg_displayed = _avg(summary["avg_displayed_elapsed"].get(provider, []))

        rows.append({
            "provider": provider,
            "selected": selected,
            "displayed": displayed,
            "acceptance_vs_commits": acceptance_vs_commits,
            "acceptance_vs_shown": acceptance_vs_shown,
            "avg_selected": avg_selected,
            "avg_displayed": avg_displayed,
            "generator_usage": summary["generator_usage"].get(provider, 0),
            "judge_usage": summary["judge_usage"].get(provider, 0),
            "refiner_usage": summary["refiner_usage"].get(provider, 0),
            "display_share": safe_pct(displayed, total_displayed),
        })

    rows.sort(
        key=lambda row: (
            -row["acceptance_vs_shown"],
            -row["selected"],
            row["avg_selected"] if row["avg_selected"] is not None else 999999,
        )
    )
    return rows


def _avg(values):
    if not values:
        return None
    return sum(values) / len(values)


def format_seconds(value):
    if value is None:
        return "-"
    return f"{value:.2f}s"


def format_pct(value):
    return f"{value:.1f}%"


def get_acceptance_style(value):
    if value >= 60:
        return "green"
    if value >= 30:
        return "yellow"
    return "red"


def render_summary(entries, summary, provider_rows):
    if HAS_RICH:
        _render_rich_summary(entries, summary, provider_rows)
        return
    _render_plain_summary(entries, summary, provider_rows)


def _render_rich_summary(entries, summary, provider_rows):
    console = Console()
    total_commits = summary["total_commits"]
    top_provider = provider_rows[0]["provider"] if provider_rows else "N/A"
    top_rate = provider_rows[0]["acceptance_vs_shown"] if provider_rows else 0.0

    overview = Text()
    overview.append("Commits analyzed: ", style="bold")
    overview.append(str(total_commits), style="cyan")
    overview.append("\nTop accepted provider: ", style="bold")
    overview.append(top_provider, style="magenta")
    overview.append(" (")
    overview.append(format_pct(top_rate), style=get_acceptance_style(top_rate))
    overview.append(" of shown candidates)")
    console.print(Panel(overview, title="History Overview", expand=False))

    provider_table = Table(title="Acceptance Relative And Average Time", header_style="bold cyan")
    provider_table.add_column("Provider", style="bold")
    provider_table.add_column("Selected", justify="right")
    provider_table.add_column("Shown", justify="right")
    provider_table.add_column("Accept/Shown", justify="right")
    provider_table.add_column("Accept/Commits", justify="right")
    provider_table.add_column("Avg Selected", justify="right")
    provider_table.add_column("Avg Shown", justify="right")
    provider_table.add_column("Gen", justify="right")
    provider_table.add_column("Judge", justify="right")
    provider_table.add_column("Refine", justify="right")

    for row in provider_rows:
        provider_table.add_row(
            row["provider"],
            str(row["selected"]),
            str(row["displayed"]),
            f"[{get_acceptance_style(row['acceptance_vs_shown'])}]"
            f"{format_pct(row['acceptance_vs_shown'])}[/{get_acceptance_style(row['acceptance_vs_shown'])}]",
            format_pct(row["acceptance_vs_commits"]),
            format_seconds(row["avg_selected"]),
            format_seconds(row["avg_displayed"]),
            str(row["generator_usage"]),
            str(row["judge_usage"]),
            str(row["refiner_usage"]),
        )
    console.print(provider_table)

    idx_table = Table(title="Selection Position", header_style="bold magenta")
    idx_table.add_column("Choice")
    idx_table.add_column("Count", justify="right")
    idx_table.add_column("Rate", justify="right")
    for choice, count in sorted(summary["selected_indexes"].items(), key=lambda item: int(item[0])):
        idx_table.add_row(choice, str(count), format_pct(safe_pct(count, total_commits)))
    console.print(idx_table)


def _render_plain_summary(entries, summary, provider_rows):
    print("History Overview")
    print("================")
    print(f"Commits analyzed: {summary['total_commits']}")
    if provider_rows:
        print(
            f"Top accepted provider: {provider_rows[0]['provider']} "
            f"({format_pct(provider_rows[0]['acceptance_vs_shown'])} of shown candidates)"
        )
    print()
    print("Acceptance Relative And Average Time")
    print("Provider | Selected | Shown | Accept/Shown | Accept/Commits | Avg Selected | Avg Shown | Gen | Judge | Refine")
    for row in provider_rows:
        print(
            f"{row['provider']} | {row['selected']} | {row['displayed']} | "
            f"{format_pct(row['acceptance_vs_shown'])} | "
            f"{format_pct(row['acceptance_vs_commits'])} | "
            f"{format_seconds(row['avg_selected'])} | "
            f"{format_seconds(row['avg_displayed'])} | "
            f"{row['generator_usage']} | {row['judge_usage']} | {row['refiner_usage']}"
        )


def main():
    config = load_config()
    history_path = config.get("history_json_path", "~/.gcm_history.jsonl")
    entries = load_history_entries(history_path)

    if not entries:
        print(f"No structured history found at {os.path.expanduser(history_path)}")
        return 1

    summary = summarize_entries(entries)
    provider_rows = compute_provider_rows(summary)
    render_summary(entries, summary, provider_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
