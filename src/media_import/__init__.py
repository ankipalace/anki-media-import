import sys
from typing import Any, List
from pathlib import Path

from anki.hooks import wrap
from aqt import mw
from aqt.addons import AddonManager

from .libs import install_pycrypto, uninstall_pycrypto

core_dir = Path(__file__).resolve().parent / "core"
sys.path.append(str(core_dir))
libs_dir = Path(__file__).resolve().parent / "libs"
sys.path.append(str(libs_dir))

try:
    from Crypto.Cipher import AES  # type: ignore
except:
    install_pycrypto()

# exposed functions
from .ui import open_import_dialog, ImportDialog


def on_delete_addon(mgr: AddonManager, module: str) -> None:
    addon_id = mw.addonManager.addonFromModule(__name__)
    if module == addon_id:
        uninstall_pycrypto()


# Triggered when addon is deleted & updated
AddonManager.deleteAddon = wrap(  # type: ignore
    old=AddonManager.deleteAddon,
    new=on_delete_addon,
    pos="before",
)
