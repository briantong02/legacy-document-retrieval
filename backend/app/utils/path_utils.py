import re


def _collapse_separators(value: str) -> str:
    # Config values and stored paths can disagree on separator repetition
    # (e.g. a doubled-backslash root from over-escaped config). Collapse runs
    # of backslashes to one so the root comparison is not defeated by it.
    return re.sub(r"\\+", "\\\\", value)


def resolve_path(document_path: str, canonical_root: str, local_root: str) -> str:
    canonical_normalized = (
        _collapse_separators(canonical_root.replace("/", "\\")).rstrip("\\").lower()
    )
    document_normalized = _collapse_separators(document_path.replace("/", "\\"))

    if not document_normalized.lower().startswith(canonical_normalized):
        raise ValueError(f"DocumentPath does not start with canonical root: {document_path}")

    relative = document_normalized[len(canonical_normalized) :].lstrip("\\/")
    relative_parts = [part for part in relative.replace(chr(92), "/").split("/") if part]
    local_base = local_root.rstrip("/")

    if not relative_parts:
        return local_base

    return f"{local_base}/{'/'.join(relative_parts)}"
