from __future__ import annotations
import os, re, shutil, subprocess
from dataclasses import dataclass, field
from pathlib import Path
from PySide6.QtCore import QProcess, QSettings, Qt, QSize
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QPixmap, QImage
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from core.analyzer import format_analysis_summary, parse_analysis_output
from core.ffmpeg_runner import build_ffmpeg_args
from core.ffprobe import format_duration, is_audio_file, probe_duration, probe_format_name, read_basic_tags
from core.formats import DEFAULT_QUALITY, get_format_spec, output_formats, quality_options
from core.metadata import write_metadata
from core.path_builder import build_output_path
from core.presets import PRESETS, PRESET_DESCRIPTIONS
from gui.metadata_dialog import MetadataDialog
from gui.themes import DEFAULT_THEME, THEMES, get_stylesheet

@dataclass
class AudioJob:
    source: Path
    duration: float
    format_name: str
    tags: dict[str, str]
    cover_path: Path | None = None
    output_path: Path | None = None
    status: str = "wartet"
    progress: int = 0
    warnings: list[str] = field(default_factory=list)
    clip_retry_done: bool = False

class MainWindow(QMainWindow):
    BANNER_WIDTH = 420
    BANNER_HEIGHT = 236  # 16:9, passend über dem Ausgabe-Frame

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioForge")
        self.settings = QSettings("DanielaKamp", "AudioForge")
        self.current_theme = str(self.settings.value("theme", DEFAULT_THEME))
        # Start smaller for notebook displays / HiDPI scaling. The right settings
        # column is scrollable, so the app remains usable on compact screens.
        self.resize(1040, 680)
        self.setMinimumSize(820, 520)
        self.setAcceptDrops(True)
        self.jobs: list[AudioJob] = []
        self.current_index = -1
        self.current_process: QProcess | None = None
        self.current_preview = False
        self.output_dir = Path(str(self.settings.value("output_dir", str(Path.home() / "Music" / "AudioForge"))))
        self.common_root: Path | None = None
        self._process_mode: str | None = None
        self._analysis_stderr: list[str] = []
        self._current_stderr: list[str] = []
        self._queue_settings: dict[str, object] = {}
        self._build_ui(); self._apply_style(); self._refresh_buttons(); self._check_tools()

    def _build_ui(self) -> None:
        central = QWidget(); root = QVBoxLayout(central); self.setCentralWidget(central)
        splitter = QSplitter(Qt.Horizontal); root.addWidget(splitter, 1)
        left = QWidget(); left_layout = QVBoxLayout(left); splitter.addWidget(left)
        file_buttons = QHBoxLayout()
        self.add_files_btn = QPushButton("+ Dateien"); self.add_folder_btn = QPushButton("+ Ordner"); self.remove_btn = QPushButton("Entfernen"); self.clear_btn = QPushButton("Liste leeren")
        for b in [self.add_files_btn,self.add_folder_btn,self.remove_btn,self.clear_btn]: file_buttons.addWidget(b)
        left_layout.addLayout(file_buttons)
        self.table = QTableWidget(0,8); self.table.setHorizontalHeaderLabels(["Cover","Datei","Titel","Artist","Album","Format","Dauer","Status"])
        self.table.verticalHeader().setVisible(False); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.ExtendedSelection); self.table.setAlternatingRowColors(True)
        for i in [0,5,6,7]: self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        for i in [1,2,3,4]: self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch if i in [1,2] else QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(180)
        left_layout.addWidget(self.table, 1)
        progress_box = QGroupBox("Fortschritt"); progress_layout = QFormLayout(progress_box); self.current_progress = QProgressBar(); self.total_progress = QProgressBar(); progress_layout.addRow("Aktuelle Datei:", self.current_progress); progress_layout.addRow("Gesamt:", self.total_progress); left_layout.addWidget(progress_box)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(1000); self.log.setPlaceholderText("FFmpeg-Log…"); self.log.setMinimumHeight(110); left_layout.addWidget(self.log, 1)

        right = QWidget(); right_layout = QVBoxLayout(right)
        right_scroll = QScrollArea(); right_scroll.setWidgetResizable(True); right_scroll.setObjectName("RightScrollArea")
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded); right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setFrameShape(QFrame.NoFrame); right_scroll.setWidget(right)
        splitter.addWidget(right_scroll); splitter.setSizes([720,420])
        self.logo_label = QLabel(); self.logo_label.setObjectName("HeaderBanner")
        self.logo_label.setFixedSize(self.BANNER_WIDTH, self.BANNER_HEIGHT)
        self.logo_label.setAlignment(Qt.AlignCenter); self.logo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._configure_header_logo_transparency()
        self._header_logo_pixmap: QPixmap | None = None; self._load_header_logo()
        right_layout.addWidget(self.logo_label, 0, Qt.AlignHCenter | Qt.AlignTop)
        layout_box = QGroupBox("Layout")
        layout_form = QFormLayout(layout_box)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(self.current_theme if self.current_theme in THEMES else DEFAULT_THEME)
        layout_form.addRow("Farbschema:", self.theme_combo)
        right_layout.addWidget(layout_box)
        output_box = QGroupBox("Ausgabe"); output_layout = QGridLayout(output_box)
        self.format_combo = QComboBox(); self.format_combo.addItems(output_formats()); self.format_combo.setCurrentText("MP3")
        self.quality_combo = QComboBox(); self.quality_combo.addItems(quality_options()); self.quality_combo.setCurrentText(DEFAULT_QUALITY)
        self.output_dir_edit = QLineEdit(str(self.output_dir)); self.output_dir_edit.setReadOnly(True); self.choose_output_btn = QPushButton("Wählen"); self.open_output_btn = QPushButton("Öffnen")
        self.preserve_structure_cb = QCheckBox("Ordnerstruktur beibehalten"); self.auto_number_cb = QCheckBox("Bei vorhandener Datei Nummer anhängen"); self.auto_number_cb.setChecked(True); self.keep_metadata_cb = QCheckBox("Original-Metadaten übernehmen"); self.keep_metadata_cb.setChecked(True)
        output_layout.addWidget(QLabel("Format:"),0,0); output_layout.addWidget(self.format_combo,0,1,1,2); output_layout.addWidget(QLabel("Qualität:"),1,0); output_layout.addWidget(self.quality_combo,1,1,1,2); output_layout.addWidget(QLabel("Ausgabeordner:"),2,0); output_layout.addWidget(self.output_dir_edit,2,1); output_layout.addWidget(self.choose_output_btn,2,2); output_layout.addWidget(self.open_output_btn,3,2); output_layout.addWidget(self.preserve_structure_cb,4,0,1,3); output_layout.addWidget(self.auto_number_cb,5,0,1,3); output_layout.addWidget(self.keep_metadata_cb,6,0,1,3); right_layout.addWidget(output_box)
        sound_box = QGroupBox("Sound"); sound_layout = QFormLayout(sound_box)
        self.normalize_cb = QCheckBox("Lautstärke normalisieren (-14 LUFS)"); self.normalize_cb.setChecked(True); self.preset_combo = QComboBox(); self.preset_combo.addItems(list(PRESETS.keys())); self.preset_combo.setCurrentText("Magic 3")
        self.analyze_btn = QPushButton("Analysieren & Magic empfehlen"); self.apply_analysis_cb = QCheckBox("Empfehlung automatisch übernehmen"); self.apply_analysis_cb.setChecked(False); self.analysis_result_label = QLabel("Noch keine Analyse."); self.analysis_result_label.setWordWrap(True); self.analysis_result_label.setObjectName("MutedLabel")
        sound_layout.addRow(self.normalize_cb); sound_layout.addRow("Magic-Preset:", self.preset_combo); sound_layout.addRow(self.analyze_btn); sound_layout.addRow(self.apply_analysis_cb); sound_layout.addRow("Analyse:", self.analysis_result_label); right_layout.addWidget(sound_box)
        meta_box = QGroupBox("Metadaten & Cover"); meta_layout = QVBoxLayout(meta_box); meta_buttons = QGridLayout()
        self.edit_meta_btn = QPushButton("Metadaten bearbeiten"); self.save_meta_btn = QPushButton("Metadaten speichern"); self.tags_from_filename_btn = QPushButton("Tags aus Dateiname"); self.cover_btn = QPushButton("Cover wählen"); self.cover_all_btn = QPushButton("Cover auf alle"); self.cover_remove_btn = QPushButton("Cover entfernen")
        meta_buttons.addWidget(self.edit_meta_btn,0,0,1,2); meta_buttons.addWidget(self.save_meta_btn,1,0,1,2); meta_buttons.addWidget(self.tags_from_filename_btn,2,0,1,2); meta_buttons.addWidget(self.cover_btn,3,0); meta_buttons.addWidget(self.cover_all_btn,3,1); meta_buttons.addWidget(self.cover_remove_btn,4,0,1,2); meta_layout.addLayout(meta_buttons)
        self.cover_preview = QLabel("Kein Cover"); self.cover_preview.setAlignment(Qt.AlignCenter); self.cover_preview.setFixedHeight(160); self.cover_preview.setObjectName("CoverPreview"); meta_layout.addWidget(self.cover_preview); right_layout.addWidget(meta_box)
        action_box = QGroupBox("Aktion"); action_layout = QVBoxLayout(action_box); self.preview_btn = QPushButton("30s Vorschau"); self.convert_btn = QPushButton("Konvertieren"); self.stop_btn = QPushButton("Stop"); self.convert_btn.setObjectName("PrimaryButton"); action_layout.addWidget(self.preview_btn); action_layout.addWidget(self.convert_btn); action_layout.addWidget(self.stop_btn); right_layout.addWidget(action_box); right_layout.addStretch(1)
        self.status_label = QLabel("Bereit."); root.addWidget(self.status_label)

        self.add_files_btn.clicked.connect(self.add_files); self.add_folder_btn.clicked.connect(self.add_folder); self.remove_btn.clicked.connect(self.remove_selected); self.clear_btn.clicked.connect(self.clear_jobs); self.choose_output_btn.clicked.connect(self.choose_output_dir); self.open_output_btn.clicked.connect(self.open_output_dir); self.edit_meta_btn.clicked.connect(self.edit_metadata); self.save_meta_btn.clicked.connect(self.save_metadata_to_sources); self.tags_from_filename_btn.clicked.connect(self.tags_from_filename); self.cover_btn.clicked.connect(self.choose_cover); self.cover_all_btn.clicked.connect(self.cover_to_all); self.cover_remove_btn.clicked.connect(self.remove_cover); self.analyze_btn.clicked.connect(self.analyze_selected); self.preview_btn.clicked.connect(self.make_preview); self.convert_btn.clicked.connect(self.start_conversion); self.stop_btn.clicked.connect(self.stop_conversion); self.table.itemSelectionChanged.connect(self.update_cover_preview); self.table.itemSelectionChanged.connect(self._refresh_buttons)
        self._load_settings_to_ui()
        self._connect_settings_signals()
        self._build_menu()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Datei"); a = QAction("Dateien hinzufügen", self); a.triggered.connect(self.add_files); b = QAction("Ordner hinzufügen", self); b.triggered.connect(self.add_folder); q = QAction("Beenden", self); q.triggered.connect(self.close); file_menu.addAction(a); file_menu.addAction(b); file_menu.addSeparator(); file_menu.addAction(q)
        settings_menu = self.menuBar().addMenu("Einstellungen")
        save_action = QAction("Einstellungen jetzt speichern", self)
        save_action.triggered.connect(lambda: (self.save_settings(), QMessageBox.information(self, "Einstellungen", "Einstellungen gespeichert.")))
        reset_action = QAction("Einstellungen zurücksetzen", self)
        reset_action.triggered.connect(self.reset_settings)
        settings_menu.addAction(save_action); settings_menu.addAction(reset_action)
        help_menu = self.menuBar().addMenu("Hilfe"); h = QAction("Hilfe / Dateiformate / Magic Presets", self); h.triggered.connect(self.show_help); about = QAction("Über AudioForge", self); about.triggered.connect(self.show_about); help_menu.addAction(h); help_menu.addSeparator(); help_menu.addAction(about)

    def _bool_setting(self, key: str, default: bool) -> bool:
        value = self.settings.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "ja", "on"}

    def _set_combo_if_valid(self, combo: QComboBox, value: object) -> None:
        text = str(value)
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _load_settings_to_ui(self) -> None:
        self.output_dir = Path(str(self.settings.value("output_dir", str(self.output_dir))))
        self.output_dir_edit.setText(str(self.output_dir))
        self._set_combo_if_valid(self.format_combo, self.settings.value("format", self.format_combo.currentText()))
        self._set_combo_if_valid(self.quality_combo, self.settings.value("quality", self.quality_combo.currentText()))
        self._set_combo_if_valid(self.preset_combo, self.settings.value("preset", self.preset_combo.currentText()))
        self._set_combo_if_valid(self.theme_combo, self.settings.value("theme", self.current_theme))
        self.preserve_structure_cb.setChecked(self._bool_setting("preserve_structure", self.preserve_structure_cb.isChecked()))
        self.auto_number_cb.setChecked(self._bool_setting("auto_number", self.auto_number_cb.isChecked()))
        self.keep_metadata_cb.setChecked(self._bool_setting("keep_metadata", self.keep_metadata_cb.isChecked()))
        self.normalize_cb.setChecked(self._bool_setting("normalize", self.normalize_cb.isChecked()))
        self.apply_analysis_cb.setChecked(self._bool_setting("apply_analysis", self.apply_analysis_cb.isChecked()))
        try:
            width = int(self.settings.value("window_width", self.width()))
            height = int(self.settings.value("window_height", self.height()))
            if width >= 820 and height >= 520:
                self.resize(width, height)
        except Exception:
            pass

    def _connect_settings_signals(self) -> None:
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        for combo in [self.format_combo, self.quality_combo, self.preset_combo]:
            combo.currentTextChanged.connect(lambda _value: self.save_settings())
        for checkbox in [self.preserve_structure_cb, self.auto_number_cb, self.keep_metadata_cb, self.normalize_cb, self.apply_analysis_cb]:
            checkbox.toggled.connect(lambda _value: self.save_settings())

    def on_theme_changed(self, _theme: str) -> None:
        self._apply_style()
        self.save_settings()

    def save_settings(self) -> None:
        if not hasattr(self, "settings") or not hasattr(self, "format_combo"):
            return
        self.settings.setValue("theme", self.theme_combo.currentText())
        self.settings.setValue("output_dir", self.output_dir_edit.text())
        self.settings.setValue("format", self.format_combo.currentText())
        self.settings.setValue("quality", self.quality_combo.currentText())
        self.settings.setValue("preset", self.preset_combo.currentText())
        self.settings.setValue("preserve_structure", self.preserve_structure_cb.isChecked())
        self.settings.setValue("auto_number", self.auto_number_cb.isChecked())
        self.settings.setValue("keep_metadata", self.keep_metadata_cb.isChecked())
        self.settings.setValue("normalize", self.normalize_cb.isChecked())
        self.settings.setValue("apply_analysis", self.apply_analysis_cb.isChecked())
        self.settings.setValue("window_width", self.width())
        self.settings.setValue("window_height", self.height())
        self.settings.sync()

    def reset_settings(self) -> None:
        reply = QMessageBox.question(self, "Einstellungen zurücksetzen", "Alle gespeicherten AudioForge-Einstellungen zurücksetzen?")
        if reply != QMessageBox.Yes:
            return
        self.settings.clear()
        self.settings.sync()
        self._set_combo_if_valid(self.theme_combo, DEFAULT_THEME)
        self._set_combo_if_valid(self.format_combo, "MP3")
        self._set_combo_if_valid(self.quality_combo, DEFAULT_QUALITY)
        self._set_combo_if_valid(self.preset_combo, "Magic 3")
        self.output_dir = Path.home() / "Music" / "AudioForge"
        self.output_dir_edit.setText(str(self.output_dir))
        self.preserve_structure_cb.setChecked(False)
        self.auto_number_cb.setChecked(True)
        self.keep_metadata_cb.setChecked(True)
        self.normalize_cb.setChecked(True)
        self.apply_analysis_cb.setChecked(False)
        self._apply_style()
        self.save_settings()
        QMessageBox.information(self, "Einstellungen", "Einstellungen wurden zurückgesetzt.")

    def _apply_style(self) -> None:
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else getattr(self, "current_theme", DEFAULT_THEME)
        self.current_theme = theme if theme in THEMES else DEFAULT_THEME
        self.setStyleSheet(get_stylesheet(self.current_theme))
        if hasattr(self, "logo_label"):
            self._configure_header_logo_transparency()

    def _configure_header_logo_transparency(self) -> None:
        # Wichtig für transparente PNGs:
        # Das PNG selbst behält seine Alpha-Transparenz automatisch.
        # Diese Einstellungen verhindern nur, dass QLabel oder ein Theme-Stylesheet
        # eine eigene Hintergrundfläche hinter das Logo malt.
        self.logo_label.setAutoFillBackground(False)
        self.logo_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.logo_label.setAttribute(Qt.WA_NoSystemBackground, True)
        self.logo_label.setStyleSheet("""
            QLabel#HeaderBanner {
                background-color: transparent;
                border: none;
            }
        """)

    def _load_header_logo(self) -> None:
        self._configure_header_logo_transparency()
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
        if not logo_path.exists():
            self.logo_label.setPixmap(QPixmap())
            self.logo_label.setText("assets/logo.png\n16:9 Banner")
            return
        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            self.logo_label.setPixmap(QPixmap())
            self.logo_label.setText("Logo konnte nicht geladen werden")
            return
        pixmap = self._prepare_header_logo_pixmap(pixmap)
        self.logo_label.clear()
        self._header_logo_pixmap = pixmap
        self._update_header_logo_pixmap()

    def _pixmap_has_real_transparency(self, pixmap: QPixmap) -> bool:
        image = pixmap.toImage()
        if not image.hasAlphaChannel():
            return False
        width, height = image.width(), image.height()
        if width <= 0 or height <= 0:
            return False
        # Voller Scan ist beim kleinen Header-Logo unkritisch und erkennt auch
        # PNGs, die zwar einen Alpha-Kanal haben, aber komplett deckend sind.
        for y in range(height):
            for x in range(width):
                if image.pixelColor(x, y).alpha() < 250:
                    return True
        return False

    def _prepare_header_logo_pixmap(self, pixmap: QPixmap) -> QPixmap:
        # Fall 1: Das PNG hat echte Alpha-Transparenz. Dann nichts anfassen.
        if self._pixmap_has_real_transparency(pixmap):
            return pixmap

        # Fall 2: Das vermeintlich transparente PNG enthält ein hineingerendertes
        # Schachbrettmuster. Dann versuchen wir, nur die vom Bildrand erreichbaren
        # typischen hellgrauen/weißen Karo-Pixel transparent zu machen.
        cleaned = self._remove_baked_checkerboard_background(pixmap)
        return cleaned if cleaned is not None else pixmap

    def _remove_baked_checkerboard_background(self, pixmap: QPixmap) -> QPixmap | None:
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        width, height = image.width(), image.height()
        if width <= 0 or height <= 0:
            return None

        def is_light_neutral(color) -> bool:
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
            avg = (r + g + b) / 3
            return a > 245 and 145 <= avg <= 255 and max(r, g, b) - min(r, g, b) <= 14

        # Typische Checkerboard-Farben aus dem Rand sammeln, z.B. #ffffff und #cccccc.
        step = max(1, min(width, height) // 80)
        sampled = []
        for x in range(0, width, step):
            sampled.append(image.pixelColor(x, 0))
            sampled.append(image.pixelColor(x, height - 1))
        for y in range(0, height, step):
            sampled.append(image.pixelColor(0, y))
            sampled.append(image.pixelColor(width - 1, y))

        buckets: dict[tuple[int, int, int], int] = {}
        for color in sampled:
            if not is_light_neutral(color):
                continue
            # Etwas runden, damit kleine Export-Artefakte zusammenfallen.
            key = (round(color.red() / 8) * 8, round(color.green() / 8) * 8, round(color.blue() / 8) * 8)
            buckets[key] = buckets.get(key, 0) + 1

        candidates = [key for key, count in sorted(buckets.items(), key=lambda item: item[1], reverse=True)[:4] if count >= 2]
        if len(candidates) < 2:
            return None

        brightness = [sum(c) / 3 for c in candidates]
        if max(brightness) - min(brightness) < 12:
            return None

        def matches_checker(color) -> bool:
            if not is_light_neutral(color):
                return False
            r, g, b = color.red(), color.green(), color.blue()
            for cr, cg, cb in candidates:
                if abs(r - cr) <= 18 and abs(g - cg) <= 18 and abs(b - cb) <= 18:
                    return True
            return False

        # Flood-fill nur vom Rand aus: Dadurch werden helle Details im Logo nicht
        # einfach gelöscht, solange sie nicht Teil des Außen-Hintergrunds sind.
        stack: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for x in range(width):
            stack.append((x, 0))
            stack.append((x, height - 1))
        for y in range(height):
            stack.append((0, y))
            stack.append((width - 1, y))

        changed = False
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= width or y >= height or (x, y) in seen:
                continue
            seen.add((x, y))
            color = image.pixelColor(x, y)
            if not matches_checker(color):
                continue
            color.setAlpha(0)
            image.setPixelColor(x, y, color)
            changed = True
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))

        if not changed:
            return None
        return QPixmap.fromImage(image)

    def _update_header_logo_pixmap(self) -> None:
        if not getattr(self, "_header_logo_pixmap", None): return
        self._configure_header_logo_transparency()
        scaled = self._header_logo_pixmap.scaled(QSize(self.BANNER_WIDTH, self.BANNER_HEIGHT), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled)

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Audiodateien auswählen", str(Path.home()), "Audio (*.wav *.wave *.flac *.mp3 *.m4a *.aac *.ogg *.opus *.aiff *.aif *.wv);;Alle Dateien (*)")
        self._add_paths([Path(f) for f in files])
    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ordner auswählen", str(Path.home()))
        if folder: self._add_paths([p for p in Path(folder).rglob("*") if p.is_file() and is_audio_file(p)])
    def _add_paths(self, paths: list[Path]) -> None:
        existing = {j.source.resolve() for j in self.jobs}; added = 0; first_new_row = len(self.jobs)
        for path in paths:
            if not path.exists() or not is_audio_file(path): continue
            if path.resolve() in existing: continue
            self.jobs.append(AudioJob(path, probe_duration(path), probe_format_name(path), read_basic_tags(path))); existing.add(path.resolve()); added += 1
        self._update_common_root(); self.refresh_table()
        if added and 0 <= first_new_row < len(self.jobs): self.table.selectRow(first_new_row)
        self.log_message(f"{added} Datei(en) hinzugefügt.")
    def _update_common_root(self) -> None:
        self.common_root = Path(os.path.commonpath([str(j.source.parent) for j in self.jobs])) if self.jobs else None
    def remove_selected(self) -> None:
        for row in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            if 0 <= row < len(self.jobs): self.jobs.pop(row)
        self._update_common_root(); self.refresh_table()
    def clear_jobs(self) -> None:
        if self.current_process: return
        self.jobs.clear(); self.refresh_table(); self.current_progress.setValue(0); self.total_progress.setValue(0); self.cover_preview.setText("Kein Cover"); self.cover_preview.setPixmap(QPixmap())
    def refresh_table(self) -> None:
        self.table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            values = ["🖼" if job.cover_path else "—", job.source.name, job.tags.get("title",""), job.tags.get("artist",""), job.tags.get("album",""), job.source.suffix.upper().lstrip("."), format_duration(job.duration), f"{job.status} {job.progress}%" if job.progress else job.status]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value); item.setToolTip(str(job.source) if col==1 else "")
                if col in {0,5,6,7}: item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row,col,item)
        self._refresh_buttons()
    def selected_rows(self) -> list[int]: return sorted({i.row() for i in self.table.selectedIndexes()})
    def selected_rows_or_first(self) -> list[int]: return self.selected_rows() or ([0] if self.jobs else [])
    def choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ausgabeordner wählen", str(self.output_dir))
        if folder:
            self.output_dir = Path(folder)
            self.output_dir_edit.setText(str(self.output_dir))
            self.save_settings()
    def open_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True); subprocess.Popen(["xdg-open", str(self.output_dir)])
    def edit_metadata(self) -> None:
        rows = self.selected_rows()
        if not rows: QMessageBox.information(self,"Keine Auswahl","Bitte erst eine oder mehrere Dateien auswählen."); return
        d = MetadataDialog(self.jobs[rows[0]].tags.copy(), self)
        if d.exec() != MetadataDialog.Accepted: return
        targets = range(len(self.jobs)) if d.apply_to_all else rows
        for row in targets: self.jobs[row].tags.update(d.values())
        self.refresh_table(); self.log_message("Metadaten aktualisiert.")
    def save_metadata_to_sources(self) -> None:
        rows = self.selected_rows()
        if not rows: QMessageBox.information(self,"Keine Auswahl","Bitte erst eine oder mehrere Dateien auswählen."); return
        if QMessageBox.question(self,"Metadaten speichern","Tags/Cover direkt in die ausgewählten Originaldateien schreiben?") != QMessageBox.Yes: return
        for row in rows:
            for warning in write_metadata(self.jobs[row].source, self.jobs[row].tags, self.jobs[row].cover_path): self.log_message(f"WARNUNG {self.jobs[row].source.name}: {warning}")
        self.log_message(f"Metadaten gespeichert: {len(rows)} Datei(en).")
    def tags_from_filename(self) -> None:
        rows = self.selected_rows()
        if not rows: QMessageBox.information(self,"Keine Auswahl","Bitte erst Dateien auswählen."); return
        for row in rows:
            job=self.jobs[row]; stem=job.source.stem; m=re.match(r"^(?P<track>\d{1,3})\s*[-_. ]+\s*(?P<title>.+)$", stem)
            if m: job.tags["tracknumber"]=m.group("track"); job.tags["title"]=m.group("title").replace("_"," ").strip()
            elif " - " in stem: job.tags["artist"], job.tags["title"] = [x.strip() for x in stem.split(" - ",1)]
            else: job.tags["title"] = stem
        self.refresh_table(); self.log_message("Tags aus Dateinamen erzeugt.")
    def choose_cover(self) -> None:
        rows=self.selected_rows()
        if not rows: QMessageBox.information(self,"Keine Auswahl","Bitte erst eine oder mehrere Dateien auswählen."); return
        file,_=QFileDialog.getOpenFileName(self,"Cover auswählen",str(Path.home()),"Bilder (*.jpg *.jpeg *.png *.webp);;Alle Dateien (*)")
        if not file: return
        for row in rows: self.jobs[row].cover_path=Path(file)
        self.refresh_table(); self.update_cover_preview(); self.log_message("Cover gesetzt.")
    def cover_to_all(self) -> None:
        rows=self.selected_rows(); cover=self.jobs[rows[0]].cover_path if rows else None
        if not cover: QMessageBox.information(self,"Kein Cover","Die erste ausgewählte Datei hat kein Cover."); return
        for job in self.jobs: job.cover_path=cover
        self.refresh_table(); self.log_message("Cover auf alle Dateien angewendet.")
    def remove_cover(self) -> None:
        for row in self.selected_rows(): self.jobs[row].cover_path=None
        self.refresh_table(); self.update_cover_preview()
    def update_cover_preview(self) -> None:
        rows=self.selected_rows(); cover=self.jobs[rows[0]].cover_path if rows else None
        if cover and cover.exists():
            pix=QPixmap(str(cover))
            if not pix.isNull(): self.cover_preview.setPixmap(pix.scaled(QSize(150,150), Qt.KeepAspectRatio, Qt.SmoothTransformation)); return
        self.cover_preview.setPixmap(QPixmap()); self.cover_preview.setText("Kein Cover")

    def analyze_selected(self) -> None:
        rows=self.selected_rows_or_first()
        if not rows: QMessageBox.information(self,"Keine Datei","Bitte erst eine Audiodatei hinzufügen."); return
        if self.current_process: QMessageBox.warning(self,"Läuft bereits","Es läuft bereits ein FFmpeg-Prozess."); return
        row=rows[0]; job=self.jobs[row]; self.current_index=row; self._process_mode="analysis"; self._analysis_stderr=[]; job.status="Analyse"; job.progress=0; self.current_progress.setValue(0); self.total_progress.setValue(0); self.analysis_result_label.setText("Analyse läuft…"); self.status_label.setText(f"Analysiere {job.source.name}…"); self.refresh_table(); self._refresh_buttons()
        seconds=int(min(max(job.duration,1),60)) if job.duration else 60
        args=["-hide_banner","-nostats","-progress","pipe:1","-i",str(job.source),"-t",str(seconds),"-af","astats=metadata=1:reset=0,volumedetect","-f","null","-"]
        self.log_message(f"Analyse: {job.source.name} ({seconds}s)")
        p=QProcess(self); self.current_process=p; p.setProgram("ffmpeg"); p.setArguments(args); p.setProcessChannelMode(QProcess.SeparateChannels); p.readyReadStandardOutput.connect(self._read_progress); p.readyReadStandardError.connect(self._read_stderr); p.finished.connect(self._analysis_finished); p.errorOccurred.connect(self._process_error); p.start()
    def _analysis_finished(self, exit_code:int, _status) -> None:
        if self.current_index < 0: return
        job=self.jobs[self.current_index]; text="\n".join(self._analysis_stderr)
        if exit_code==0:
            result=parse_analysis_output(text, job.source)
            if self.apply_analysis_cb.isChecked():
                self.preset_combo.setCurrentText(result.recommendation)
                applied_note="\n\nDie Empfehlung wurde automatisch als Magic-Preset übernommen."
            else:
                applied_note="\n\nDas aktuell gewählte Magic-Preset wurde nicht verändert. Zum Übernehmen Checkbox aktivieren oder Preset manuell wählen."
            job.status=f"Empfehlung {result.recommendation}"; job.progress=100; self.current_progress.setValue(100); self.total_progress.setValue(100); self.analysis_result_label.setText(f"{result.recommendation}: {result.reason}"); self.log_message(format_analysis_summary(result)+applied_note); QMessageBox.information(self,"Magic-Empfehlung",format_analysis_summary(result)+applied_note)
        else:
            job.status="Analyse-Fehler"; self.analysis_result_label.setText("Analyse fehlgeschlagen."); self.log_message(f"FEHLER bei Analyse von {job.source.name}: FFmpeg Exit-Code {exit_code}")
        self.current_process=None; self.current_index=-1; self._process_mode=None; self.refresh_table(); self._refresh_buttons(); self.status_label.setText("Bereit.")

    def make_preview(self) -> None:
        rows=self.selected_rows_or_first()
        if not rows: QMessageBox.information(self,"Keine Datei","Bitte erst eine Audiodatei hinzufügen."); return
        self._start_queue(rows[:1], True)
    def start_conversion(self) -> None:
        if not self.jobs: QMessageBox.information(self,"Keine Dateien","Bitte erst Audiodateien hinzufügen."); return
        self._start_queue(list(range(len(self.jobs))), False)
    def _start_queue(self, rows:list[int], preview:bool) -> None:
        if self.current_process: QMessageBox.warning(self,"Läuft bereits","Es läuft bereits eine Konvertierung."); return
        self._queue=rows; self._queue_pos=0; self.current_preview=preview; self._process_mode="conversion"
        self._queue_settings={
            "format_name": self.format_combo.currentText(),
            "quality_name": self.quality_combo.currentText(),
            "preset_name": self.preset_combo.currentText(),
            "normalize": self.normalize_cb.isChecked(),
            "preserve_metadata": self.keep_metadata_cb.isChecked(),
            "preserve_structure": self.preserve_structure_cb.isChecked(),
            "auto_number": self.auto_number_cb.isChecked(),
        }
        for row in rows:
            self.jobs[row].status="wartet"; self.jobs[row].progress=0; self.jobs[row].clip_retry_done=False
        self.log_message(f"Queue-Einstellungen: Preset={self._queue_settings['preset_name']}, Normalisieren={self._queue_settings['normalize']}, Format={self._queue_settings['format_name']}, Qualität={self._queue_settings['quality_name']}")
        self.current_progress.setValue(0); self.total_progress.setValue(0); self._refresh_buttons(); self._start_next_job()
    def _start_next_job(self) -> None:
        if self._queue_pos >= len(self._queue):
            self.current_process=None; self.current_index=-1; self._process_mode=None; self.status_label.setText("Fertig."); self.current_progress.setValue(100); self.total_progress.setValue(100); self.refresh_table(); self._refresh_buttons(); self.log_message("Alle Aufgaben abgeschlossen."); return
        row=self._queue[self._queue_pos]; self.current_index=row; job=self.jobs[row]; job.status="läuft" if not job.clip_retry_done else "läuft + Headroom"; job.progress=0; self.refresh_table()
        fmt=str(self._queue_settings.get("format_name", self.format_combo.currentText()))
        qual=str(self._queue_settings.get("quality_name", self.quality_combo.currentText()))
        preset=str(self._queue_settings.get("preset_name", self.preset_combo.currentText()))
        normalize=bool(self._queue_settings.get("normalize", self.normalize_cb.isChecked()))
        preserve_metadata=bool(self._queue_settings.get("preserve_metadata", self.keep_metadata_cb.isChecked()))
        preserve_structure=bool(self._queue_settings.get("preserve_structure", self.preserve_structure_cb.isChecked()))
        auto_number=bool(self._queue_settings.get("auto_number", self.auto_number_cb.isChecked()))
        spec=get_format_spec(fmt, qual); out_dir=Path(self.output_dir_edit.text()).expanduser(); out_dir.mkdir(parents=True, exist_ok=True)
        if job.clip_retry_done and job.output_path:
            output=job.output_path
        else:
            output=(out_dir/"previews"/f"{job.source.stem}_preview_{preset.replace(' ','_')}{spec.extension}") if self.current_preview else build_output_path(job.source,out_dir,spec.extension,preserve_structure,self.common_root,auto_number)
        output.parent.mkdir(parents=True, exist_ok=True); job.output_path=output
        extra_headroom_db=6.0 if job.clip_retry_done else 0.0
        args=build_ffmpeg_args(job.source,output,fmt,qual,preset,normalize,preserve_metadata,True,30 if self.current_preview else None,extra_headroom_db=extra_headroom_db)
        self._current_stderr=[]
        self.log_message(f"Starte: {job.source.name} → {output.name} | Preset={preset}, Normalisieren={normalize}, Extra-Headroom={extra_headroom_db:.0f} dB")
        p=QProcess(self); self.current_process=p; p.setProgram("ffmpeg"); p.setArguments(args); p.setProcessChannelMode(QProcess.SeparateChannels); p.readyReadStandardOutput.connect(self._read_progress); p.readyReadStandardError.connect(self._read_stderr); p.finished.connect(self._process_finished); p.errorOccurred.connect(self._process_error); p.start()
    def _read_progress(self) -> None:
        if not self.current_process or self.current_index < 0: return
        data=bytes(self.current_process.readAllStandardOutput()).decode(errors="replace"); job=self.jobs[self.current_index]
        for line in data.splitlines():
            if line.startswith("out_time_ms="):
                try:
                    cur=int(line.split("=",1)[1])/1_000_000; dur=(min(job.duration,60) if job.duration else 60) if self._process_mode=="analysis" else (min(job.duration,30) if self.current_preview else job.duration)
                    if dur>0: job.progress=max(0,min(100,int((cur/dur)*100))); self.current_progress.setValue(job.progress); self._update_total_progress()
                except ValueError: pass
        self.refresh_table()
    def _read_stderr(self) -> None:
        if not self.current_process: return
        data=bytes(self.current_process.readAllStandardError()).decode(errors="replace")
        if data.strip():
            if self._process_mode=="analysis": self._analysis_stderr.append(data)
            elif self._process_mode=="conversion": self._current_stderr.append(data)
            self.log.appendPlainText(data.rstrip())
    def _process_finished(self, exit_code:int, _status) -> None:
        if self.current_index<0: return
        job=self.jobs[self.current_index]
        row=self.current_index
        stderr_text="\n".join(self._current_stderr)
        clipping_warning=bool(re.search(r"clipping.*Please reduce gain|Channel\s+\d+\s+clipping", stderr_text, re.IGNORECASE))
        preset=str(self._queue_settings.get("preset_name", self.preset_combo.currentText()))
        if exit_code==0:
            if clipping_warning and preset != "Aus" and not job.clip_retry_done:
                self.log_message(f"Clip-Warnung erkannt bei {job.source.name}. Wiederhole automatisch mit 6 dB zusätzlichem Headroom …")
                job.clip_retry_done=True; job.status="Headroom-Retry"; job.progress=0; self.current_process=None; self.current_progress.setValue(0); self.refresh_table(); self._start_next_job(); return
            job.progress=100; job.status="fertig ⚠" if clipping_warning else "fertig"; self.current_progress.setValue(100)
            if clipping_warning:
                job.warnings.append("FFmpeg meldete trotz Headroom noch Channel-Clipping. Datei wurde erzeugt, aber bitte kurz gegenhören oder niedrigeres Magic-Preset wählen.")
                self.log_message(f"WARNUNG {job.source.name}: Clip-Warnung blieb bestehen. Niedrigeres Magic-Preset oder Normalisierung prüfen.")
            if not self.current_preview and job.output_path:
                for w in write_metadata(job.output_path, job.tags, job.cover_path): self.log_message(f"WARNUNG {job.output_path.name}: {w}")
                self.log_message(f"Metadaten/Cover in Ausgabedatei geschrieben: {job.output_path.name}")
            self.log_message(f"Fertig: {job.output_path}")
        else: job.status="Fehler"; self.log_message(f"FEHLER bei {job.source.name}: FFmpeg Exit-Code {exit_code}")
        self._queue_pos+=1; self.current_process=None; self._update_total_progress(); self.refresh_table(); self._start_next_job()
    def _process_error(self, error) -> None: self.log_message(f"Prozessfehler: {error}")
    def stop_conversion(self) -> None:
        if self.current_process:
            self.current_process.kill();
            if 0<=self.current_index<len(self.jobs): self.jobs[self.current_index].status="gestoppt"
            self.current_process=None; self._process_mode=None; self.status_label.setText("Gestoppt."); self.refresh_table(); self._refresh_buttons()
    def _update_total_progress(self) -> None:
        if not getattr(self,"_queue",None): self.total_progress.setValue(self.current_progress.value()); return
        completed=self._queue_pos; current=(self.jobs[self.current_index].progress/100 if self.current_index>=0 else 0); self.total_progress.setValue(max(0,min(100,int(((completed+current)/len(self._queue))*100))))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event: QDropEvent) -> None:
        paths=[]
        for url in event.mimeData().urls():
            p=Path(url.toLocalFile())
            if p.is_dir(): paths.extend([x for x in p.rglob("*") if x.is_file() and is_audio_file(x)])
            elif p.is_file(): paths.append(p)
        self._add_paths(paths)
    def closeEvent(self, event: QCloseEvent) -> None:
        if self.current_process and QMessageBox.question(self,"Konvertierung läuft","FFmpeg läuft noch. Wirklich beenden?") != QMessageBox.Yes: event.ignore(); return
        if self.current_process: self.current_process.kill()
        self.save_settings()
        event.accept()
    def _check_tools(self) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None: QMessageBox.warning(self,"FFmpeg fehlt","FFmpeg oder FFprobe wurde nicht gefunden. Bitte install.sh ausführen oder FFmpeg installieren.")
    def _refresh_buttons(self) -> None:
        running=self.current_process is not None; has_jobs=bool(self.jobs); has_sel=bool(self.selected_rows())
        self.convert_btn.setEnabled(has_jobs and not running); self.preview_btn.setEnabled(has_jobs and not running); self.analyze_btn.setEnabled(has_jobs and not running); self.stop_btn.setEnabled(running); self.remove_btn.setEnabled(has_sel and not running); self.clear_btn.setEnabled(has_jobs and not running); self.edit_meta_btn.setEnabled(has_sel and not running); self.save_meta_btn.setEnabled(has_sel and not running); self.tags_from_filename_btn.setEnabled(has_sel and not running); self.cover_btn.setEnabled(has_sel and not running); self.cover_all_btn.setEnabled(has_sel and not running); self.cover_remove_btn.setEnabled(has_sel and not running)
    def log_message(self, message:str) -> None: self.log.appendPlainText(message)
    def show_help(self) -> None:
        preset_lines="\n".join(f"{n}: {d}" for n,d in PRESET_DESCRIPTIONS.items())
        QMessageBox.information(self,"Hilfe / Dateiformate / Magic Presets","AudioForge konvertiert Audiodateien mit FFmpeg und schreibt Metadaten/Cover danach mit Mutagen.\n\nDateiformate kurz:\nMP3: maximale Kompatibilität, verlustbehaftet.\nFLAC: verlustfrei, ideal fürs Archiv.\nWAV/AIFF: unkomprimiert, Studio/DAW.\nOPUS: modern, sehr effizient.\nM4A/AAC: Apple/Handy/Web.\nALAC: Apple Lossless.\nOGG/Vorbis: offenes Format.\n\nQualität: ‘Beste Qualität’ ist Standard.\n\nMagic Presets:\n"+preset_lines+"\n\nv10: Neues Layout-Farbschema-Menü und automatische Speicherung von Ausgabeordner, Format, Qualität, Magic-Preset, Normalisierung, Analyse-Option, Fenstergröße und Theme. v9: Magic-Kette nutzt erst Headroom-Absenkung, dann Effekte, dann Normalisierung/Limiter.")
    def show_about(self) -> None:
        QMessageBox.about(self,"Über AudioForge","AudioForge MVP v10\n\nAudio-Konverter mit FFmpeg, Magic-Presets, Normalisierung, Metadaten und Cover-Bearbeitung.\n\nWritten by Daniela Kamp\nFree MIT License · 2026")
