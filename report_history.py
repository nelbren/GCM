#!/usr/bin/env python3

import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
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


def get_repos_registry_path():
    return os.path.expanduser("~/.gcm/repos.txt")


def load_registered_repos(path=None):
    registry_path = os.path.expanduser(path or get_repos_registry_path())
    if not os.path.exists(registry_path):
        return []

    repos = []
    seen = set()
    with open(registry_path, "r", encoding="utf-8") as f:
        for line in f:
            repo_path = line.strip()
            if not repo_path or repo_path.startswith("#"):
                continue
            normalized = os.path.abspath(os.path.expanduser(repo_path))
            if normalized in seen:
                continue
            seen.add(normalized)
            repos.append(normalized)
    return repos


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


def get_project_path(entry):
    project = entry.get("project")
    if isinstance(project, dict):
        path = project.get("path")
        if path:
            return str(path)
    return None


def normalize_os_name(value):
    if not value:
        return None

    normalized = str(value).strip().upper().replace(" ", "")
    aliases = {
        "WINDOWS": "WINDOWS",
        "WIN": "WINDOWS",
        "CYGWIN": "WINDOWS",
        "GITBASH": "WINDOWS",
        "MSYS": "WINDOWS",
        "MINGW": "WINDOWS",
        "LINUX": "LINUX",
        "MACOS": "MACOS",
        "MAC": "MACOS",
        "DARWIN": "MACOS",
        "OSX": "MACOS",
    }
    return aliases.get(normalized)


def get_entry_os_name(entry):
    final_message = entry.get("final_message") or ""
    message_os_name = parse_os_from_commit_message(final_message)
    if message_os_name:
        return message_os_name

    normalized = normalize_os_name(entry.get("os"))
    if normalized:
        return normalized

    return None


def build_os_summary(summary):
    os_definitions = [
        ("WINDOWS", "🪟", "Windows"),
        ("LINUX", "🐧", "Linux"),
        ("MACOS", "🍎", "MacOS"),
    ]
    return [
        {
            "key": os_key,
            "emoji": emoji,
            "label": label,
            "count": summary["runs_by_os"].get(os_key, 0),
            "pct": safe_pct(summary["runs_by_os"].get(os_key, 0), summary["os_total_runs"]),
        }
        for os_key, emoji, label in os_definitions
    ]


def build_empty_overview():
    return {
        "total_runs": 0,
        "os_total_runs": 0,
        "total_commits": 0,
        "total_canceled": 0,
        "projects": set(),
        "runs_by_os": defaultdict(int),
    }


def parse_os_from_commit_message(message):
    if not message:
        return None

    match = re.search(r"🌐:\s*(WINDOWS|LINUX|MACOS|CYGWIN|GITBASH)\b", message)
    if match:
        return normalize_os_name(match.group(1))

    header_match = re.search(r"\[💻[^\]\r\n]*([🪟🐧🍎])\]", message)
    if header_match:
        emoji_map = {
            "🪟": "WINDOWS",
            "🐧": "LINUX",
            "🍎": "MACOS",
        }
        return emoji_map.get(header_match.group(1))

    return None


def parse_provider_from_commit_message(message):
    if not message:
        return None

    match = re.search(r"🤖:\s*(.+?)\s+🧠:", message)
    if not match:
        return None
    return match.group(1).strip()


def parse_elapsed_from_commit_message(message):
    if not message:
        return None

    match = re.search(r"⏱️:\s*([0-9]+(?:\.[0-9]+)?)\s+secs\b", message)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def load_git_log_messages(project_path):
    safe_path = os.path.abspath(project_path)
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={safe_path}",
            "log",
            "--pretty=format:%B%x1e",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        cwd=project_path,
    )
    return [message.strip() for message in result.stdout.split("\x1e") if message.strip()]


