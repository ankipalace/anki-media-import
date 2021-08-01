from concurrent.futures import Future
from typing import Optional, TYPE_CHECKING

from anki.utils import isWin
from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor

from ..importing import import_media, get_list_of_files
from ..pathlike import LocalPath
from .base import ImportTab
if TYPE_CHECKING:
    from .base import ImportDialog


class LocalTab(QWidget, ImportTab):

    def __init__(self, dialog: "ImportDialog"):
        QWidget.__init__(self, dialog)
        self.dialog = dialog
        self.valid_path = False
        self.setup()
        self.update_file_count()

    def setup(self) -> None:
        self.main_layout = QVBoxLayout(self)
        main_layout = self.main_layout
        self.setLayout(self.main_layout)

        main_grid = QGridLayout(self)

        main_layout.addLayout(main_grid)

        import_text = self.qlabel("Import")
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

        fcount_label = self.small_qlabel("")
        self.fcount_label = fcount_label
        main_grid.addWidget(fcount_label, 1, 2)

        main_layout.addStretch(1)

    def on_import(self) -> None:
        path = LocalPath(self.path_input.text())
        if self.valid_path:
            mw.progress.start(
                parent=mw, label="Starting import", immediate=True)
            import_media(path, self.dialog.finish_import)
        else:
            tooltip("Invalid Path", parent=self)  # type: ignore

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

    # File Browse Dialogs

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
            get_list_of_files, on_done, {"src": LocalPath(path)}
        )
