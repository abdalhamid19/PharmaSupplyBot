"""Safe configuration updater that preserves YAML comments and structure."""

import re
from pathlib import Path

def update_matching_flags_in_config(config_path: Path | str, new_flags: dict[str, bool]) -> None:
    """Safely update or add boolean matching flags in the config file."""
    path = Path(config_path)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines, _ = _process_config_lines(lines, new_flags)
    path.write_text("\n".join(new_lines), encoding="utf-8")


def _process_config_lines(lines: list[str], new_flags: dict[str, bool]):
    """Process config lines and update matching flags."""
    in_matching_section, matching_indent, updated_keys, new_lines = False, "", set(), []
    
    for line in lines:
        if line.strip().startswith("matching:"):
            in_matching_section = True
            new_lines.append(line)
        elif in_matching_section:
            in_matching_section, matching_indent = _process_matching_section(line, new_flags, updated_keys, new_lines, matching_indent)
        else:
            new_lines.append(line)
    
    if in_matching_section:
        new_lines.extend(_inject_missing_keys(new_flags, updated_keys, matching_indent))
    
    return new_lines, updated_keys


def _process_matching_section(line, new_flags, updated_keys, new_lines, matching_indent):
    """Process a line within matching section."""
    if _is_section_end(line):
        new_lines.extend(_inject_missing_keys(new_flags, updated_keys, matching_indent))
        new_lines.append(line)
        return False, matching_indent
    
    line, indent, updated = _process_matching_line(line, new_flags, updated_keys)
    new_lines.append(line)
    if indent:
        matching_indent = indent
    return True, matching_indent


def _is_section_end(line: str) -> bool:
    """Check if line marks end of section."""
    return (
        line.strip() and not line.startswith(" ") and
        not line.startswith("\t") and not line.startswith("#")
    )


def _process_matching_line(line: str, new_flags: dict, updated_keys: set):
    """Process a line in matching section."""
    match = re.match(r"^(\s+)([\w_]+)\s*:\s*(true|false|True|False)(.*)$", line)
    if match:
        indent, key, old_val, rest = match.groups()
        if key in new_flags:
            val_str = "true" if new_flags[key] else "false"
            updated_keys.add(key)
            return f"{indent}{key}: {val_str}{rest}", indent, True
        return line, indent, False
    return line, None, False


def _inject_missing_keys(new_flags: dict, updated_keys: set, indent: str) -> list[str]:
    """Inject missing keys at end of section."""
    missing_keys = set(new_flags.keys()) - updated_keys
    indent = indent if indent else "  "
    return [f"{indent}{key}: {'true' if new_flags[key] else 'false'}" for key in missing_keys]
