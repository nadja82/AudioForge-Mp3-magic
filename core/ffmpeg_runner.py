from __future__ import annotations
from pathlib import Path
from .formats import get_format_spec
from .presets import build_filter_chain


def build_ffmpeg_args(
    source: Path,
    output: Path,
    format_name: str,
    quality_name: str,
    preset_name: str,
    normalize: bool,
    preserve_metadata: bool = True,
    overwrite: bool = True,
    preview_seconds: int | None = None,
    extra_headroom_db: float = 0.0,
) -> list[str]:
    spec = get_format_spec(format_name, quality_name)
    args: list[str] = ["-hide_banner", "-y" if overwrite else "-n", "-i", str(source), "-map", "0:a:0", "-vn"]
    args += ["-map_metadata", "0" if preserve_metadata else "-1"]
    filter_chain = build_filter_chain(preset_name, normalize, extra_headroom_db=extra_headroom_db)
    if filter_chain:
        args += ["-af", filter_chain]
    if preview_seconds:
        args += ["-t", str(preview_seconds)]
    args += spec.codec_args
    args += ["-progress", "pipe:1", "-nostats", str(output)]
    return args
