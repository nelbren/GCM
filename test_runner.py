#!/usr/bin/env python3

import io
import sys
import unittest

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


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
    summary.append("\nPassed: ", style="bold")
    summary.append(str(len(result.successes)), style="green")
    summary.append("\nFailures: ", style="bold")
    summary.append(str(len(result.failures)), style="red")
    summary.append("\nErrors: ", style="bold")
    summary.append(str(len(result.errors)), style="red")
    summary.append("\nSkipped: ", style="bold")
    summary.append(str(len(result.skipped)), style="yellow")
    summary.append("\nExpected failures: ", style="bold")
    summary.append(str(len(result.expectedFailures)), style="yellow")
    summary.append("\nUnexpected successes: ", style="bold")
    summary.append(str(len(result.unexpectedSuccesses)), style="yellow")
    return summary


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
