from typing import Optional

from aqt import mw
from aqt.utils import openLink
from aqt.qt import *


import_dialog = None


def open_import_dialog() -> None:
    from .dialog import ImportDialog

    global import_dialog
    if import_dialog is None:
        import_dialog = ImportDialog()
    if not import_dialog.isVisible():
        import_dialog.show()
    import_dialog.activateWindow()


# Anking menu code
#####################################################


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
