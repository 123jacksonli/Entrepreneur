"""Robust parser for LLM-generated file output.

The Execution Agent asks the LLM to return files in a structured format:

    FILE: relative/path/to/file.ext
    ```ext
    <content>
    ```

This module parses that format, handles variants (tildes, optional language
labels, nested fences), sanitizes paths, and reports warnings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# Paths that are never allowed, regardless of sanitization.
_BLOCKLISTED_NAMES = {
    ".git",
    ".hg",
    ".svn",
}


@dataclass
class ParserResult:
    files: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _is_path_safe(relative_path: str) -> tuple[bool, str | None]:
    """Return (safe, reason) for a candidate relative path.

    Rejects absolute paths, parent traversal, paths that escape the workspace,
    and a short blocklist of version-control directories.
    """
    if not relative_path:
        return False, "empty path"

    # Reject absolute paths.
    if Path(relative_path).is_absolute():
        return False, f"absolute path not allowed: {relative_path}"

    # Normalize using Path so that ``a/../b`` becomes ``b`` and we can detect
    # any part that would resolve above the workspace root.
    parts = Path(relative_path).parts
    if ".." in parts:
        return False, f"parent-directory traversal not allowed: {relative_path}"

    # Blocklist sensitive directory names anywhere in the path.
    if any(part in _BLOCKLISTED_NAMES for part in parts):
        return False, f"blocklisted directory in path: {relative_path}"

    # Reject hidden system files that could alter behavior outside the project.
    if parts[-1].startswith("~") or parts[-1] in {"Thumbs.db", ".DS_Store"}:
        return False, f"system file not allowed: {relative_path}"

    return True, None


def parse_code_files(text: str) -> ParserResult:
    """Parse FILE:/fenced-block output into a path->content map.

    Supported fence styles:
    - Triple backticks with optional language tag: ```python
    - Triple tildes with optional language tag: ~~~python
    - Fences may contain more than three characters to allow nested content.

    Returns a ParserResult containing the files, any warnings, and an optional
    error message if the response is completely unusable.
    """
    result = ParserResult()

    if not text or not text.strip():
        result.error = "Empty response from LLM."
        return result

    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Regex explanation:
    # - ^FILE:\s*  matches the file marker at start of line.
    # - (\S+)      captures the relative path.
    # - \n         newline after the path.
    # - (`{3,}|~{3,})(?:\w+)?\n  captures the opening fence and optional lang tag.
    # - (.*?)      captures content non-greedily.
    # - \n\1      matches a closing fence with the same character repeated at
    #              least as many times as the opener (so ````` can close ```).
    #
    # DOTALL lets .*? span newlines; MULTILINE lets ^ match line starts.
    pattern = re.compile(
        r"^FILE:\s*(\S+)\n"
        r"(`{3,}|~{3,})(?:\w+)?\n"
        r"(.*?)"
        # The closing fence must be the exact same fence characters. It may
        # appear either immediately after the opening fence (empty file) or on
        # a subsequent line. It is optionally followed by whitespace, and then
        # a newline or end of string. This prevents an inner ```python opening
        # fence from being mistaken for the closing fence of the current block,
        # and it correctly handles empty files.
        r"(?:\n\2|\2)\s*(?:\n|$)",
        re.MULTILINE | re.DOTALL,
    )

    seen_paths: set[str] = set()
    last_end = 0

    for match in pattern.finditer(text):
        # Warn if there is non-whitespace text between matches (explanations).
        between = text[last_end:match.start()]
        if between and between.strip():
            result.warnings.append(
                f"Ignored explanatory text before file at position {match.start()}."
            )
        last_end = match.end()

        raw_path = match.group(1).strip()

        safe, reason = _is_path_safe(raw_path)
        if not safe:
            result.warnings.append(f"Skipping unsafe path '{raw_path}': {reason}")
            continue

        # Strip a leading slash only after confirming the path is relative.
        relative_path = raw_path.lstrip("/")
        # Normalize path separators to POSIX-style forward slashes.
        relative_path = str(Path(relative_path).as_posix())

        if relative_path in seen_paths:
            result.warnings.append(f"Duplicate file '{relative_path}'; using last occurrence.")
        seen_paths.add(relative_path)

        content = match.group(3)
        # Preserve trailing newline behavior: files that the LLM left with a
        # trailing blank line inside the fence keep it; otherwise strip the
        # implicit trailing newline added by the regex match.
        if not content.endswith("\n"):
            content = content.rstrip("\n")
        result.files[relative_path] = content

    # Warn about trailing text after the last file.
    trailing = text[last_end:]
    if trailing and trailing.strip():
        result.warnings.append("Ignored trailing text after last file.")

    if not result.files:
        result.error = "No parseable FILE:/fence blocks found in LLM response."

    return result
