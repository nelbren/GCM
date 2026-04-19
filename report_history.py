#!/usr/bin/env python3

import json
import os
import shutil
import sys
from collections import defaultdict

import yaml

RICH_IMPORT_ERROR = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError as exc:
    HAS_RICH = False
    RICH_IMPORT_ERROR = exc


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


def get_project_name(entry):
    project = entry.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if name:
            return str(name)
        path = project.get("path")
        if path:
            return os.path.basename(path) or str(path)
    if isinstance(project, str) and project:
        return project
    return "(unknown)"


def summarize_entries(entries):
    summary = {
        "total_runs": len(entries),
        "total_commits": 0,
        "total_canceled": 0,
        "projects": set(),
        "selection_by_project_provider": defaultdict(int),
        "displayed_by_project_provider": defaultdict(int),
        "canceled_displayed_by_project_provider": defaultdict(int),
        "judge_usage_by_project_provider": defaultdict(int),
        "refiner_usage_by_project_provider": defaultdict(int),
        "generator_usage_by_project_provider": defaultdict(int),
        "avg_selected_elapsed_by_project_provider": defaultdict(list),
        "avg_displayed_elapsed_by_project_provider": defaultdict(list),
        "selected_indexes": defaultdict(int),
    }

    for entry in entries:
        project_name = get_project_name(entry)
        summary["projects"].add(project_name)
        outcome = entry.get("outcome", "committed")
        is_committed = outcome != "canceled"

        if is_committed:
            summary["total_commits"] += 1
        else:
            summary["total_canceled"] += 1

        selected_candidate = entry.get("selected_candidate") or {}
        selected_provider = selected_candidate.get("provider")
        selected_elapsed = selected_candidate.get("elapsed")

        if is_committed and selected_provider:
            key = (project_name, selected_provider)
            summary["selection_by_project_provider"][key] += 1
            if isinstance(selected_elapsed, (int, float)):
                summary["avg_selected_elapsed_by_project_provider"][key].append(
                    selected_elapsed
                )

        selected_index = entry.get("selected_index")
        if selected_index is not None:
            summary["selected_indexes"][str(selected_index)] += 1

        plan = entry.get("plan") or {}
        for provider in plan.get("generators") or []:
            summary["generator_usage_by_project_provider"][(project_name, provider)] += 1

        judge = plan.get("judge")
        if judge:
            summary["judge_usage_by_project_provider"][(project_name, judge)] += 1

        refiner = plan.get("refiner")
        if refiner:
            summary["refiner_usage_by_project_provider"][(project_name, refiner)] += 1

        for displayed in entry.get("displayed_messages") or []:
            provider = displayed.get("provider")
            elapsed = displayed.get("elapsed")
            if not provider:
                continue
            key = (project_name, provider)
            summary["displayed_by_project_provider"][key] += 1
            if not is_committed:
                summary["canceled_displayed_by_project_provider"][key] += 1
            if isinstance(elapsed, (int, float)):
                summary["avg_displayed_elapsed_by_project_provider"][key].append(elapsed)

    return summary


