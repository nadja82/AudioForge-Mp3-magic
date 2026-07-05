from __future__ import annotations
import io
from pathlib import Path
from typing import Any
from PIL import Image
from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, COMM, ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TRCK, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

TagDict = dict[str, str]

def cleaned_tags(tags: TagDict) -> TagDict:
    return {k: str(v).strip() for k, v in tags.items() if str(v).strip()}

def prepare_cover_bytes(cover_path: Path, max_size: int = 1000) -> tuple[bytes, str]:
    with Image.open(cover_path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO(); image.save(buf, format="JPEG", quality=90, optimize=True)
        return buf.getvalue(), "image/jpeg"

def write_metadata(path: Path, tags: TagDict, cover_path: Path | None = None) -> list[str]:
    warnings: list[str] = []
    tags = cleaned_tags(tags)
    suffix = path.suffix.lower()
    try:
        if suffix == ".mp3": _write_mp3(path, tags, cover_path)
        elif suffix == ".flac": _write_flac(path, tags, cover_path)
        elif suffix in {".m4a", ".mp4"}: _write_mp4(path, tags, cover_path)
        elif suffix == ".ogg":
            _write_ogg(path, tags, OggVorbis)
            if cover_path: warnings.append("Cover für OGG/Vorbis wird in dieser MVP-Version nicht eingebettet.")
        elif suffix == ".opus":
            _write_ogg(path, tags, OggOpus)
            if cover_path: warnings.append("Cover für OPUS wird in dieser MVP-Version nicht eingebettet.")
        else:
            _write_easy(path, tags)
            if cover_path: warnings.append(f"Cover für {suffix.upper().lstrip('.')} ist nicht zuverlässig unterstützt.")
    except Exception as exc:
        warnings.append(f"Metadaten konnten nicht vollständig geschrieben werden: {exc}")
    return warnings

def _write_easy(path: Path, tags: TagDict) -> None:
    audio = MutagenFile(path, easy=True)
    if not audio: return
    if audio.tags is None: audio.add_tags()
    for k, v in tags.items(): audio.tags[k] = [v]
    audio.save()

def _write_mp3(path: Path, tags: TagDict, cover_path: Path | None) -> None:
    audio = MP3(path)
    try: id3 = ID3(path)
    except ID3NoHeaderError: id3 = ID3()
    mapping: dict[str, Any] = {"title": TIT2, "artist": TPE1, "album": TALB, "albumartist": TPE2, "genre": TCON, "date": TDRC, "tracknumber": TRCK}
    frame_ids = {TIT2:"TIT2", TPE1:"TPE1", TALB:"TALB", TPE2:"TPE2", TCON:"TCON", TDRC:"TDRC", TRCK:"TRCK"}
    for name, cls in mapping.items():
        if value := tags.get(name):
            id3.delall(frame_ids[cls]); id3.add(cls(encoding=3, text=value))
    if comment := tags.get("comment"):
        id3.delall("COMM"); id3.add(COMM(encoding=3, lang="eng", desc="", text=comment))
    if cover_path:
        image_bytes, mime = prepare_cover_bytes(cover_path)
        id3.delall("APIC"); id3.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=image_bytes))
    audio.tags = id3; audio.save()

def _write_flac(path: Path, tags: TagDict, cover_path: Path | None) -> None:
    audio = FLAC(path)
    for k, v in tags.items(): audio[k] = v
    if cover_path:
        image_bytes, mime = prepare_cover_bytes(cover_path)
        pic = Picture(); pic.type = 3; pic.mime = mime; pic.desc = "Cover"; pic.data = image_bytes
        audio.clear_pictures(); audio.add_picture(pic)
    audio.save()

def _write_mp4(path: Path, tags: TagDict, cover_path: Path | None) -> None:
    audio = MP4(path); mp4_tags = audio.tags or {}
    mapping = {"title":"\xa9nam", "artist":"\xa9ART", "album":"\xa9alb", "albumartist":"aART", "genre":"\xa9gen", "date":"\xa9day", "comment":"\xa9cmt"}
    for src, dst in mapping.items():
        if value := tags.get(src): mp4_tags[dst] = [value]
    if track := tags.get("tracknumber"):
        try: mp4_tags["trkn"] = [(int(track.split("/")[0].strip()), 0)]
        except ValueError: pass
    if cover_path:
        image_bytes, _ = prepare_cover_bytes(cover_path)
        mp4_tags["covr"] = [MP4Cover(image_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
    audio.tags = mp4_tags; audio.save()

def _write_ogg(path: Path, tags: TagDict, cls: Any) -> None:
    audio = cls(path)
    for k, v in tags.items(): audio[k] = [v]
    audio.save()
