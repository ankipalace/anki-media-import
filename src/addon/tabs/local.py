from typing import Optional, TYPE_CHECKING

from anki.utils import isWin
from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor

from ..importing import import_media
from ..pathlike import LocalRoot
from .base import ImportTab
if TYPE_CHECKING:
    from .base import ImportDialog


class LocalTab(ImportTab):

    def __init__(self, dialog: "ImportDialog"):
        self.define_texts()
        ImportTab.__init__(self, dialog)

    def define_texts(self) -> None:
        self.button_text = "Browse"
        self.import_not_valid_tooltip = "Check if your path is correct"
        self.empty_input_msg = "Input a path"
        self.while_create_rootpath_msg = "Calculating number of files..."
        self.malformed_url_msg = "Invalid Path"
        self.root_not_found_msg = "Folder doesn't exist."
        self.is_a_file_msg = "This path leads to a file. Please write a path to a folder."

    def create_root_file(self, url: str) -> LocalRoot:
        return LocalRoot(url)

    def on_btn(self) -> None:
        path = self.get_directory()
        if path is not None:
            self.path_input.setText(path)
            self.update_root_file()

    # File Browse Dialog
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
            # This can return multiple paths onccasionally. Qt bug?
            if not len(dialog.selectedFiles()) == 1:
                tooltip("Something went wrong. Please select the folder again.")
                return None
            path = dialog.selectedFiles()[0]
            return path
        else:
            return None
