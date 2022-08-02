import sys
from pathlib import Path

core_dir = Path(__file__).resolve().parent / "core"
sys.path.append(str(core_dir))
libs_dir = Path(__file__).resolve().parent / "libs"
sys.path.append(str(libs_dir))

try:
    import Crypto.Cipher
except:
    from .libs import install_pycrypto

    install_pycrypto()

from .ui import open_import_dialog, ImportDialog
