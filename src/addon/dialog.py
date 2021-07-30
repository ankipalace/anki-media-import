from typing import Optional, Tuple
from pathlib import Path
import math

from anki.media import media_paths_from_col_path
from anki.utils import isWin
from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, openLink, restoreGeom, saveGeom
import aqt.editor

from .importing import import_media, get_list_of_files


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


class ImportDialog(QDialog):  # TODO: allow selecting text from dialog
    def __init__(self) -> None:
        QDialog.__init__(self, mw, Qt.Window)
        self.setWindowTitle("Import Media")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMinimumWidth(500)
        self.setup()
        self.setup_buttons()
        restoreGeom(self, f"addon-mediaimport-import")
        self.update_file_count()

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

    def update_file_count(self) -> None:
        path = self.path_input.text()
        if path == "":
            self.fcount_label.setText("Input a Path")
            return
        files_list = get_list_of_files(Path(path))
        if files_list is None:
            self.fcount_label.setText("Invalid Path")
        else:
            self.fcount_label.setText(
                "{} Files Found".format(len(files_list)))

    def setup(self) -> None:
        outer_layout = QVBoxLayout(self)
        self.outer_layout = outer_layout
        self.setLayout(outer_layout)

        main_grid = QGridLayout(self)

        outer_layout.addLayout(main_grid)

        import_text = qlabel("Import")
        main_grid.addWidget(import_text, 0, 0)

        dropdown = QComboBox()
        options = ("Directory", "File")
        for option in options:
            dropdown.addItem(option)
        dropdown.setCurrentIndex(0)
        main_grid.addWidget(dropdown, 0, 1)
        self.import_dropdown = dropdown

        path_input = QLineEdit()
        self.path_input = path_input
        path_input.setMinimumWidth(200)
        path_input.editingFinished.connect(self.update_file_count)
        main_grid.addWidget(path_input, 0, 2)

        def on_browse() -> None:
            if dropdown.currentText() == options[0]:  # Directory
                path = self.get_directory()
            elif dropdown.currentText() == options[1]:  # File
                path = self.get_file()
            else:
                raise Exception("Import Media: What happened to the dropdown?")
            if path is not None:
                path_input.setText(path)
                self.update_file_count()

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(on_browse)
        main_grid.addWidget(browse_button, 0, 3)

        fcount_label = small_qlabel("")
        self.fcount_label = fcount_label
        main_grid.addWidget(fcount_label, 1, 2)

        self.outer_layout.addStretch(1)
        self.outer_layout.addSpacing(10)

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
