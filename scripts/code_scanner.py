#!/usr/bin/env python3
"""Code Pattern Scanner for direction-analyzer.

Scans codebases for patterns indicating work in progress: TODOs, FIXMEs,
incomplete implementations, feature flags, and commented-out code blocks.
"""

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


# Directories to skip during scanning
SKIP_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".cache",
    ".tox",
    "site-packages",
    "vendor",
    "target",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

# File extensions to scan, grouped by language
LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "go": {".go"},
    "rust": {".rs"},
    "markdown": {".md"},
}

# All supported extensions (flattened)
SUPPORTED_EXTENSIONS = set()
for exts in LANGUAGE_EXTENSIONS.values():
    SUPPORTED_EXTENSIONS.update(exts)

# Comment syntax by extension
SINGLE_LINE_COMMENTS = {
    ".py": "#",
    ".js": "//",
    ".jsx": "//",
    ".mjs": "//",
    ".cjs": "//",
    ".ts": "//",
    ".tsx": "//",
    ".go": "//",
    ".rs": "//",
}

# Multi-line comment markers (start, end)
MULTI_LINE_COMMENTS = {
    ".py": [('"""', '"""'), ("'''", "'''")],
    ".js": [("/*", "*/")],
    ".jsx": [("/*", "*/")],
    ".mjs": [("/*", "*/")],
    ".cjs": [("/*", "*/")],
    ".ts": [("/*", "*/")],
    ".tsx": [("/*", "*/")],
    ".go": [("/*", "*/")],
    ".rs": [("/*", "*/")],
}

# Patterns for TODO markers
TODO_PATTERN = re.compile(
    r"\b(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE|REFACTOR)\b[:\s]*(.*)",
    re.IGNORECASE
)

# Incomplete implementation patterns by extension
INCOMPLETE_PATTERNS = {
    ".py": [
        (r"raise\s+NotImplementedError", "NotImplementedError"),
        (r"^\s*pass\s*$", "pass statement"),
        (r"^\s*\.\.\.\s*$", "ellipsis placeholder"),
        (r"raise\s+NotImplemented\b", "NotImplemented (incorrect)"),
    ],
    ".js": [
        (r'throw\s+new\s+Error\s*\(\s*[\'"]not\s+implemented', "throw not implemented"),
        (r"^\s*//\s*TODO\s*$", "TODO placeholder"),
    ],
    ".jsx": [
        (r'throw\s+new\s+Error\s*\(\s*[\'"]not\s+implemented', "throw not implemented"),
        (r"^\s*//\s*TODO\s*$", "TODO placeholder"),
    ],
    ".mjs": [
        (r'throw\s+new\s+Error\s*\(\s*[\'"]not\s+implemented', "throw not implemented"),
    ],
    ".cjs": [
        (r'throw\s+new\s+Error\s*\(\s*[\'"]not\s+implemented', "throw not implemented"),
    ],
    ".ts": [
        (r'throw\s+new\s+Error\s*\(\s*[\'"]not\s+implemented', "throw not implemented"),
        (r"^\s*//\s*TODO\s*$", "TODO placeholder"),
    ],
    ".tsx": [
        (r'throw\s+new\s+Error\s*\(\s*[\'"]not\s+implemented', "throw not implemented"),
        (r"^\s*//\s*TODO\s*$", "TODO placeholder"),
    ],
    ".go": [
        (r"panic\s*\(\s*['\"]not\s+implemented", "panic not implemented"),
        (r"panic\s*\(\s*['\"]TODO", "panic TODO"),
    ],
    ".rs": [
        (r"todo!\s*\(", "todo! macro"),
        (r"unimplemented!\s*\(", "unimplemented! macro"),
        (r"panic!\s*\(\s*['\"]not\s+implemented", "panic not implemented"),
    ],
}

