#!/usr/bin/env python3

import io
import sys
import unittest

RICH_IMPORT_ERROR = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
except ImportError as exc:
    RICH_IMPORT_ERROR = exc


TEST_SUMMARY_ROWS = (
    ("passed", "✅", "Passed", "green"),
    ("failures", "❌", "Failures", "red"),
    ("errors", "🚨", "Errors", "red"),
    ("skipped", "⚠️", "Skipped", "yellow"),
    ("expected_failures", "🧪", "Expected failures", "yellow"),
    ("unexpected_successes", "🎉", "Unexpected successes", "yellow"),
)


class RichTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, console):
        super().__init__(stream, descriptions, verbosity)
        self.console = console
        self.successes = []

    def getDescription(self, test):
        return str(test)

    def startTest(self, test):
        super().startTest(test)
        self.console.print(f"[cyan]▶ Running[/cyan] {self.getDescription(test)}")

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)
        self.console.print(f"[green]✅ PASS[/green] {self.getDescription(test)}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.console.print(f"[red]❌ FAIL[/red] {self.getDescription(test)}")

    def addError(self, test, err):
        super().addError(test, err)
        self.console.print(f"[red]❌ ERROR[/red] {self.getDescription(test)}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.console.print(
            f"[yellow]⚠️ SKIP[/yellow] {self.getDescription(test)}"
            f" [dim]({reason})[/dim]"
        )

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.console.print(
            f"[yellow]⚠️ XFAIL[/yellow] {self.getDescription(test)}"
        )

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.console.print(
            f"[yellow]⚠️ XPASS[/yellow] {self.getDescription(test)}"
        )


class RichTestRunner(unittest.TextTestRunner):
    resultclass = RichTestResult

    def __init__(self, *args, console=None, **kwargs):
        self.console = console or Console()
        kwargs.setdefault("verbosity", 2)
        super().__init__(*args, **kwargs)

    def _makeResult(self):
        return self.resultclass(
            self.stream,
            self.descriptions,
            self.verbosity,
            self.console,
        )


def build_summary_text(result):
    summary = Text()
    summary.append("Total: ", style="bold")
    summary.append(str(result.testsRun), style="cyan")
    for row in build_summary_rows(result):
        summary.append("\n")
        summary.append(row["text"], style=row["style"])
    return summary


def get_bar_style(pct):
    if pct >= 75.0:
        return "█"
    if pct >= 50.0:
        return "▓"
    if pct >= 25.0:
        return "▒"
    return "░"


def format_count(value):
    if value < 1000:
        return f"{value:03d}"
    return f"{value:,}"


def format_pct(value):
    return f"{value:.1f}%"


def build_summary_rows(result, width=28):
    total = max(result.testsRun, 0)
    row_counts = {
        "passed": len(result.successes),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    max_count = max(row_counts.values(), default=0)

    rows = []
    for key, emoji, label, color in TEST_SUMMARY_ROWS:
        count = row_counts[key]
        pct = 0.0 if total <= 0 else (count / total) * 100.0
        filled = 0 if max_count <= 0 or count <= 0 else max(1, round((count / max_count) * width))
        bar = get_bar_style(pct) * filled
        rows.append({
            "text": (
                f"{emoji} {label:<20} {bar:<{width}} "
                f"{format_count(count)} ({format_pct(pct)})"
            ),
            "style": color,
        })
    return rows


def print_issue_details(console, result):
    issues = []
    for test, traceback_text in result.failures:
        issues.append(("❌ Failure", test, traceback_text))
    for test, traceback_text in result.errors:
        issues.append(("❌ Error", test, traceback_text))

    for title, test, traceback_text in issues:
        console.print()
        console.print(
            Panel(
                traceback_text.rstrip(),
                title=f"{title} - {test}",
                border_style="red",
            )
        )


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if RICH_IMPORT_ERROR is not None:
        print(
            "Warning: missing Python dependencies required to run tests.\n"
            "Use `./install.bash` to install the necessary dependencies.\n"
            f"Import error: {RICH_IMPORT_ERROR}",
            file=sys.stderr,
        )
        return 1

    console = Console(stderr=False, emoji=True)
    loader = unittest.defaultTestLoader
    suite = loader.discover("tests")

    console.print(Panel.fit("🧪 Running test suite with verbose output", style="cyan"))
    runner = RichTestRunner(
        console=console,
        verbosity=2,
        stream=io.StringIO(),
    )
    result = runner.run(suite)

    console.print()
    if result.wasSuccessful():
        console.print(
            Panel.fit(
                build_summary_text(result),
                title="✅ Test Summary",
                border_style="green",
            )
        )
        console.print("[green]✅ Overall status: all tests passed[/green]")
        return 0

    print_issue_details(console, result)
    console.print(
        Panel.fit(
            build_summary_text(result),
            title="❌ Test Summary",
            border_style="red",
        )
    )
    console.print("[red]❌ Overall status: failures detected[/red]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
