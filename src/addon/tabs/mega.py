from typing import TYPE_CHECKING

from ..pathlike import MegaRoot
from .base import ImportTab
if TYPE_CHECKING:
    from .base import ImportDialog


class MegaTab(ImportTab):

    def __init__(self, dialog: "ImportDialog"):
        self.define_texts()
        ImportTab.__init__(self, dialog)

    def define_texts(self) -> None:
        self.button_text = "Check URL"
        self.import_not_valid_tooltip = "Check if your URL is correct, then press 'check URL'."
        self.empty_input_msg = "Input a url to a Mega shared folder"
        self.while_create_rootfile_msg = "Checking if URL is valid..."
        self.valid_input_msg = "Valid URL"
        self.malformed_url_msg = "Invalid URL"
        self.root_not_found_msg = "Folder not found"

    def on_btn(self) -> None:
        self.update_root_file()

    def create_root_file(self, url: str) -> MegaRoot:
        return MegaRoot(url)