def summarize_selected_commits(entries, summary):
    committed_entries = [entry for entry in entries if entry.get("outcome", "committed") != "canceled"]
    entries_by_project_path = defaultdict(list)
    fallback_entries = []

    for entry in committed_entries:
        project_path = get_project_path(entry)
        if project_path:
            entries_by_project_path[project_path].append(entry)
        else:
            fallback_entries.append(entry)

    for project_path, project_entries in entries_by_project_path.items():
        try:
            log_messages = load_git_log_messages(project_path)
        except (OSError, subprocess.SubprocessError):
            fallback_entries.extend(project_entries)
            continue

        message_counts = Counter(log_messages)
        for entry in project_entries:
            final_message = (entry.get("final_message") or "").strip()
            project_name = get_project_name(entry)
            selected_provider = None
            selected_elapsed = None

            if final_message and message_counts.get(final_message, 0) > 0:
                message_counts[final_message] -= 1
                selected_provider = parse_provider_from_commit_message(final_message)
                selected_elapsed = parse_elapsed_from_commit_message(final_message)

            if not selected_provider:
                fallback_entries.append(entry)
                continue

            key = (project_name, selected_provider)
            summary["selection_by_project_provider"][key] += 1
            if isinstance(selected_elapsed, (int, float)):
                summary["avg_selected_elapsed_by_project_provider"][key].append(
                    selected_elapsed
                )

    for entry in fallback_entries:
        project_name = get_project_name(entry)
        selected_candidate = entry.get("selected_candidate") or {}
        selected_provider = selected_candidate.get("provider")
        selected_elapsed = selected_candidate.get("elapsed")
        if not selected_provider:
            continue

        key = (project_name, selected_provider)
        summary["selection_by_project_provider"][key] += 1
        if isinstance(selected_elapsed, (int, float)):
            summary["avg_selected_elapsed_by_project_provider"][key].append(
                selected_elapsed
            )


def summarize_committed_os(entries, summary):
    project_paths = []
    seen_paths = set()
    fallback_entries = []

    for entry in entries:
        project_path = get_project_path(entry)
        if project_path and project_path not in seen_paths:
            seen_paths.add(project_path)
            project_paths.append(project_path)
        elif not project_path and entry.get("outcome", "committed") != "canceled":
            fallback_entries.append(entry)

    for project_path in project_paths:
        try:
            log_messages = load_git_log_messages(project_path)
        except (OSError, subprocess.SubprocessError):
            continue

        for message in log_messages:
            os_name = parse_os_from_commit_message(message)
            if not os_name:
                continue
            summary["runs_by_os"][os_name] += 1
            summary["os_total_runs"] += 1

    for entry in fallback_entries:
        os_name = get_entry_os_name(entry)
        if os_name:
            summary["runs_by_os"][os_name] += 1
            summary["os_total_runs"] += 1


def summarize_os_for_scope(entries, project_paths=None):
    overview = build_empty_overview()
    project_paths = project_paths or []
    seen_paths = set()
    fallback_entries = []

    for project_path in project_paths:
        if project_path and project_path not in seen_paths:
            seen_paths.add(project_path)

    for project_path in seen_paths:
        try:
            log_messages = load_git_log_messages(project_path)
        except (OSError, subprocess.SubprocessError):
            continue

        for message in log_messages:
            os_name = parse_os_from_commit_message(message)
            if not os_name:
                continue
            overview["runs_by_os"][os_name] += 1
            overview["os_total_runs"] += 1

    if not seen_paths:
        for entry in entries:
            if entry.get("outcome", "committed") == "canceled":
                continue
            fallback_entries.append(entry)

    for entry in fallback_entries:
        os_name = get_entry_os_name(entry)
        if os_name:
            overview["runs_by_os"][os_name] += 1
            overview["os_total_runs"] += 1

    return overview


def collect_project_paths_from_entries(entries):
    project_paths = []
    seen_paths = set()

    for entry in entries:
        project_path = get_project_path(entry)
        if not project_path:
            continue
        normalized = os.path.abspath(project_path)
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        project_paths.append(normalized)

    return project_paths


