# expose functions
import sys
from pathlib import Path

from anki.hooks import wrap
from aqt import mw
from aqt.addons import AddonManager

from .libs import install_zstandard, uninstall_zstandard

libs_dir = Path(__file__).resolve().parent / "libs"
sys.path.append(str(libs_dir))

try:
    from zstandard import ZstdDecompressor  # noqa F401
except:
    install_zstandard()


def on_delete_addon(mgr: AddonManager, module: str) -> None:
    addon_id = mw.addonManager.addonFromModule(__name__)
    if module == addon_id:
        uninstall_zstandard()


# Triggered when addon is deleted & updated
AddonManager.deleteAddon = wrap(  # type: ignore
    old=AddonManager.deleteAddon,
    new=on_delete_addon,
    pos="before",
)

# expose functions
from .ui import ImportDialog, open_import_dialog  # noqa F401
