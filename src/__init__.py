from typing import Callable

from aqt import gui_hooks, mw
from aqt.qt import QAction

from .anking import get_anking_menu
from .media_import import open_import_dialog


def setupMenu(handler: Callable[[], None]) -> None:
    menu = get_anking_menu()
    a = QAction("Import Media", mw)
    a.triggered.connect(handler)  # type: ignore
    menu.addAction(a)


gui_hooks.main_window_did_init.append(lambda: setupMenu(open_import_dialog))
