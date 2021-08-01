from typing import Optional, TYPE_CHECKING
import re

from aqt import mw
from aqt.qt import *
from requests.models import parse_url

from ..pathlike import GDrivePath, RequestError
from ..importing import ImportResult, import_media
from .base import ImportTab
if TYPE_CHECKING:
    from .base import ImportDialog


REGEXP = r"drive.google.com/drive/folders/([^?]*)(?:\?|$)"
URL_PATTERN = re.compile(REGEXP)


class GDriveTab(QWidget, ImportTab):

    def __init__(self, dialog: "ImportDialog"):
        QWidget.__init__(self, dialog)
        self.dialog = dialog
        self.valid_path = False
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

    def parse_url(self, url: str) -> Optional[str]:
        """ Format: https://drive.google.com/drive/folders/{gdrive_id}?params """
        m = re.search(URL_PATTERN, url)
        if m:
            return m.group(1)
        return None

    def update_sub_text(self) -> None:
        self.valid_path = False
        url = self.url_input.text()
        if url == "":
            self.sub_text.setText(
                "Input a url to a Google Drive shared folder.")
            return

        id = self.parse_url(url)
        if id:
            self.valid_path = True
            self.sub_text.setText("Valid url")
        else:
            self.sub_text.setText("Invalid url")

    def on_import(self) -> None:
        if self.valid_path:
            url = self.url_input.text()
            id = self.parse_url(url)
            mw.progress.start(
                parent=mw, label="Starting import", immediate=True)
            try:
                path = GDrivePath(id=id)
            except RequestError as err:
                logs = [str(err)]
                result = ImportResult(logs, success=False)
                self.dialog.finish_import(result)
                return

            import_media(path, self.dialog.finish_import)
