from __future__ import annotations
import json, subprocess
from pathlib import Path
from typing import Any
from mutagen import File as MutagenFile

SUPPORTED_EXTENSIONS = {".wav", ".wave", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".aiff", ".aif", ".wv"}

def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS

def probe_duration(path: Path) -> float:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], check=True, capture_output=True, text=True)
        data: dict[str, Any] = json.loads(result.stdout or "{}")
        return float(data.get("format", {}).get("duration") or 0.0)
    except Exception:
        return 0.0

def probe_format_name(path: Path) -> str:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=format_name", "-of", "json", str(path)], check=True, capture_output=True, text=True)
        data: dict[str, Any] = json.loads(result.stdout or "{}")
        return str(data.get("format", {}).get("format_name") or path.suffix.upper().lstrip("."))
    except Exception:
        return path.suffix.upper().lstrip(".")

def read_basic_tags(path: Path) -> dict[str, str]:
    result = {"title":"", "artist":"", "album":"", "albumartist":"", "genre":"", "date":"", "tracknumber":"", "comment":""}
    try:
        audio = MutagenFile(path, easy=True)
        if not audio or not audio.tags:
            return result
        for key in result:
            value = audio.tags.get(key)
            if isinstance(value, list) and value:
                result[key] = str(value[0])
            elif value:
                result[key] = str(value)
    except Exception:
        pass
    return result

def format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "--:--"
    total = int(seconds + 0.5)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:d}:{sec:02d}"
