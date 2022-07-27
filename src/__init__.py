from aqt import gui_hooks

from .anking import setupMenu
from .media_import import open_import_dialog


gui_hooks.main_window_did_init.append(lambda: setupMenu(open_import_dialog))
