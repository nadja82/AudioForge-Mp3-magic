from __future__ import annotations
from pathlib import Path

def unique_path(path: Path) -> Path:
    if not path.exists(): return path
    parent, stem, suffix = path.parent, path.stem, path.suffix
    i = 1
    while True:
        candidate = parent / f"{stem}_{i:03d}{suffix}"
        if not candidate.exists(): return candidate
        i += 1

def build_output_path(source: Path, base_output_dir: Path, extension: str, preserve_structure: bool=False, common_root: Path|None=None, auto_number: bool=True) -> Path:
    if preserve_structure and common_root:
        try: target_dir = base_output_dir / source.parent.relative_to(common_root)
        except ValueError: target_dir = base_output_dir
    else:
        target_dir = base_output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / f"{source.stem}{extension}"
    return unique_path(output) if auto_number else output
