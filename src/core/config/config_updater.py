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
    
    in_matching_section = False
    matching_indent = ""
    updated_keys = set()
    
    new_lines = []
    
    for line in lines:
        if line.strip().startswith("matching:"):
            in_matching_section = True
            new_lines.append(line)
            continue
            
        if in_matching_section:
            # Check if we left the section
            if line.strip() and not line.startswith(" ") and not line.startswith("\t") and not line.startswith("#"):
                # We left the section! Inject any missing keys before leaving
                missing_keys = set(new_flags.keys()) - updated_keys
                for key in missing_keys:
                    val_str = "true" if new_flags[key] else "false"
                    indent = matching_indent if matching_indent else "  "
                    new_lines.append(f"{indent}{key}: {val_str}")
                in_matching_section = False
                new_lines.append(line)
                continue
                
            # If it's a key-value pair in matching section
            match = re.match(r"^(\s+)([\w_]+)\s*:\s*(true|false|True|False)(.*)$", line)
            if match:
                indent, key, old_val, rest = match.groups()
                matching_indent = indent
                if key in new_flags:
                    val_str = "true" if new_flags[key] else "false"
                    new_lines.append(f"{indent}{key}: {val_str}{rest}")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    # If we reached the end and are still in matching section
    if in_matching_section:
        missing_keys = set(new_flags.keys()) - updated_keys
        for key in missing_keys:
            val_str = "true" if new_flags[key] else "false"
            indent = matching_indent if matching_indent else "  "
            new_lines.append(f"{indent}{key}: {val_str}")

    path.write_text("\n".join(new_lines), encoding="utf-8")
