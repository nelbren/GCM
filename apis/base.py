from apis.types import ModelResponse


def normalize_response(provider_name, raw_response):
    code, model, content, usage, elapsed = raw_response
    error = None
    if code != 200:
        error = content if isinstance(content, str) else None

    return ModelResponse(
        code=code,
        provider=provider_name,
        model=model,
        content=content if isinstance(content, str) else None,
        usage=usage,
        elapsed=elapsed,
        error=error,
    )