def summarize_entries(entries):
    summary = {
        "total_runs": len(entries),
        "os_total_runs": 0,
        "total_commits": 0,
        "total_canceled": 0,
        "projects": set(),
        "runs_by_os": defaultdict(int),
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

    summarize_committed_os(entries, summary)
    summarize_selected_commits(entries, summary)
    return summary


def build_overview_summary(entries, project_path=None, project_name=None):
    overview = build_empty_overview()
    normalized_path = os.path.abspath(project_path) if project_path else None
    filtered_entries = []
    filtered_project_paths = []
    seen_paths = set()

    for entry in entries:
        entry_project_name = get_project_name(entry)
        entry_project_path = get_project_path(entry)
        entry_project_path = os.path.abspath(entry_project_path) if entry_project_path else None

        matches_project = True
        if normalized_path:
            matches_project = entry_project_path == normalized_path
        elif project_name:
            matches_project = entry_project_name == project_name

        if not matches_project:
            continue

        filtered_entries.append(entry)
        overview["projects"].add(entry_project_name)
        overview["total_runs"] += 1
        if entry_project_path and entry_project_path not in seen_paths:
            seen_paths.add(entry_project_path)
            filtered_project_paths.append(entry_project_path)

        if entry.get("outcome", "committed") == "canceled":
            overview["total_canceled"] += 1
        else:
            overview["total_commits"] += 1

    scope_paths = [normalized_path] if normalized_path else filtered_project_paths
    os_summary = summarize_os_for_scope(filtered_entries, scope_paths)
    overview["runs_by_os"] = os_summary["runs_by_os"]
    overview["os_total_runs"] = os_summary["os_total_runs"]
    return overview


def build_global_overview(entries, registered_repos=None):
    overview = build_empty_overview()
    filtered_entries = list(entries)
    registered_paths = []
    seen_paths = set()

    for repo_path in registered_repos or []:
        normalized = os.path.abspath(repo_path)
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        registered_paths.append(normalized)

    if not registered_paths:
        registered_paths = collect_project_paths_from_entries(entries)

    for entry in filtered_entries:
        overview["projects"].add(get_project_name(entry))
        overview["total_runs"] += 1
        if entry.get("outcome", "committed") == "canceled":
            overview["total_canceled"] += 1
        else:
            overview["total_commits"] += 1

    os_summary = summarize_os_for_scope(filtered_entries, registered_paths)
    overview["runs_by_os"] = os_summary["runs_by_os"]
    overview["os_total_runs"] = os_summary["os_total_runs"]
    return overview


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


def format_overview_count(value):
    if value < 1000:
        return f"{value:03d}"
    return f"{value:,}"


def get_os_bar_style(pct):
    if pct >= 75.0:
        return "█", "green"
    if pct >= 50.0:
        return "▓", "blue"
    if pct >= 25.0:
        return "▒", "yellow"
    return "░", "dark_orange"


def build_os_bar_chart_lines(overview, width=28):
    rows = build_os_summary(overview)
    max_count = max((row["count"] for row in rows), default=0)
    if max_count <= 0:
        return []

    lines = []
    for row in rows:
        filled = 0 if row["count"] <= 0 else max(1, round((row["count"] / max_count) * width))
        bar_char, color = get_os_bar_style(row["pct"])
        bar = bar_char * filled
        lines.append({
            "text": (
                f"{row['emoji']} {row['label']:<7} {bar:<{width}} "
                f"{format_overview_count(row['count'])} ({format_pct(row['pct'])})"
            ),
            "style": color,
        })
    return lines


def get_acceptance_style(value):
    if value >= 60:
        return "green"
    if value >= 30:
        return "yellow"
    return "red"


def render_summary(entries, summary, provider_rows, global_overview, project_overview, project_label):
    if HAS_RICH:
        _render_rich_summary(
            entries,
            summary,
            provider_rows,
            global_overview,
            project_overview,
            project_label,
        )
        return
    _render_plain_summary(
        entries,
        summary,
        provider_rows,
        global_overview,
        project_overview,
        project_label,
    )


def _build_overview_text(overview, provider_rows=None):
    total_runs = overview["total_runs"]
    total_commits = overview["total_commits"]
    total_canceled = overview["total_canceled"]
    total_projects = len(overview["projects"])
    top_label = (
        f"{provider_rows[0]['project']} / {provider_rows[0]['provider']}"
        if provider_rows else "N/A"
    )
    top_rate = provider_rows[0]["acceptance_vs_shown"] if provider_rows else 0.0

    overview_text = Text()
    overview_text.append("Runs analyzed: ", style="bold")
    overview_text.append(format_overview_count(total_runs), style="cyan")
    overview_text.append("\nCommits completed: ", style="bold")
    overview_text.append(format_overview_count(total_commits), style="cyan")
    overview_text.append("\nCanceled runs: ", style="bold")
    overview_text.append(format_overview_count(total_canceled), style="cyan")
    overview_text.append("\nProjects found: ", style="bold")
    overview_text.append(format_overview_count(total_projects), style="cyan")
    chart_lines = build_os_bar_chart_lines(overview)
    if chart_lines:
        overview_text.append("\nOS bar chart:", style="bold")
        for line in chart_lines:
            overview_text.append(f"\n{line['text']}", style=line["style"])
    if provider_rows is not None:
        overview_text.append("\nTop accepted project/provider: ", style="bold")
        overview_text.append(top_label, style="magenta")
        overview_text.append(" (")
        overview_text.append(format_pct(top_rate), style=get_acceptance_style(top_rate))
        overview_text.append(" of shown candidates)")
    return overview_text


def _render_rich_summary(entries, summary, provider_rows, global_overview, project_overview, project_label):
    console = Console()
    console.print(
        Panel(
            _build_overview_text(global_overview, provider_rows),
            title="History Overview Global",
            expand=False,
        )
    )
    console.print(
        Panel(
            _build_overview_text(project_overview),
            title=f"History Overview Project ({project_label})",
            expand=False,
        )
    )

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
        idx_table.add_row(choice, str(count), format_pct(safe_pct(count, summary["total_runs"])))
    console.print(idx_table)


def _print_plain_overview(title, overview, provider_rows=None):
    print(title)
    print("=" * len(title))
    if RICH_IMPORT_ERROR is not None:
        print(
            "Note: Rich is not available in the active environment; "
            "showing a plain-text table instead."
        )
        print(f"Import error: {RICH_IMPORT_ERROR}")
        print("Tip: run install.bat to install missing dependencies into .venv.")
        print()
    print(f"Runs analyzed: {format_overview_count(overview['total_runs'])}")
    print(f"Commits completed: {format_overview_count(overview['total_commits'])}")
    print(f"Canceled runs: {format_overview_count(overview['total_canceled'])}")
    print(f"Projects found: {format_overview_count(len(overview['projects']))}")
    chart_lines = build_os_bar_chart_lines(overview)
    if chart_lines:
        print("OS bar chart:")
        for line in chart_lines:
            print(line["text"])
    if provider_rows is not None and provider_rows:
        print(
            f"Top accepted project/provider: {provider_rows[0]['project']} / "
            f"{provider_rows[0]['provider']} "
            f"({format_pct(provider_rows[0]['acceptance_vs_shown'])} of shown candidates)"
        )
    print()


def _render_plain_summary(entries, summary, provider_rows, global_overview, project_overview, project_label):
    _print_plain_overview("History Overview Global", global_overview, provider_rows)
    _print_plain_overview(f"History Overview Project ({project_label})", project_overview)
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
    current_project_path = os.path.abspath(os.getcwd())
    current_project_name = os.path.basename(current_project_path) or current_project_path
    registered_repos = load_registered_repos()
    global_overview = build_global_overview(entries, registered_repos)
    project_overview = build_overview_summary(
        entries,
        project_path=current_project_path,
        project_name=current_project_name,
    )
    provider_rows = compute_provider_rows(summary)
    render_summary(
        entries,
        summary,
        provider_rows,
        global_overview,
        project_overview,
        current_project_name,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
