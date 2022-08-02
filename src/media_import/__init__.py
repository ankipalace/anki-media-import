import sys
from typing import Any, List
from pathlib import Path
from aqt import gui_hooks, mw

from .libs import install_pycrypto, uninstall_pycrypto

core_dir = Path(__file__).resolve().parent / "core"
sys.path.append(str(core_dir))
libs_dir = Path(__file__).resolve().parent / "libs"
sys.path.append(str(libs_dir))

try:
    from Crypto.Cipher import AES  # type: ignore
except:
    install_pycrypto()

from .ui import open_import_dialog, ImportDialog


def on_delete_addon(dial: Any, ids: List[str]) -> None:
    addon_id = mw.addonManager.addonFromModule(__name__)
    if addon_id in ids:
        uninstall_pycrypto()


gui_hooks.addons_dialog_will_delete_addons.append(on_delete_addon)
