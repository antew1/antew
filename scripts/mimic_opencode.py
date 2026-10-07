#!/usr/bin/env python3
"""Return plain Python to Mimic from OpenCode's structured output."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MODEL = "opencode/big-pickle"


def failure_detail(raw):
    """Report only fixed error names and HTTP status, never provider payloads."""
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "error":
            continue
        error = event.get("error") or {}
        if not isinstance(error, dict):
            continue
        data = error.get("data") or {}
        status = data.get("statusCode") if isinstance(data, dict) else None
        status_text = f"HTTP {status}" if type(status) is int and 100 <= status <= 599 else ""
        try:
            body = json.loads(data.get("responseBody", "{}")) if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            body = {}
        nested = body.get("error") if isinstance(body, dict) else None
        candidates = [body.get("_tag")] if isinstance(body, dict) else []
        if isinstance(nested, dict):
            candidates.extend([nested.get("type"), nested.get("_tag"), nested.get("name")])
        known = {
            "FreeTierError", "Forbidden", "Unauthorized", "AuthenticationError",
            "InsufficientBalanceError", "BillingError", "PermissionDenied",
            "ModelNotFoundError", "RateLimitError",
        }
        kind = next((item for item in candidates if isinstance(item, str) and item in known), "")
        if kind:
            return "; ".join(item for item in (status_text, kind) if item)
        if status_text:
            return status_text
        name = error.get("name")
        if name in {"ProviderModelNotFoundError", "ProviderAuthError", "ConfigInvalidError"}:
            return name
    return "provider request failed"


def python_from_events(raw):
    chunks = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "error":
            raise RuntimeError(f"OpenCode reported a provider error ({failure_detail(raw)}).")
        part = event.get("part") or {}
        if event.get("type") == "text" and isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    source = "\n".join(chunks).strip()
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", source, re.S)
    if match:
        source = match.group(1).strip()
    if not source:
        raise RuntimeError("OpenCode returned no Python code.")
    try:
        ast.parse(source)
    except SyntaxError as error:
        raise RuntimeError("OpenCode returned invalid Python code.") from error
    return source + "\n"


def main():
    binary = os.environ["MIMIC_OPENCODE_BINARY"]
    config = os.environ["MIMIC_OPENCODE_CONFIG"]
    state = Path(os.environ["MIMIC_OPENCODE_STATE_DIR"])
    environment = os.environ.copy()
    environment["OPENCODE_CONFIG"] = config
    for name, directory in (
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_CACHE_HOME", "cache"),
    ):
        environment[name] = str(state / directory)
    arguments = sys.argv[1:]
    if not arguments or arguments[0] != "run":
        os.execvpe(binary, [binary, *arguments], environment)
    if len(arguments) != 2:
        raise RuntimeError("Mimic integration expects: opencode run PROMPT.")
    result = subprocess.run(
        [binary, "run", "--format", "json", "--model", MODEL,
         "--title", "Mimic client generation", arguments[1]],
        env=environment, capture_output=True, text=True, timeout=240,
    )
    if result.returncode:
        raise RuntimeError(
            f"OpenCode request failed ({failure_detail(result.stdout)}). "
            "Check OPENCODE_API_KEY and model access."
        )
    sys.stdout.write(python_from_events(result.stdout))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"OpenCode integration: {error}", file=sys.stderr)
        sys.exit(1)

