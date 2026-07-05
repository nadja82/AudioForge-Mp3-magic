"""Magic audio presets for AudioForge.

v9 uses a safer gain structure:

    pre-headroom -> Magic EQ/dynamics/stereo -> stage limiter
    -> optional loudness normalization -> final limiter

The pre-headroom is intentionally stronger than before because FFmpeg's EQ
filters can report internal channel clipping before a final limiter can catch
peaks. Lowering first is safer than trying to fix the peak after the EQ.
"""
from __future__ import annotations

PRESETS = {
    "Aus": "",
    "Magic 1": "highpass=f=25,lowpass=f=19000,acompressor=threshold=-24dB:ratio=1.18:attack=40:release=340",
    "Magic 2": "highpass=f=30,bass=g=0.25:f=90,treble=g=-0.35:f=10000,acompressor=threshold=-23dB:ratio=1.28:attack=34:release=310",
    "Magic 3": "highpass=f=30,bass=g=0.40:f=85,treble=g=-0.55:f=11000,acompressor=threshold=-22dB:ratio=1.42:attack=30:release=290,stereowiden=delay=9:feedback=0.05:crossfeed=0.14:drymix=0.93",
    "Magic 4": "highpass=f=35,bass=g=0.55:f=80,treble=g=-0.75:f=9500,acompressor=threshold=-21dB:ratio=1.62:attack=26:release=330,stereowiden=delay=12:feedback=0.07:crossfeed=0.16:drymix=0.90",
    "Magic 5": "highpass=f=35,bass=g=0.70:f=75,equalizer=f=2500:t=q:w=1.2:g=-0.55,treble=g=-1.00:f=10000,acompressor=threshold=-20dB:ratio=1.85:attack=22:release=350,stereowiden=delay=14:feedback=0.08:crossfeed=0.18:drymix=0.88",
}

PRESET_DESCRIPTIONS = {
    "Aus": "Keine Klangbearbeitung. Nur Konvertierung und, falls aktiv, Normalisierung.",
    "Magic 1": "Sehr leichte Reinigung: Subbass-Rumpeln entfernen, sanfter Kompressor, fast unsichtbar.",
    "Magic 2": "Soft Balance: minimal wärmer, minimal glattere Höhen, leichte Dynamik-Kontrolle.",
    "Magic 3": "Wider & Smoother: etwas voller, etwas breiter, guter Standard für normales Material.",
    "Magic 4": "Warm Master: hörbar runder, dichter und etwas wärmer, aber noch fein dosiert.",
    "Magic 5": "Full Polish: stärkstes Magic-Preset mit mehr Zusammenhalt und Breite, aber mit Clip-Schutz.",
}

# Stronger pre-headroom per preset. This is the most important anti-clipping step.
PRE_HEADROOM_VOLUME = {
    "Magic 1": 0.82,
    "Magic 2": 0.74,
    "Magic 3": 0.68,
    "Magic 4": 0.62,
    "Magic 5": 0.56,
}

# Gentle post-makeup when loudnorm is disabled. This keeps Magic from becoming
# too quiet but stays below a final limiter.
POST_MAKEUP_VOLUME = {
    "Magic 1": 1.02,
    "Magic 2": 1.06,
    "Magic 3": 1.10,
    "Magic 4": 1.14,
    "Magic 5": 1.18,
}

NORMALIZE_FILTER = "loudnorm=I=-14:TP=-1.5:LRA=11"
STAGE_LIMITER = "alimiter=limit=0.90"
FINAL_LIMITER = "alimiter=limit=0.96"


def _db_to_linear(db: float) -> float:
    return 10 ** (db / 20)


def build_filter_chain(preset_name: str, normalize: bool, extra_headroom_db: float = 0.0) -> str:
    """Return an FFmpeg -af filter chain.

    extra_headroom_db is used by the automatic clipping guard. If FFmpeg still
    reports channel clipping, AudioForge can retry the same job with additional
    input attenuation before the Magic chain.
    """
    filters: list[str] = []
    preset = PRESETS.get(preset_name, "")

    if preset:
        pre = PRE_HEADROOM_VOLUME.get(preset_name, 0.70) * _db_to_linear(-abs(extra_headroom_db))
        filters.append(f"volume={pre:.4f}")
        filters.append(preset)
        filters.append(STAGE_LIMITER)
        if normalize:
            filters.append(NORMALIZE_FILTER)
        else:
            makeup = POST_MAKEUP_VOLUME.get(preset_name, 1.0)
            filters.append(f"volume={makeup:.3f}")
        filters.append(FINAL_LIMITER)
    elif normalize:
        filters.append(NORMALIZE_FILTER)
        filters.append(FINAL_LIMITER)

    return ",".join(filters)
