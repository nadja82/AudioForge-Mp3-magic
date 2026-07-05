from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class FormatSpec:
    name: str
    extension: str
    codec_args: list[str]
    notes: str = ""

FORMAT_SPECS: dict[str, dict[str, FormatSpec]] = {
    "MP3": {
        "Beste Qualität": FormatSpec("MP3", ".mp3", ["-codec:a", "libmp3lame", "-q:a", "0"]),
        "Sehr hoch": FormatSpec("MP3", ".mp3", ["-codec:a", "libmp3lame", "-q:a", "0"]),
        "Hoch": FormatSpec("MP3", ".mp3", ["-codec:a", "libmp3lame", "-q:a", "2"]),
        "Standard": FormatSpec("MP3", ".mp3", ["-codec:a", "libmp3lame", "-q:a", "4"]),
        "320 kbit/s": FormatSpec("MP3", ".mp3", ["-codec:a", "libmp3lame", "-b:a", "320k"]),
    },
    "FLAC": {
        "Beste Qualität": FormatSpec("FLAC", ".flac", ["-codec:a", "flac", "-compression_level", "12"]),
        "Sehr hoch": FormatSpec("FLAC", ".flac", ["-codec:a", "flac", "-compression_level", "12"]),
        "Hoch": FormatSpec("FLAC", ".flac", ["-codec:a", "flac", "-compression_level", "8"]),
        "Standard": FormatSpec("FLAC", ".flac", ["-codec:a", "flac", "-compression_level", "5"]),
        "320 kbit/s": FormatSpec("FLAC", ".flac", ["-codec:a", "flac", "-compression_level", "8"]),
    },
    "WAV": {
        "Beste Qualität": FormatSpec("WAV", ".wav", ["-codec:a", "pcm_s24le"]),
        "Sehr hoch": FormatSpec("WAV", ".wav", ["-codec:a", "pcm_s24le"]),
        "Hoch": FormatSpec("WAV", ".wav", ["-codec:a", "pcm_s24le"]),
        "Standard": FormatSpec("WAV", ".wav", ["-codec:a", "pcm_s16le"]),
        "320 kbit/s": FormatSpec("WAV", ".wav", ["-codec:a", "pcm_s16le"]),
    },
    "OPUS": {
        "Beste Qualität": FormatSpec("OPUS", ".opus", ["-codec:a", "libopus", "-b:a", "320k"]),
        "Sehr hoch": FormatSpec("OPUS", ".opus", ["-codec:a", "libopus", "-b:a", "256k"]),
        "Hoch": FormatSpec("OPUS", ".opus", ["-codec:a", "libopus", "-b:a", "160k"]),
        "Standard": FormatSpec("OPUS", ".opus", ["-codec:a", "libopus", "-b:a", "128k"]),
        "320 kbit/s": FormatSpec("OPUS", ".opus", ["-codec:a", "libopus", "-b:a", "320k"]),
    },
    "OGG": {
        "Beste Qualität": FormatSpec("OGG", ".ogg", ["-codec:a", "libvorbis", "-q:a", "10"]),
        "Sehr hoch": FormatSpec("OGG", ".ogg", ["-codec:a", "libvorbis", "-q:a", "8"]),
        "Hoch": FormatSpec("OGG", ".ogg", ["-codec:a", "libvorbis", "-q:a", "6"]),
        "Standard": FormatSpec("OGG", ".ogg", ["-codec:a", "libvorbis", "-q:a", "5"]),
        "320 kbit/s": FormatSpec("OGG", ".ogg", ["-codec:a", "libvorbis", "-q:a", "9"]),
    },
    "M4A/AAC": {
        "Beste Qualität": FormatSpec("M4A/AAC", ".m4a", ["-codec:a", "aac", "-b:a", "320k"]),
        "Sehr hoch": FormatSpec("M4A/AAC", ".m4a", ["-codec:a", "aac", "-b:a", "320k"]),
        "Hoch": FormatSpec("M4A/AAC", ".m4a", ["-codec:a", "aac", "-b:a", "256k"]),
        "Standard": FormatSpec("M4A/AAC", ".m4a", ["-codec:a", "aac", "-b:a", "192k"]),
        "320 kbit/s": FormatSpec("M4A/AAC", ".m4a", ["-codec:a", "aac", "-b:a", "320k"]),
    },
    "ALAC": {q: FormatSpec("ALAC", ".m4a", ["-codec:a", "alac"]) for q in ["Beste Qualität", "Sehr hoch", "Hoch", "Standard", "320 kbit/s"]},
    "AIFF": {
        "Beste Qualität": FormatSpec("AIFF", ".aiff", ["-codec:a", "pcm_s24be"]),
        "Sehr hoch": FormatSpec("AIFF", ".aiff", ["-codec:a", "pcm_s24be"]),
        "Hoch": FormatSpec("AIFF", ".aiff", ["-codec:a", "pcm_s24be"]),
        "Standard": FormatSpec("AIFF", ".aiff", ["-codec:a", "pcm_s16be"]),
        "320 kbit/s": FormatSpec("AIFF", ".aiff", ["-codec:a", "pcm_s16be"]),
    },
}
DEFAULT_QUALITY = "Beste Qualität"

def get_format_spec(format_name: str, quality_name: str) -> FormatSpec:
    return FORMAT_SPECS[format_name].get(quality_name) or FORMAT_SPECS[format_name][DEFAULT_QUALITY]

def output_formats() -> list[str]:
    return list(FORMAT_SPECS.keys())

def quality_options() -> list[str]:
    return [DEFAULT_QUALITY, "Sehr hoch", "Hoch", "Standard", "320 kbit/s"]
