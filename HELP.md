# AudioForge Hilfe

## Dateiformate kurz

- **MP3**: verlustbehaftet, maximale Kompatibilität.
- **FLAC**: verlustfrei, ideal für Archiv und eigene Master.
- **WAV**: unkomprimiert, Studio/DAW, große Dateien.
- **OPUS**: modern, sehr effizient, kleine gute Dateien.
- **OGG/Vorbis**: offen, gut für Linux/Open-Source.
- **M4A/AAC**: Apple/Handy/Web, gute Alternative zu MP3.
- **ALAC**: Apple Lossless, verlustfrei im M4A-Container.
- **AIFF**: unkomprimiert, Studio/Apple-Workflows.

## Qualität

Standard ist **Beste Qualität**.

- MP3: LAME VBR q0
- FLAC: Compression Level 12, verlustfrei
- WAV/AIFF: 24 Bit PCM
- OPUS/AAC: 320 kbit/s
- OGG: Qualitätsstufe 10
- ALAC: verlustfrei

## Magic Presets

- **Aus**: keine Klangbearbeitung.
- **Magic 1**: sehr sanft.
- **Magic 2**: leichte Balance.
- **Magic 3**: Standard, etwas voller/breiter.
- **Magic 4**: wärmer/dichter.
- **Magic 5**: stärkste Politur.

## Analyse

Die Analyse nutzt FFmpeg `astats` und `volumedetect`, wertet Pegel/Headroom und Dateityp aus und setzt ein empfohlenes Magic-Preset.

## 16:9 Banner

Oben ist die Bildbox auf **16:9** eingestellt. Ersetze `assets/logo.png` durch ein eigenes 16:9-Bild.

## Layout-Hinweis ab v7

Der 16:9-Banner steht jetzt oben rechts über dem Ausgabe-Bereich. Die Dateiauswahl beginnt dadurch links direkt oben im Hauptbereich.

Empfohlenes eigenes Banner:

```text
assets/logo.png
16:9, z.B. 1280 × 720 px oder 1920 × 1080 px
PNG
```

AudioForge skaliert das Bild in eine kompakte Box über dem Ausgabe-Frame.
