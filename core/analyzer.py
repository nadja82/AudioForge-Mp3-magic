from __future__ import annotations
from dataclasses import dataclass
import re
from pathlib import Path

@dataclass
class AnalysisResult:
    mean_volume_db: float | None = None
    max_volume_db: float | None = None
    rms_level_db: float | None = None
    peak_level_db: float | None = None
    recommendation: str = "Magic 3"
    reason: str = "Allround-Empfehlung."

def _last_float(pattern: str, text: str) -> float | None:
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    if not matches: return None
    try: return float(matches[-1])
    except ValueError: return None

def parse_analysis_output(text: str, source: Path | None = None) -> AnalysisResult:
    r = AnalysisResult()
    r.mean_volume_db = _last_float(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
    r.max_volume_db = _last_float(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
    r.rms_level_db = _last_float(r"RMS level dB:\s*(-?\d+(?:\.\d+)?)", text)
    r.peak_level_db = _last_float(r"Peak level dB:\s*(-?\d+(?:\.\d+)?)", text)
    mean = r.mean_volume_db if r.mean_volume_db is not None else r.rms_level_db
    peak = r.max_volume_db if r.max_volume_db is not None else r.peak_level_db
    suffix = source.suffix.lower() if source else ""
    if peak is not None and peak >= -0.5:
        r.recommendation = "Magic 1"; r.reason = "Die Datei ist bereits sehr nah an 0 dB. Magic 1 bleibt am sichersten."; return r
    if suffix in {".mp3", ".aac", ".m4a", ".ogg", ".opus"}:
        r.recommendation = "Magic 3" if mean is not None and mean < -24 and (peak is None or peak < -5) else "Magic 2"
        r.reason = "Verlustbehaftete Quellen profitieren meist von sanfter Balance statt starker Bearbeitung."
        return r
    if mean is not None and peak is not None:
        if mean < -30 and peak < -8:
            r.recommendation = "Magic 5"; r.reason = "Sehr leise Datei mit viel Headroom. Magic 5 kann mehr Dichte geben."; return r
        if mean < -24 and peak < -4:
            r.recommendation = "Magic 4"; r.reason = "Eher leise/dynamisch. Magic 4 gibt Wärme, Kontrolle und Breite."; return r
        if mean > -16 or peak > -1.5:
            r.recommendation = "Magic 2"; r.reason = "Schon recht laut. Magic 2 poliert sanft."; return r
    r.recommendation = "Magic 3"; r.reason = "Normales Material. Magic 3 ist der ausgewogene Standard."
    return r

def format_analysis_summary(r: AnalysisResult) -> str:
    fmt = lambda v: "n/a" if v is None else f"{v:.1f} dB"
    return f"Empfehlung: {r.recommendation}\n\nMean Volume: {fmt(r.mean_volume_db)}\nMax Volume: {fmt(r.max_volume_db)}\nRMS Level: {fmt(r.rms_level_db)}\nPeak Level: {fmt(r.peak_level_db)}\n\nWarum: {r.reason}"
