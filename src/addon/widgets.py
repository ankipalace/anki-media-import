from concurrent.futures import Future
from typing import Optional
from pathlib import Path
import math

from anki.media import media_paths_from_col_path
from anki.utils import isWin
from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, restoreGeom, saveGeom, tooltip
import aqt.editor

from .importing import import_media, get_list_of_files, delete_temp_folder, ImportResult


def qlabel(text: str) -> QLabel:
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    return label


def small_qlabel(text: str) -> QLabel:
    label = qlabel(text)
    font = label.font()
    if font.pointSize() != -1:
        font_size = math.floor(font.pointSize() * 0.92)
        font.setPointSize(font_size)
    else:
        font_size = math.floor(font.pixelSize() * 0.92)
        font.setPixelSize(font_size)
    label.setFont(font)
    return label


class ImportResultDialog(QMessageBox):
    def __init__(self, parent: QWidget, result: ImportResult) -> None:
        QMessageBox.__init__(self, parent)
        if result.success:
            title = "Import Complete"
            self.setIcon(QMessageBox.Information)
        else:
            title = "Import Failed"
            self.setIcon(QMessageBox.Critical)
        self.setWindowTitle(title)
        text = f"<h3><b>{title}</b></h3>{result.logs[-1]}{'&nbsp;'*5}<br>"
        self.setText(text)
        self.setTextFormat(Qt.RichText)
        self.setDetailedText("\n".join(result.logs))


class ImportDialog(QDialog):
    def __init__(self) -> None:
        QDialog.__init__(self, mw, Qt.Window)
        self.setWindowTitle("Import Media")
        self.setMinimumWidth(500)
        self.setup()
        self.setup_buttons()
        restoreGeom(self, f"addon-mediaimport-import")
        self.update_file_count()
        self.valid_path = False

    def setup(self) -> None:
        outer_layout = QVBoxLayout(self)
        self.outer_layout = outer_layout
        self.setLayout(outer_layout)

        main_grid = QGridLayout(self)

        outer_layout.addLayout(main_grid)

        import_text = qlabel("Import")
        main_grid.addWidget(import_text, 0, 0)

        dropdown = QComboBox()
        self.filemode_dropdown = dropdown
        options = ("Folder", "File")
        self.filemode_dropdown_opts = options
        for option in options:
            dropdown.addItem(option)
        dropdown.setCurrentIndex(0)
        main_grid.addWidget(dropdown, 0, 1)
        self.import_dropdown = dropdown

        path_input = QLineEdit()
        self.path_input = path_input
        path_input.setMinimumWidth(200)
        path_input.textEdited.connect(self.update_file_count)
        main_grid.addWidget(path_input, 0, 2)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.on_browse)
        main_grid.addWidget(browse_button, 0, 3)

        fcount_label = small_qlabel("")
        self.fcount_label = fcount_label
        main_grid.addWidget(fcount_label, 1, 2)

        self.outer_layout.addStretch(1)
        self.outer_layout.addSpacing(10)

    def setup_buttons(self) -> None:
        button_row = QHBoxLayout()
        self.outer_layout.addLayout(button_row)

        media_dir_btn = QPushButton("Open Media Folder")
        media_dir_btn.clicked.connect(self.open_media_dir)
        button_row.addWidget(media_dir_btn)

        button_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        button_row.addWidget(cancel_btn)

        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.on_import)
        button_row.addWidget(import_btn)

    def on_browse(self) -> None:
        dropdown = self.filemode_dropdown
        options = self.filemode_dropdown_opts
        if dropdown.currentText() == options[0]:  # Directory
            path = self.get_directory()
        elif dropdown.currentText() == options[1]:  # File
            path = self.get_file()
        else:
            raise Exception("Import Media: What happened to the dropdown?")
        if path is not None:
            self.path_input.setText(path)
            self.update_file_count()

    def finish_import(self, result: ImportResult) -> None:
        delete_temp_folder()
        mw.progress.finish()
        if result.success:
            ImportResultDialog(mw, result).exec_()
            self.hide()
        else:
            ImportResultDialog(self, result).exec_()

    def on_import(self) -> None:
        path = Path(self.path_input.text()).resolve()
        if self.valid_path:
            mw.progress.start(
                parent=mw, label="Starting import", immediate=True)
            import_media(path, self.finish_import)
        else:
            tooltip("Invalid Path", parent=self)  # type: ignore

    def open_media_dir(self) -> None:
        media_dir = media_paths_from_col_path(mw.col.path)[0]
        openFolder(media_dir)

    def closeEvent(self, evt: QCloseEvent) -> None:
        saveGeom(self, f"addon-mediaImport-import")

    def file_name_filter(self) -> str:
        exts_filter = ""
        for ext_list in (aqt.editor.pics, aqt.editor.audio):
            for ext in ext_list:
                exts_filter += f"*.{ext} "
        exts_filter = exts_filter[:-1]  # remove last whitespace
        return f"Image & Audio Files ({exts_filter})"

    def file_dialog(self) -> QFileDialog:
        dialog = QFileDialog(self)
        dialog.setNameFilter(self.file_name_filter())
        dialog.setOption(QFileDialog.ShowDirsOnly, False)
        if isWin:
            # Windows directory chooser doesn't display files
            # TODO: Check whether to use native or qt file chooser
            dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        return dialog

    def get_directory(self) -> Optional[str]:
        dialog = self.file_dialog()
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec_():
            # TODO this *can* raise error. ToFix!
            assert len(dialog.selectedFiles()) == 1
            path = dialog.selectedFiles()[0]
            return path
        else:
            return None

    def get_file(self) -> Optional[str]:
        dialog = self.file_dialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec_():
            assert len(dialog.selectedFiles()) == 1
            path = dialog.selectedFiles()[0]
            return path
        else:
            return None

    def update_file_count(self) -> None:
        self.valid_path = False
        path = self.path_input.text()
        if path == "":
            self.fcount_label.setText("Input a path")
            return
        self.fcount_label.setText("Calculating number of files...")

        def on_done(fut: Future) -> None:
            if self.path_input.text() != path:
                # Text many have changed during long calculation
                return
            try:
                files_list = fut.result()
            except PermissionError:
                self.fcount_label.setText("Insufficient permission")
                return

            if files_list is None:
                self.fcount_label.setText("Invalid path")
            else:
                self.fcount_label.setText(
                    "{} files found".format(len(files_list)))
                self.valid_path = True

        mw.taskman.run_in_background(
            get_list_of_files, on_done, {"src": Path(path).resolve()}
        )
