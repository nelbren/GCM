from apis.base import normalize_response
from apis.types import CandidateMessage, ExecutionPlan


def build_execution_plan(providers, config):
    generators = sorted(
        [provider for provider in providers if "generate" in provider.roles],
        key=lambda provider: provider.priority
    )
    judges = sorted(
        [provider for provider in providers if "judge" in provider.roles],
        key=lambda provider: provider.priority,
        reverse=True
    )
    refiners = sorted(
        [provider for provider in providers if "refine" in provider.roles],
        key=lambda provider: provider.priority,
        reverse=True
    )

    max_generators = config.get(
        "generator_count",
        config.get("suggested_messages", 1)
    )
    judge_enabled = config.get("enable_judge", False)
    refiner_enabled = config.get("enable_refiner", False)

    return ExecutionPlan(
        generators=generators[:max_generators],
        judge=judges[0] if judge_enabled and judges else None,
        refiner=refiners[0] if refiner_enabled and refiners else None,
    )


def validate_message(content, max_characters):
    if not content or not content.strip():
        return False, "empty"

    content = content.strip()
    if max_characters and len(content) > max_characters:
        return False, "too_long"

    forbidden_markers = [
        "Changes:",
        "Diff summary:",
        "{changes}",
        "{diff}",
    ]
    if any(marker in content for marker in forbidden_markers):
        return False, "echoed_input"

    conventional_prefixes = (
        "feat:", "fix:", "chore:", "refactor:", "docs:",
        "test:", "ci:", "build:", "perf:", "style:"
    )
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return False, "empty"
    if not any(lines[0].lower().startswith(prefix) for prefix in conventional_prefixes):
        return False, "invalid_prefix"

    return True, None


def run_generators(generators, prompt, max_characters):
    candidates = []

    for provider in generators:
        response = normalize_response(
            provider.name,
            provider.query_fn(prompt)
        )
        if response.code != 200 or not response.content:
            continue

        content = response.content[:max_characters] if max_characters else response.content
        valid, _ = validate_message(content, max_characters)
        if not valid:
            continue

        candidates.append(CandidateMessage(
            provider=response.provider,
            model=response.model,
            content=content,
            usage=response.usage,
            elapsed=response.elapsed,
        ))

    return candidates


def build_judge_prompt(base_prompt, candidates, max_characters):
    candidate_lines = []
    for idx, candidate in enumerate(candidates, 1):
        candidate_lines.append(f"{idx}. {candidate.content}")

    return "\n".join([
        "Using the same repository context below, choose the best commit message candidate.",
        "",
        "Rules:",
        "- Must be faithful to the changes.",
        "- Must not list file names or paths.",
        "- Must use Conventional Commits.",
        f"- Must be concise, complete, and within {max_characters} characters.",
        "- Return only the selected message, optionally rewritten for clarity.",
        "",
        "Context:",
        base_prompt,
        "",
        "Candidates:",
        *candidate_lines,
    ])


def run_judge(judge, base_prompt, candidates, max_characters):
    if not judge or len(candidates) < 2:
        return candidates[0] if candidates else None

    prompt = build_judge_prompt(base_prompt, candidates, max_characters)
    response = normalize_response(judge.name, judge.query_fn(prompt))
    if response.code != 200 or not response.content:
        return candidates[0]

    content = response.content[:max_characters] if max_characters else response.content
    valid, _ = validate_message(content, max_characters)
    if not valid:
        return candidates[0]

    return CandidateMessage(
        provider=response.provider,
        model=response.model,
        content=content,
        usage=response.usage,
        elapsed=response.elapsed,
    )


def build_refiner_prompt(base_prompt, candidate, max_characters):
    return "\n".join([
        "Using the same repository context below, improve this commit message.",
        "",
        "Constraints:",
        "- Preserve meaning.",
        "- Do not list file names or paths.",
        f"- Keep it within {max_characters} characters.",
        "- Use plain text only.",
        "- Return only the improved commit message.",
        "",
        "Context:",
        base_prompt,
        "",
        "Candidate:",
        candidate.content,
    ])


def run_refiner(refiner, base_prompt, candidate, max_characters):
    if not refiner or not candidate:
        return candidate

    prompt = build_refiner_prompt(base_prompt, candidate, max_characters)
    response = normalize_response(refiner.name, refiner.query_fn(prompt))
    if response.code != 200 or not response.content:
        return candidate

    content = response.content[:max_characters] if max_characters else response.content
    valid, _ = validate_message(content, max_characters)
    if not valid:
        return candidate

    return CandidateMessage(
        provider=response.provider,
        model=response.model,
        content=content,
        usage=response.usage,
        elapsed=response.elapsed,
    )
