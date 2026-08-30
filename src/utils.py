"""
utils.py
--------
Small shared helpers used across the NetSage AI codebase.
"""
import json
import os
import re
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")


def now_iso():
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def strip_code_fences(text):
    """Remove ```json ... ``` or ``` ... ``` fences some LLMs wrap around JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def safe_json_parse(text, fallback=None):
    """Best-effort JSON parsing that tolerates code fences and stray text."""
    cleaned = strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to salvage the first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return fallback


def flatten_show_outputs(show_outputs: dict) -> str:
    """Join a case's {command: output} dict into one text blob for parsing/prompting."""
    parts = []
    for cmd, output in show_outputs.items():
        parts.append(f"$ {cmd}\n{output}")
    return "\n\n".join(parts)


def truncate(text, max_len=400):
    text = str(text)
    return text if len(text) <= max_len else text[:max_len].rstrip() + "..."
