# AudioForge MVP v6

**Written by Daniela Kamp**  
**Free MIT License · 2026**

AudioForge ist ein Linux-Desktop-Audio-Konverter mit PySide6, FFmpeg, Magic-Presets, Normalisierung, Metadaten und Cover-Bearbeitung.

## Neu in v6

- Die obere Bildbox ist jetzt fest auf **16:9** eingestellt.
- Standardgröße der Bannerbox: **640 × 360 px**.
- Die Datei `assets/logo.png` wird dort angezeigt.
- Am besten ersetzt du `assets/logo.png` durch ein eigenes 16:9-Bild, z.B. 1280×720 oder 1920×1080.

## Installation

```bash
chmod +x install.sh
./install.sh
./run.sh
```

## Funktionen

- WAV, FLAC, MP3, M4A/AAC, OGG, OPUS, AIFF und WavPack als Eingabe
- Ausgabe nach MP3, FLAC, WAV, OPUS, OGG, M4A/AAC, ALAC und AIFF
- Standardqualität: **Beste Qualität**
- Ausgabeordner wählbar
- Metadaten bearbeiten/speichern
- Cover wählen und einbetten
- Magic 1–5 Presets
- Analysefunktion empfiehlt ein Magic-Preset
- 30s Vorschau
- Live-FFmpeg-Log

## Banner

Die App nutzt:

```text
assets/logo.png
```

Empfohlen:

```text
16:9 PNG
1280 x 720 px
oder 1920 x 1080 px
```

Die Box selbst ist 16:9, damit dein Logo ohne Verzerrung passt.

## Änderung in v7

- Der 16:9-Banner (`assets/logo.png`) steht jetzt oben rechts direkt über dem **Ausgabe**-Frame.
- Die globale obere Banner-Zeile wurde entfernt, dadurch rutscht die Dateiauswahl links direkt nach oben.
- Die Bannerbox ist jetzt kompakter auf den rechten Einstellungsbereich skaliert: 420 × 236 px im 16:9-Verhältnis.