# Feature flag patterns
FEATURE_FLAG_PATTERNS = [
    (r"os\.(?:getenv|environ)\.get\s*\(\s*['\"](\w*(?:FEATURE|FLAG|ENABLE|DISABLE)\w*)['\"]",
     "env var", "python"),
    (r"process\.env\.(\w*(?:FEATURE|FLAG|ENABLE|DISABLE)\w*)",
     "env var", "javascript"),
    (r"os\.Getenv\s*\(\s*['\"](\w*(?:FEATURE|FLAG|ENABLE|DISABLE)\w*)['\"]",
     "env var", "go"),
    (r"std::env::var\s*\(\s*['\"](\w*(?:FEATURE|FLAG|ENABLE|DISABLE)\w*)['\"]",
     "env var", "rust"),
    (r"(?:FEATURE|FLAG|ENABLE|DISABLE)_\w+\s*[:=]\s*(?:True|False|true|false)",
     "hardcoded bool", "any"),
    (r"#\s*\[cfg\s*\(\s*feature\s*=\s*['\"](\w+)['\"]",
     "rust feature gate", "rust"),
    (r"if\s+(?:FEATURE|FLAG|ENABLE|DISABLE)_\w+",
     "feature conditional", "any"),
]


def load_gitignore_patterns(root: Path) -> list[str]:
    """Load patterns from .gitignore file.

    Args:
        root: Repository root directory

    Returns:
        List of gitignore pattern strings
    """
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return []

    patterns = []
    with open(gitignore_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def matches_gitignore(path: Path, root: Path, patterns: list[str]) -> bool:
    """Check if a path matches any gitignore pattern.

    Simple implementation that handles common patterns.

    Args:
        path: Path to check
        root: Repository root
        patterns: List of gitignore patterns

    Returns:
        True if path should be ignored
    """
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        return False

    rel_str = str(rel_path)
    name = path.name

    for pattern in patterns:
        # Directory pattern (ends with /)
        if pattern.endswith("/"):
            dir_pattern = pattern[:-1]
            if name == dir_pattern or f"/{dir_pattern}/" in f"/{rel_str}/":
                return True
        # Wildcard pattern
        elif "*" in pattern:
            import fnmatch
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(name, pattern):
                return True
        # Exact match
        elif name == pattern or rel_str == pattern:
            return True

    return False


def is_binary_file(path: Path) -> bool:
    """Check if a file appears to be binary.

    Args:
        path: Path to file

    Returns:
        True if file appears binary
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
    except (OSError, IOError):
        return True
    return False


def iter_source_files(
    root: Path,
    gitignore_patterns: list[str]
) -> Iterator[Path]:
    """Iterate over source files in directory tree.

    Skips binary files, excluded directories, and gitignored files.

    Args:
        root: Root directory to scan
        gitignore_patterns: Patterns from .gitignore

    Yields:
        Paths to source files
    """
    for item in root.iterdir():
        if item.name.startswith(".") and item.name not in {".github", ".gitlab"}:
            continue

        if item.is_dir():
            if item.name in SKIP_DIRS:
                continue
            if matches_gitignore(item, root.parent if root != root.parent else root,
                                gitignore_patterns):
                continue
            yield from iter_source_files(item, gitignore_patterns)
        elif item.is_file():
            if item.suffix not in SUPPORTED_EXTENSIONS:
                continue
            if matches_gitignore(item, root.parent if root != root.parent else root,
                                gitignore_patterns):
                continue
            if is_binary_file(item):
                continue
            yield item


def read_file_lines(path: Path) -> list[str]:
    """Read file as lines, handling encoding errors.

    Args:
        path: Path to file

    Returns:
        List of lines (empty if read fails)
    """
    encodings = ["utf-8", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with open(path, encoding=encoding) as f:
                return f.readlines()
        except (UnicodeDecodeError, OSError):
            continue
    return []


def get_context(lines: list[str], line_num: int, context_size: int = 2) -> str:
    """Get surrounding context for a line.

    Args:
        lines: All lines in file
        line_num: Target line number (1-indexed)
        context_size: Number of lines before/after

    Returns:
        Context string with line numbers
    """
    idx = line_num - 1
    start = max(0, idx - context_size)
    end = min(len(lines), idx + context_size + 1)

    context_lines = []
    for i in range(start, end):
        prefix = ">" if i == idx else " "
        context_lines.append(f"{prefix}{i + 1:4d}: {lines[i].rstrip()}")

    return "\n".join(context_lines)


def get_function_name(lines: list[str], line_num: int, ext: str) -> Optional[str]:
    """Try to detect the enclosing function name.

    Args:
        lines: All lines in file
        line_num: Target line number (1-indexed)
        ext: File extension

    Returns:
        Function name if found, None otherwise
    """
    # Patterns for function definitions by extension
    func_patterns = {
        ".py": r"^\s*(?:async\s+)?def\s+(\w+)",
        ".js": r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?function|(\w+)\s*=\s*(?:async\s+)?\()",
        ".jsx": r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?function|(\w+)\s*=\s*(?:async\s+)?\()",
        ".ts": r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?function|(\w+)\s*=\s*(?:async\s+)?\()",
        ".tsx": r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?function|(\w+)\s*=\s*(?:async\s+)?\()",
        ".go": r"^func\s+(?:\([^)]+\)\s+)?(\w+)",
        ".rs": r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)",
    }

    pattern_str = func_patterns.get(ext)
    if not pattern_str:
        return None

    pattern = re.compile(pattern_str)

    # Search backwards from the line
    for i in range(line_num - 1, -1, -1):
        match = pattern.match(lines[i])
        if match:
            # Return first non-None group
            for group in match.groups():
                if group:
                    return group
    return None


def run_git_blame(file_path: Path, line_num: int) -> tuple[Optional[str], Optional[str]]:
    """Get git blame info for a specific line.

    Args:
        file_path: Path to file
        line_num: Line number (1-indexed)

    Returns:
        Tuple of (author, date) or (None, None) if unavailable
    """
    try:
        result = subprocess.run(
            ["git", "blame", "-L", f"{line_num},{line_num}", "--porcelain", str(file_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=file_path.parent
        )
        if result.returncode != 0:
            return None, None

        author = None
        date = None
        for line in result.stdout.split("\n"):
            if line.startswith("author "):
                author = line[7:]
            elif line.startswith("author-time "):
                timestamp = int(line[12:])
                date = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

        return author, date
    except (subprocess.SubprocessError, OSError, ValueError):
        return None, None


def scan_todo_markers(
    path: str = ".",
    include_blame: bool = False
) -> list[dict]:
    """Find TODO/FIXME/HACK/XXX comments in the codebase.

    Args:
        path: Directory to scan
        include_blame: Whether to include git blame info

    Returns:
        List of todo marker dictionaries
    """
    root = Path(path).resolve()
    gitignore_patterns = load_gitignore_patterns(root)
    results = []

    for file_path in iter_source_files(root, gitignore_patterns):
        lines = read_file_lines(file_path)
        if not lines:
            continue

        for i, line in enumerate(lines):
            match = TODO_PATTERN.search(line)
            if match:
                marker_type = match.group(1).upper()
                content = match.group(2).strip()

                result = {
                    "file_path": str(file_path.relative_to(root)),
                    "line_number": i + 1,
                    "marker_type": marker_type,
                    "content": content,
                    "context": get_context(lines, i + 1),
                }

                if include_blame:
                    author, date = run_git_blame(file_path, i + 1)
                    result["author"] = author
                    result["date"] = date

                results.append(result)

    return results


def scan_incomplete_implementations(path: str = ".") -> list[dict]:
    """Find incomplete code patterns like NotImplementedError, pass, etc.

    Args:
        path: Directory to scan

    Returns:
        List of incomplete implementation dictionaries
    """
    root = Path(path).resolve()
    gitignore_patterns = load_gitignore_patterns(root)
    results = []

    for file_path in iter_source_files(root, gitignore_patterns):
        ext = file_path.suffix
        patterns = INCOMPLETE_PATTERNS.get(ext, [])
        if not patterns:
            continue

        lines = read_file_lines(file_path)
        if not lines:
            continue

        for i, line in enumerate(lines):
            for pattern_str, pattern_type in patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(line):
                    result = {
                        "file_path": str(file_path.relative_to(root)),
                        "line_number": i + 1,
                        "pattern_type": pattern_type,
                        "function_name": get_function_name(lines, i + 1, ext),
                        "context": get_context(lines, i + 1),
                    }
                    results.append(result)
                    break  # Only report once per line

    return results


def scan_feature_flags(path: str = ".") -> list[dict]:
    """Find feature flag patterns in the codebase.

    Args:
        path: Directory to scan

    Returns:
        List of feature flag dictionaries
    """
    root = Path(path).resolve()
    gitignore_patterns = load_gitignore_patterns(root)
    results = []

    # Compile patterns
    compiled_patterns = []
    for pattern_str, flag_type, lang in FEATURE_FLAG_PATTERNS:
        compiled_patterns.append((re.compile(pattern_str, re.IGNORECASE), flag_type, lang))

    for file_path in iter_source_files(root, gitignore_patterns):
        ext = file_path.suffix
        lines = read_file_lines(file_path)
        if not lines:
            continue

        # Determine language for filtering patterns
        file_lang = None
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if ext in exts:
                file_lang = lang
                break

        for i, line in enumerate(lines):
            for pattern, flag_type, lang in compiled_patterns:
                # Skip patterns not applicable to this language
                if lang != "any":
                    if file_lang and lang != file_lang:
                        continue

                match = pattern.search(line)
                if match:
                    # Try to extract flag name from capture group
                    flag_name = None
                    if match.groups():
                        flag_name = match.group(1) if match.group(1) else None

                    result = {
                        "file_path": str(file_path.relative_to(root)),
                        "line_number": i + 1,
                        "flag_name": flag_name,
                        "flag_type": flag_type,
                        "context": get_context(lines, i + 1),
                    }
                    results.append(result)
                    break  # Only report once per line

    return results


def scan_commented_code(path: str = ".") -> list[dict]:
    """Find significant commented-out code blocks (3+ consecutive lines).

    Args:
        path: Directory to scan

    Returns:
        List of commented code block dictionaries
    """
    root = Path(path).resolve()
    gitignore_patterns = load_gitignore_patterns(root)
    results = []

    for file_path in iter_source_files(root, gitignore_patterns):
        ext = file_path.suffix
        if ext == ".md":
            continue  # Skip markdown files

        comment_char = SINGLE_LINE_COMMENTS.get(ext)
        if not comment_char:
            continue

        lines = read_file_lines(file_path)
        if not lines:
            continue

        # Track consecutive comment lines
        comment_block_start = None
        comment_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if line is a comment (excluding empty comments)
            is_comment = False
            if stripped.startswith(comment_char):
                content_after_comment = stripped[len(comment_char):].strip()
                # Only count as code comment if it looks like code
                # (has operators, parens, etc., not just text)
                if content_after_comment and _looks_like_code(content_after_comment):
                    is_comment = True

            if is_comment:
                if comment_block_start is None:
                    comment_block_start = i + 1
                    comment_lines = [stripped]
                else:
                    comment_lines.append(stripped)
            else:
                # End of comment block
                if comment_block_start is not None and len(comment_lines) >= 3:
                    preview = "\n".join(comment_lines)[:100]
                    result = {
                        "file_path": str(file_path.relative_to(root)),
                        "start_line": comment_block_start,
                        "end_line": comment_block_start + len(comment_lines) - 1,
                        "preview": preview,
                    }
                    results.append(result)

                comment_block_start = None
                comment_lines = []

        # Handle block at end of file
        if comment_block_start is not None and len(comment_lines) >= 3:
            preview = "\n".join(comment_lines)[:100]
            result = {
                "file_path": str(file_path.relative_to(root)),
                "start_line": comment_block_start,
                "end_line": comment_block_start + len(comment_lines) - 1,
                "preview": preview,
            }
            results.append(result)

    return results


def _looks_like_code(text: str) -> bool:
    """Heuristic to detect if commented text looks like code.

    Args:
        text: Text to analyze

    Returns:
        True if text appears to be code
    """
    # Patterns that suggest code rather than prose comments
    code_indicators = [
        r"[=;{}()\[\]]",  # Common code punctuation
        r"^\s*\w+\s*\(",  # Function calls
        r"^\s*(?:if|for|while|return|import|from|def|class|const|let|var)\s",  # Keywords
        r"^\s*#\s*include",  # C includes
        r"\w+\.\w+\(",  # Method calls
        r"^\s*\w+\s*=",  # Assignments
    ]

    for pattern in code_indicators:
        if re.search(pattern, text):
            return True
    return False


def generate_report(
    path: str = ".",
    include_blame: bool = False
) -> dict:
    """Generate full scan report.

    Args:
        path: Directory to scan
        include_blame: Whether to include git blame info

    Returns:
        Complete report dictionary
    """
    root = Path(path).resolve()

    todos = scan_todo_markers(path, include_blame)
    incomplete = scan_incomplete_implementations(path)
    feature_flags = scan_feature_flags(path)
    commented = scan_commented_code(path)

    # Count TODOs vs FIXMEs
    todo_count = sum(1 for t in todos if t["marker_type"] == "TODO")
    fixme_count = sum(1 for t in todos if t["marker_type"] == "FIXME")
    hack_count = sum(1 for t in todos if t["marker_type"] == "HACK")
    xxx_count = sum(1 for t in todos if t["marker_type"] == "XXX")
    other_count = len(todos) - todo_count - fixme_count - hack_count - xxx_count

    # Calculate hotspots
    file_counts: dict[str, int] = {}
    for item in todos + incomplete + feature_flags:
        fp = item["file_path"]
        file_counts[fp] = file_counts.get(fp, 0) + 1

    hotspots = sorted(
        [{"file": f, "issue_count": c} for f, c in file_counts.items()],
        key=lambda x: x["issue_count"],
        reverse=True
    )[:10]

    return {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "root_path": str(root),
        "summary": {
            "total_todos": todo_count,
            "total_fixmes": fixme_count,
            "total_hacks": hack_count,
            "total_xxx": xxx_count,
            "total_other_markers": other_count,
            "incomplete_implementations": len(incomplete),
            "feature_flags": len(feature_flags),
            "commented_blocks": len(commented),
        },
        "by_category": {
            "todos": todos,
            "incomplete": incomplete,
            "feature_flags": feature_flags,
            "commented_code": commented,
        },
        "hotspots": hotspots,
    }


def format_summary(report: dict) -> str:
    """Format report as human-readable summary.

    Args:
        report: Report dictionary

    Returns:
        Formatted summary string
    """
    lines = [
        "Code Pattern Scan Report",
        "=" * 50,
        f"Scanned: {report['root_path']}",
        f"Time: {report['scan_timestamp']}",
        "",
        "Summary",
        "-" * 30,
    ]

    s = report["summary"]
    lines.extend([
        f"  TODOs:       {s['total_todos']}",
        f"  FIXMEs:      {s['total_fixmes']}",
        f"  HACKs:       {s['total_hacks']}",
        f"  XXX:         {s['total_xxx']}",
        f"  Other:       {s['total_other_markers']}",
        f"  Incomplete:  {s['incomplete_implementations']}",
        f"  Flags:       {s['feature_flags']}",
        f"  Commented:   {s['commented_blocks']}",
        "",
    ])

    if report["hotspots"]:
        lines.append("Top Hotspots")
        lines.append("-" * 30)
        for h in report["hotspots"][:5]:
            lines.append(f"  {h['issue_count']:3d}  {h['file']}")
        lines.append("")

    # Show a few sample items
    todos = report["by_category"]["todos"]
    if todos:
        lines.append("Sample TODOs/FIXMEs")
        lines.append("-" * 30)
        for item in todos[:3]:
            lines.append(f"  [{item['marker_type']}] {item['file_path']}:{item['line_number']}")
            if item["content"]:
                lines.append(f"    {item['content'][:60]}")
        lines.append("")

    incomplete = report["by_category"]["incomplete"]
    if incomplete:
        lines.append("Sample Incomplete Implementations")
        lines.append("-" * 30)
        for item in incomplete[:3]:
            func = item["function_name"] or "(unknown)"
            lines.append(f"  {item['file_path']}:{item['line_number']} - {item['pattern_type']}")
            lines.append(f"    in function: {func}")
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scan codebase for work-in-progress patterns"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="summary",
        help="Output format (default: summary)"
    )
    parser.add_argument(
        "--include-blame",
        action="store_true",
        help="Include git blame info (slower)"
    )

    args = parser.parse_args()

    report = generate_report(args.path, args.include_blame)

    if args.output == "json":
        print(json.dumps(report, indent=2))
    else:
        print(format_summary(report))


if __name__ == "__main__":
    main()
