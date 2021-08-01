from typing import TYPE_CHECKING
import math

from aqt.qt import *

if TYPE_CHECKING:
    from ..dialog import ImportDialog


class ImportTab:

    def on_import(self) -> None:
        pass

    def qlabel(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        return label

    def small_qlabel(self, text: str) -> QLabel:
        label = self.qlabel(text)
        font = label.font()
        if font.pointSize() != -1:
            font_size = math.floor(font.pointSize() * 0.92)
            font.setPointSize(font_size)
        else:
            font_size = math.floor(font.pixelSize() * 0.92)
            font.setPixelSize(font_size)
        label.setFont(font)
        return label
