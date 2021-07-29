from typing import Optional, Tuple
from pathlib import Path

from anki.media import media_paths_from_col_path
from anki.utils import isWin
from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, openLink, restoreGeom, saveGeom
import aqt.editor

from .importing import import_media


class ImportDialog(QDialog):
    def __init__(self) -> None:
        QDialog.__init__(self, mw, Qt.Window)
        self.setWindowTitle("Import Media")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumWidth(500)
        self.setup()
        self.setup_buttons()
        restoreGeom(self, f"addon-mediaimport-import")

    def format_exts(self, ext_list: Tuple[str, ...], name: str) -> str:
        exts_filter = ""
        for ext in ext_list:
            exts_filter += f"*.{ext} "
        image_exts = exts_filter[:-1]  # remove last whitespace
        return f"{name} Files ({image_exts})"

    def file_dialog(self) -> QFileDialog:
        dialog = QFileDialog(self)
        image_exts = self.format_exts(aqt.editor.pics, "Image")
        audio_exts = self.format_exts(aqt.editor.audio, "Audio")
        dialog.setNameFilters([image_exts, audio_exts])
        dialog.setFileMode(QFileDialog.ExistingFile)
        if isWin:
            # Windows directory chooser doesn't display files
            # TODO: Check whether to use native or qt file chooser
            dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        return dialog

    def get_directory(self) -> Optional[str]:
        dialog = self.file_dialog()
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec_():
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

    def setup(self) -> None:
        outer_layout = QVBoxLayout()
        self.outer_layout = outer_layout
        self.setLayout(outer_layout)

        row = QHBoxLayout()
        outer_layout.addLayout(row)

        import_text = QLabel("Import")
        row.addWidget(import_text)

        dropdown = QComboBox()
        options = ("Directory", "File")
        for option in options:
            dropdown.addItem(option)
        dropdown.setCurrentIndex(0)
        row.addWidget(dropdown)
        self.import_dropdown = dropdown

        path_input = QLineEdit()
        self.path_input = path_input
        path_input.setMinimumWidth(200)
        row.addWidget(path_input)

        def on_browse() -> None:
            if dropdown.currentText() == options[0]:  # Directory
                path = self.get_directory()
            elif dropdown.currentText() == options[1]:  # File
                path = self.get_file()
            else:
                raise Exception("Import Media: What happened to the dropdown?")
            if path is not None:
                path_input.setText(path)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(on_browse)
        row.addWidget(browse_button)

    def on_import(self) -> None:
        path = Path(self.path_input.text())
        import_media(path)
        self.close()

    def open_media_dir(self) -> None:
        media_dir = media_paths_from_col_path(mw.col.path)[0]
        openFolder(media_dir)

    def closeEvent(self, evt: QCloseEvent) -> None:
        saveGeom(self, f"addon-mediaImport-import")

    def setup_buttons(self) -> None:
        self.outer_layout.addStretch(1)
        self.outer_layout.addSpacing(10)
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


def open_import_dialog() -> None:
    dialog = ImportDialog()
    dialog.show()


# Anking menu code


def getMenu(parent: QWidget, menuName: str) -> QMenu:
    menubar = parent.form.menubar
    for a in menubar.actions():
        if menuName == a.text():
            return a.menu()
    else:
        return menubar.addMenu(menuName)


def create_sub_menu_if_not_exist(menu: QMenu, subMenuName: str) -> Optional[QMenu]:
    for a in menu.actions():
        if subMenuName == a.text():
            return None
    else:
        subMenu = QMenu(subMenuName, menu)
        menu.addMenu(subMenu)
        return subMenu


def open_web(url: str) -> None:
    openLink(f"https://{url}")


def setupMenu() -> None:
    MENU_OPTIONS = [
        ("Online Mastery Course",
         "courses.ankipalace.com/?utm_source=anking_bg_add-on&utm_medium=anki_add-on&utm_campaign=mastery_course"),
        ("Daily Q and A Support", "www.ankipalace.com/memberships"),
        ("1-on-1 Tutoring", "www.ankipalace.com/tutoring")
    ]
    menu_name = "&AnKing"
    menu = getMenu(mw, menu_name)
    submenu = create_sub_menu_if_not_exist(menu, "Get Anki Help")
    if submenu:
        for t, url in MENU_OPTIONS:
            act = QAction(t, mw)
            act.triggered.connect(lambda _: open_web(url))
            submenu.addAction(act)
    a = QAction("Import Media", mw)
    a.triggered.connect(open_import_dialog)
    menu.addAction(a)


setupMenu()