def compute_provider_rows(summary):
    project_providers = sorted({
        *summary["selection_by_project_provider"].keys(),
        *summary["displayed_by_project_provider"].keys(),
        *summary["judge_usage_by_project_provider"].keys(),
        *summary["refiner_usage_by_project_provider"].keys(),
        *summary["generator_usage_by_project_provider"].keys(),
    })

    rows = []
    total_commits = summary["total_commits"]
    total_displayed = sum(summary["displayed_by_project_provider"].values())

    for project_name, provider in project_providers:
        key = (project_name, provider)
        selected = summary["selection_by_project_provider"].get(key, 0)
        displayed = summary["displayed_by_project_provider"].get(key, 0)
        canceled_shown = summary["canceled_displayed_by_project_provider"].get(key, 0)
        acceptance_vs_commits = safe_pct(selected, total_commits)
        acceptance_vs_shown = safe_pct(selected, displayed)
        cancel_vs_shown = safe_pct(canceled_shown, displayed)
        avg_selected = _avg(summary["avg_selected_elapsed_by_project_provider"].get(key, []))
        avg_displayed = _avg(summary["avg_displayed_elapsed_by_project_provider"].get(key, []))

        rows.append({
            "project": project_name,
            "provider": provider,
            "selected": selected,
            "displayed": displayed,
            "canceled_shown": canceled_shown,
            "acceptance_vs_commits": acceptance_vs_commits,
            "acceptance_vs_shown": acceptance_vs_shown,
            "cancel_vs_shown": cancel_vs_shown,
            "avg_selected": avg_selected,
            "avg_displayed": avg_displayed,
            "generator_usage": summary["generator_usage_by_project_provider"].get(key, 0),
            "judge_usage": summary["judge_usage_by_project_provider"].get(key, 0),
            "refiner_usage": summary["refiner_usage_by_project_provider"].get(key, 0),
            "display_share": safe_pct(displayed, total_displayed),
        })

    rows.sort(
        key=lambda row: (
            -row["acceptance_vs_shown"],
            -row["selected"],
            row["project"].lower(),
            row["provider"].lower(),
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
    total_runs = summary["total_runs"]
    total_commits = summary["total_commits"]
    total_canceled = summary["total_canceled"]
    total_projects = len(summary["projects"])
    top_label = (
        f"{provider_rows[0]['project']} / {provider_rows[0]['provider']}"
        if provider_rows else "N/A"
    )
    top_rate = provider_rows[0]["acceptance_vs_shown"] if provider_rows else 0.0

    overview = Text()
    overview.append("Runs analyzed: ", style="bold")
    overview.append(str(total_runs), style="cyan")
    overview.append("\nCommits completed: ", style="bold")
    overview.append(str(total_commits), style="cyan")
    overview.append("\nCanceled runs: ", style="bold")
    overview.append(str(total_canceled), style="cyan")
    overview.append("\nProjects found: ", style="bold")
    overview.append(str(total_projects), style="cyan")
    overview.append("\nTop accepted project/provider: ", style="bold")
    overview.append(top_label, style="magenta")
    overview.append(" (")
    overview.append(format_pct(top_rate), style=get_acceptance_style(top_rate))
    overview.append(" of shown candidates)")
    console.print(Panel(overview, title="History Overview", expand=False))

    provider_table = Table(title="Acceptance Relative And Average Time", header_style="bold cyan")
    provider_table.add_column("Project", style="bold")
    provider_table.add_column("Provider", style="bold")
    provider_table.add_column("Selected", justify="right")
    provider_table.add_column("Shown", justify="right")
    provider_table.add_column("Accept/Shown", justify="right")
    provider_table.add_column("Cancel/Shown", justify="right")
    provider_table.add_column("Accept/Commits", justify="right")
    provider_table.add_column("Avg Selected", justify="right")
    provider_table.add_column("Avg Shown", justify="right")
    provider_table.add_column("Gen", justify="right")
    provider_table.add_column("Judge", justify="right")
    provider_table.add_column("Refine", justify="right")

    for row in provider_rows:
        provider_table.add_row(
            row["project"],
            row["provider"],
            str(row["selected"]),
            str(row["displayed"]),
            f"[{get_acceptance_style(row['acceptance_vs_shown'])}]"
            f"{format_pct(row['acceptance_vs_shown'])}[/{get_acceptance_style(row['acceptance_vs_shown'])}]",
            format_pct(row["cancel_vs_shown"]),
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
        idx_table.add_row(choice, str(count), format_pct(safe_pct(count, total_runs)))
    console.print(idx_table)


def _render_plain_summary(entries, summary, provider_rows):
    print("History Overview")
    print("================")
    if RICH_IMPORT_ERROR is not None:
        print(
            "Note: Rich is not available in the active environment; "
            "showing a plain-text table instead."
        )
        print(f"Import error: {RICH_IMPORT_ERROR}")
        print("Tip: run install.bat to install missing dependencies into .venv.")
        print()
    print(f"Runs analyzed: {summary['total_runs']}")
    print(f"Commits completed: {summary['total_commits']}")
    print(f"Canceled runs: {summary['total_canceled']}")
    print(f"Projects found: {len(summary['projects'])}")
    if provider_rows:
        print(
            f"Top accepted project/provider: {provider_rows[0]['project']} / "
            f"{provider_rows[0]['provider']} "
            f"({format_pct(provider_rows[0]['acceptance_vs_shown'])} of shown candidates)"
        )
    print()
    print("Acceptance Relative And Average Time")

    provider_headers = [
        "Project",
        "Provider",
        "Selected",
        "Shown",
        "Accept/Shown",
        "Cancel/Shown",
        "Accept/Commits",
        "Avg Selected",
        "Avg Shown",
        "Gen",
        "Judge",
        "Refine",
    ]
    provider_rows_text = [
        [
            row["project"],
            row["provider"],
            str(row["selected"]),
            str(row["displayed"]),
            format_pct(row["acceptance_vs_shown"]),
            format_pct(row["cancel_vs_shown"]),
            format_pct(row["acceptance_vs_commits"]),
            format_seconds(row["avg_selected"]),
            format_seconds(row["avg_displayed"]),
            str(row["generator_usage"]),
            str(row["judge_usage"]),
            str(row["refiner_usage"]),
        ]
        for row in provider_rows
    ]
    _print_plain_table(provider_headers, provider_rows_text)

    print()
    print("Selection Position")
    idx_headers = ["Choice", "Count", "Rate"]
    idx_rows = [
        [
            choice,
            str(count),
            format_pct(safe_pct(count, summary["total_runs"])),
        ]
        for choice, count in sorted(
            summary["selected_indexes"].items(), key=lambda item: int(item[0])
        )
    ]
    _print_plain_table(idx_headers, idx_rows)


def _print_plain_table(headers, rows):
    if not rows:
        print("(no data)")
        return

    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
    numeric_columns = {
        idx for idx, header in enumerate(headers)
        if header not in {"Project", "Provider"}
    }
    widths = []
    for idx, header in enumerate(headers):
        content_width = max(len(header), *(len(row[idx]) for row in rows))
        widths.append(content_width)

    separator = "  "
    minimum_width = sum(widths) + len(separator) * (len(headers) - 1)
    if minimum_width > terminal_width and widths:
        overflow = minimum_width - terminal_width
        text_indexes = [
            idx for idx, header in enumerate(headers)
            if header in {"Project", "Provider"}
        ]
        for text_idx in text_indexes:
            if overflow <= 0:
                break
            min_width = max(8, len(headers[text_idx]))
            shrinkable = max(0, widths[text_idx] - min_width)
            reduction = min(overflow, shrinkable)
            widths[text_idx] -= reduction
            overflow -= reduction

    def clip(value, width):
        if len(value) <= width:
            return value
        if width <= 1:
            return value[:width]
        return value[: width - 1] + "…"

    def format_row(row):
        parts = []
        for idx, value in enumerate(row):
            cell = clip(value, widths[idx])
            if idx in numeric_columns:
                parts.append(cell.rjust(widths[idx]))
            else:
                parts.append(cell.ljust(widths[idx]))
        return separator.join(parts)

    print(format_row(headers))
    print(separator.join("-" * width for width in widths))
    for row in rows:
        print(format_row(row))


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
