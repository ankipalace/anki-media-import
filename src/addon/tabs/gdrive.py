from concurrent.futures import Future
from typing import Optional, TYPE_CHECKING
import re

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

from ..pathlike import GDriveRoot, RequestError, RootNotFoundError, MalformedURLError
from ..importing import ImportResult, import_media
from .base import ImportTab
if TYPE_CHECKING:
    from .base import ImportDialog


class GDriveTab(QWidget, ImportTab):

    def __init__(self, dialog: "ImportDialog"):
        QWidget.__init__(self, dialog)
        self.dialog = dialog
        self.valid_path = False
        self.rootfile: Optional[GDriveRoot] = None
        self.setup()
        self.update_sub_text()

    def setup(self) -> None:
        self.main_layout = QVBoxLayout(self)
        main_layout = self.main_layout
        self.setLayout(self.main_layout)

        main_grid = QGridLayout(self)

        main_layout.addLayout(main_grid)

        import_text = self.qlabel("Import")
        main_grid.addWidget(import_text, 0, 0)

        url_input = QLineEdit()
        self.url_input = url_input
        url_input.setMinimumWidth(200)
        url_input.textEdited.connect(self.update_sub_text)
        main_grid.addWidget(url_input, 0, 2)

        sub_text = self.small_qlabel("")
        self.sub_text = sub_text
        main_grid.addWidget(sub_text, 1, 2)

        main_layout.addStretch(1)

    def create_root_file(self, url: str) -> GDriveRoot:
        return GDriveRoot(url)

    def update_sub_text(self) -> None:
        self.valid_path = False
        url = self.url_input.text()
        if url == "":
            self.sub_text.setText(
                "Input a url to a Google Drive shared folder.")
            return

        self.url_input.setText("Checking if url is valid...")

        def update_root_file(fut: Future) -> None:
            curr_url = self.url_input.text()
            if not url == curr_url:
                return
            try:
                self.rootfile = fut.result()
                self.valid_path = True
                self.sub_text.setText("Valid url")
            except MalformedURLError:
                mw.progress.finish()
                self.sub_text.setText("Invalid url")
            except RootNotFoundError:
                mw.progress.finish()
                self.sub_text.setText("Folder not found")
            except RequestError as err:
                print(err)
                self.sub_text.setText(f"ERROR: {err.msg}")

        mw.taskman.run_in_background(
            self.create_root_file, update_root_file, {"url": url})

    def on_import(self) -> None:
        if self.valid_path:
            mw.progress.start(
                parent=mw, label="Starting import")
            try:
                import_media(self.rootfile, self.dialog.finish_import)
            except RequestError as err:
                logs = [str(err)]
                result = ImportResult(logs, success=False)
                self.dialog.finish_import(result)
                return
