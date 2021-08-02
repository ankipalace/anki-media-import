from anki.media import media_paths_from_col_path
from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, restoreGeom, saveGeom

from .importing import ImportResult
from .tabs import ImportTab, LocalTab, GDriveTab, MegaTab


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

    def setup(self) -> None:
        main_layout = QVBoxLayout(self)
        self.main_layout = main_layout
        self.setLayout(main_layout)

        main_tab = QTabWidget()
        self.main_tab = main_tab
        main_tab.setFocusPolicy(Qt.StrongFocus)
        main_layout.addWidget(main_tab)
        main_layout.addSpacing(10)

        self.local_tab = LocalTab(self)
        main_tab.addTab(self.local_tab, "Local Files")
        self.gdrive_tab = GDriveTab(self)
        main_tab.addTab(self.gdrive_tab, "Google Drive")
        self.mega_tab = MegaTab(self)
        main_tab.addTab(self.mega_tab, "Mega")

    def setup_buttons(self) -> None:
        button_row = QHBoxLayout()
        self.main_layout.addLayout(button_row)

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

    def finish_import(self, result: ImportResult) -> None:
        mw.progress.finish()
        if result.success:
            ImportResultDialog(mw, result).exec_()
            self.hide()
        else:
            ImportResultDialog(self, result).exec_()

    def open_media_dir(self) -> None:
        media_dir = media_paths_from_col_path(mw.col.path)[0]
        openFolder(media_dir)

    def closeEvent(self, evt: QCloseEvent) -> None:
        saveGeom(self, f"addon-mediaImport-import")

    def on_import(self) -> None:
        self.tab.on_import()

    @property
    def tab(self) -> "ImportTab":
        print(self.main_tab.currentWidget())
        print(type(self.main_tab.currentWidget()))
        return self.main_tab.currentWidget()  # type: ignore
